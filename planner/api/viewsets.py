from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict

from django.http import HttpResponse
from django.utils import timezone
from celery.result import AsyncResult
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from planner.api.serializers import (
    AlgorithmComparisonSerializer,
    CompareAlgorithmsRequestSerializer,
    ComponentSerializer,
    EquipmentSerializer,
    OptimizationRequestSerializer,
    PersonnelSerializer,
    ProductImportStubSerializer,
    ProductSerializer,
    ProductionPlanSerializer,
    ProjectSerializer,
    ResourceAvailabilitySerializer,
    TechProcessSerializer,
)
from planner.models import AlgorithmComparison, Component, Equipment, Personnel, Product, ProductionPlan, Project, TechProcess
from planner.repositories.component import ComponentRepository
from planner.repositories.equipment import EquipmentRepository
from planner.repositories.personnel import PersonnelRepository
from planner.repositories.product import ProductRepository
from planner.repositories.production_plan import ProductionPlanRepository
from planner.repositories.project import ProjectRepository
from planner.repositories.tech_process import TechProcessRepository
from planner.services.component_service import ComponentService
from planner.services.optimization_service import OptimizationService
from planner.services.project_management_service import ProjectManagementService
from planner.services.reporting_service import ReportingService
from planner.services.resource_allocation_service import ResourceAllocationService
from planner.tasks import compare_algorithms_task, run_optimization_task
from planner.repositories.algorithm_comparison import AlgorithmComparisonRepository


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail=True, methods=["get"], url_path="products-structure")
    def products_structure(self, request: Request, pk: str | None = None) -> Response:
        project_id = int(pk or "0")
        product_repo = ProductRepository()
        component_repo = ComponentRepository()
        component_service = ComponentService(
            component_repo=component_repo,
            product_repo=product_repo,
            tech_process_repo=TechProcessRepository(),
        )

        products = list(product_repo.list_by_project(project_id))
        structures = []
        for p in products:
            structures.append({"product": ProductSerializer(p).data, "component_tree": component_service.build_component_tree(p.id)})

        return Response({"project_id": project_id, "structures": structures})

    @action(detail=True, methods=["get"], url_path="metrics")
    def metrics(self, request: Request, pk: str | None = None) -> Response:
        project_id = int(pk or "0")
        svc = ProjectManagementService(project_repo=ProjectRepository())
        progress = svc.get_progress(project_id)
        return Response({"project_id": project_id, "progress": progress})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @action(detail=True, methods=["post"], url_path="import-cad-stub")
    def import_cad_stub(self, request: Request, pk: str | None = None) -> Response:
        serializer = ProductImportStubSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"product_id": int(pk or "0"), "status": "accepted", "received": serializer.validated_data["payload"]},
            status=status.HTTP_202_ACCEPTED,
        )


class ComponentViewSet(viewsets.ModelViewSet):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request: Request) -> Response:
        product_id = int(request.query_params.get("product_id", "0"))
        product_repo = ProductRepository()
        component_repo = ComponentRepository()
        from planner.repositories.tech_process import TechProcessRepository

        svc = ComponentService(component_repo=component_repo, product_repo=product_repo, tech_process_repo=TechProcessRepository())
        return Response(svc.build_component_tree(product_id))

    @action(detail=False, methods=["post"], url_path="import-xml")
    def import_xml(self, request: Request) -> Response:
        product_id = int(request.data.get("product_id", 0))
        xml_content = request.data.get("xml_content", "")
        xml_file = request.FILES.get("xml_file")
        if xml_file is not None:
            xml_content = xml_file.read().decode("utf-8")
        overwrite = bool(request.data.get("overwrite", False))

        svc = ComponentService(
            component_repo=ComponentRepository(),
            product_repo=ProductRepository(),
            tech_process_repo=TechProcessRepository(),
        )
        svc.import_from_xml(product_id, xml_content, overwrite=overwrite)
        return Response({"status": "imported", "product_id": product_id})


class TechProcessViewSet(viewsets.ModelViewSet):
    queryset = TechProcess.objects.all()
    serializer_class = TechProcessSerializer


class ResourceViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], url_path="equipment")
    def equipment(self, request: Request) -> Response:
        qs = Equipment.objects.all().order_by("name")
        return Response(EquipmentSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="personnel")
    def personnel(self, request: Request) -> Response:
        qs = Personnel.objects.all().order_by("full_name")
        return Response(PersonnelSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="check-availability")
    def check_availability(self, request: Request) -> Response:
        serializer = ResourceAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        svc = ResourceAllocationService(
            equipment_repo=EquipmentRepository(),
            personnel_repo=PersonnelRepository(),
        )

        available = svc.check_availability(
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )
        return Response({"available": available, **data})


class PlanningViewSet(viewsets.ViewSet):
    """
    Endpoints for running optimization algorithms and comparing their results.

    Current implementation returns computed dict results; persistence into DB can be added later.
    """

    @action(detail=False, methods=["post"], url_path="optimize")
    def optimize(self, request: Request) -> Response:
        serializer = OptimizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        algorithm = serializer.validated_data["algorithm"]
        async_run = serializer.validated_data["async_run"]
        params = serializer.validated_data.get("params") or {}

        project_id = int(request.data.get("project_id", 0))
        if project_id <= 0:
            return Response({"detail": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if async_run:
            task = run_optimization_task.delay(project_id=project_id, algorithm=algorithm, params=params)
            return Response({"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)

        service = OptimizationService(
            project_repo=ProjectRepository(),
            product_repo=ProductRepository(),
            component_repo=ComponentRepository(),
        )
        result = service.compare_algorithms(project_id, **params).get(algorithm)  # type: ignore[union-attr]
        return Response({"project_id": project_id, "algorithm": algorithm, "result": result})

    @action(detail=False, methods=["post"], url_path="compare")
    def compare(self, request: Request) -> Response:
        serializer = CompareAlgorithmsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        async_run = serializer.validated_data["async_run"]
        params = serializer.validated_data.get("params") or {}
        project_id = int(request.data.get("project_id", 0))
        if project_id <= 0:
            return Response({"detail": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if async_run:
            task = compare_algorithms_task.delay(project_id=project_id, params=params)
            return Response({"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)

        service = OptimizationService(
            project_repo=ProjectRepository(),
            product_repo=ProductRepository(),
            component_repo=ComponentRepository(),
        )
        result = service.compare_algorithms(project_id, **params)
        return Response(result)

    @action(detail=False, methods=["post"], url_path="compare-and-save")
    def compare_and_save(self, request: Request) -> Response:
        project_id = int(request.data.get("project_id", 0))
        if project_id <= 0:
            return Response({"detail": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        params = request.data.get("params", {}) or {}
        service = OptimizationService(
            project_repo=ProjectRepository(),
            product_repo=ProductRepository(),
            component_repo=ComponentRepository(),
        )
        result = service.compare_algorithms(project_id, **params)

        AlgorithmComparison.objects.filter(project_id=project_id).delete()
        now = timezone.now().date()

        cpm_time = float(result.get("cpm", {}).get("total_duration", 0) or 0)
        ga_fit = float(result.get("ga", {}).get("best_fitness", 0) or 0)
        sa_cost = float(result.get("sa", {}).get("best_cost", 0) or 0)

        records = [
            AlgorithmComparison(
                project_id=project_id,
                algorithm_name="CPM",
                total_duration=cpm_time,
                resource_utilization=0.0,
                deadline_satisfaction=1.0 if cpm_time > 0 else 0.0,
                computed_date=now,
            ),
            AlgorithmComparison(
                project_id=project_id,
                algorithm_name="GA",
                total_duration=ga_fit,
                resource_utilization=0.0,
                deadline_satisfaction=1.0 if ga_fit > 0 else 0.0,
                computed_date=now,
            ),
            AlgorithmComparison(
                project_id=project_id,
                algorithm_name="SA",
                total_duration=sa_cost,
                resource_utilization=0.0,
                deadline_satisfaction=1.0 if sa_cost > 0 else 0.0,
                computed_date=now,
            ),
        ]
        AlgorithmComparison.objects.bulk_create(records)
        return Response({"status": "saved", "project_id": project_id, "result": result})

    @action(detail=False, methods=["post"], url_path="select-algorithm")
    def select_algorithm(self, request: Request) -> Response:
        project_id = int(request.data.get("project_id", 0))
        algorithm = str(request.data.get("algorithm", "")).lower()
        if project_id <= 0 or algorithm not in {"cpm", "ga", "sa"}:
            return Response({"detail": "project_id and valid algorithm are required"}, status=status.HTTP_400_BAD_REQUEST)
        params = request.data.get("params", {}) or {}

        service = OptimizationService(
            project_repo=ProjectRepository(),
            product_repo=ProductRepository(),
            component_repo=ComponentRepository(),
        )
        compare_result = service.compare_algorithms(project_id, **params)
        selected_result = compare_result.get(algorithm, {})

        plan = ProductionPlan.objects.create(
            project_id=project_id,
            algorithm_used=algorithm.upper(),
            created_date=timezone.now().date(),
            status="selected",
            schedule=selected_result,
            actual_data={},
            deviations={},
        )
        return Response({"status": "selected", "project_id": project_id, "algorithm": algorithm, "plan_id": plan.id})

    @action(detail=False, methods=["get"], url_path="task-status")
    def task_status(self, request: Request) -> Response:
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response({"detail": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        res = AsyncResult(task_id)
        payload: Dict[str, Any] = {"task_id": task_id, "state": res.state}
        if res.successful():
            payload["result"] = res.result
        elif res.failed():
            payload["error"] = str(res.result)
        return Response(payload)


class ReportViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], url_path="gantt")
    def gantt(self, request: Request) -> Response:
        project_id = int(request.query_params.get("project_id", "0"))
        selected_plan = (
            ProductionPlan.objects.filter(project_id=project_id).order_by("-created_date", "-id").first()
        )

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        y = 800
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, f"Gantt Report - Project {project_id}")
        y -= 30
        pdf.setFont("Helvetica", 11)
        if selected_plan is None:
            pdf.drawString(40, y, "No production plan found.")
        else:
            pdf.drawString(40, y, f"Plan ID: {selected_plan.id}")
            y -= 20
            pdf.drawString(40, y, f"Algorithm: {selected_plan.algorithm_used}")
            y -= 20
            pdf.drawString(40, y, f"Status: {selected_plan.status}")
            y -= 20
            ops_count = 0
            if isinstance(selected_plan.schedule, dict):
                if "operations" in selected_plan.schedule and isinstance(selected_plan.schedule["operations"], dict):
                    ops_count = len(selected_plan.schedule["operations"])
                elif "schedule" in selected_plan.schedule and isinstance(selected_plan.schedule["schedule"], list):
                    ops_count = len(selected_plan.schedule["schedule"])
            pdf.drawString(40, y, f"Operations in schedule: {ops_count}")
        pdf.showPage()
        pdf.save()
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="gantt_project_{project_id}.pdf"'
        return response

    @action(detail=False, methods=["get"], url_path="tech-card")
    def tech_card(self, request: Request) -> Response:
        project_id = int(request.query_params.get("project_id", "0"))
        wb = Workbook()
        ws = wb.active
        ws.title = "TechCard"
        ws.append(["Project ID", "Algorithm", "Plan Status", "Created Date"])
        plans = ProductionPlan.objects.filter(project_id=project_id).order_by("-created_date", "-id")
        for p in plans:
            ws.append([project_id, p.algorithm_used, p.status, str(p.created_date or "")])
        if plans.count() == 0:
            ws.append([project_id, "", "No plans", ""])

        out = BytesIO()
        wb.save(out)
        out.seek(0)
        response = HttpResponse(
            out.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="tech_card_project_{project_id}.xlsx"'
        return response


class ProductionPlanViewSet(viewsets.ModelViewSet):
    queryset = ProductionPlan.objects.all()
    serializer_class = ProductionPlanSerializer


class AlgorithmComparisonViewSet(viewsets.ModelViewSet):
    queryset = AlgorithmComparison.objects.all()
    serializer_class = AlgorithmComparisonSerializer

