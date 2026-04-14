from __future__ import annotations


import os

from datetime import date, datetime

from io import BytesIO

from typing import Any, Dict



from django.http import HttpResponse

from django.db import transaction

from django.utils import timezone

from celery.result import AsyncResult

from openpyxl import Workbook

from openpyxl.styles import Font

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

from planner.models import (

    AlgorithmComparison,

    Component,
    ComponentTechProcess,

    Equipment,

    Personnel,

    Product,

    ProductionPlan,

    ProductionPlanEquipment,

    ProductionPlanPersonnel,

    Project,

    TechProcess,

)

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

from planner.repositories.production_plan import ProductionPlanRepository





class ProjectViewSet(viewsets.ModelViewSet):

    queryset = Project.objects.all()

    serializer_class = ProjectSerializer



    @action(detail=True, methods=["post"], url_path="pause")

    def pause(self, request: Request, pk: str | None = None) -> Response:

        project_id = int(pk or "0")

        if project_id <= 0:

            return Response({"detail": "Invalid project id"}, status=status.HTTP_400_BAD_REQUEST)

        project = self.get_object()

        project.status = "paused"

        project.save(update_fields=["status"])



        svc = ProjectManagementService(

            project_repo=ProjectRepository(),

            equipment_repo=EquipmentRepository(),

            personnel_repo=PersonnelRepository(),

        )

        released_links = svc.release_project_resources(project_id)

        return Response({"status": "paused", "project_id": project_id, "released_links": released_links})



    @action(detail=True, methods=["post"], url_path="resume")

    def resume(self, request: Request, pk: str | None = None) -> Response:

        project = self.get_object()

        project.status = "active"

        project.save(update_fields=["status"])

        return Response({"status": "active", "project_id": project.id})



    @action(detail=True, methods=["get"], url_path="resource-summary")

    def resource_summary(self, request: Request, pk: str | None = None) -> Response:

        project_id = int(pk or "0")

        if project_id <= 0:

            return Response({"detail": "Invalid project id"}, status=status.HTTP_400_BAD_REQUEST)

        plans = ProductionPlan.objects.filter(project_id=project_id)

        plan_ids = list(plans.values_list("id", flat=True))

        if not plan_ids:

            return Response(

                {

                    "project_id": project_id,

                    "personnel_count": 0,

                    "equipment_count": 0,

                    "equipment_types": [],

                }

            )



        personnel_ids = (

            ProductionPlanPersonnel.objects.filter(production_plan_id__in=plan_ids)

            .values_list("personnel_id", flat=True)

            .distinct()

        )

        equipment_qs = Equipment.objects.filter(

            id__in=ProductionPlanEquipment.objects.filter(production_plan_id__in=plan_ids).values_list("equipment_id", flat=True)

        ).distinct()

        equipment_types = sorted(set(e.type for e in equipment_qs if e.type))

        return Response(

            {

                "project_id": project_id,

                "personnel_count": len(list(personnel_ids)),

                "equipment_count": equipment_qs.count(),

                "equipment_types": equipment_types,

            }

        )



    @action(detail=True, methods=["post"], url_path="assign-resources")

    def assign_resources(self, request: Request, pk: str | None = None) -> Response:

        project_id = int(pk or "0")

        if project_id <= 0:

            return Response({"detail": "Invalid project id"}, status=status.HTTP_400_BAD_REQUEST)



        equipment_ids = request.data.get("equipment_ids", []) or []

        personnel_ids = request.data.get("personnel_ids", []) or []

        if not isinstance(equipment_ids, list) or not isinstance(personnel_ids, list):

            return Response(

                {"detail": "equipment_ids and personnel_ids must be arrays"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        equipment_ids = [int(x) for x in equipment_ids]

        personnel_ids = [int(x) for x in personnel_ids]



        with transaction.atomic():

            plan, _ = ProductionPlan.objects.get_or_create(

                project_id=project_id,

                status="draft",

                defaults={

                    "algorithm_used": "MANUAL",

                    "created_date": timezone.now().date(),

                    "schedule": {},

                    "actual_data": {},

                    "deviations": {},

                },

            )



            ProductionPlanEquipment.objects.filter(production_plan_id=plan.id).delete()

            ProductionPlanPersonnel.objects.filter(production_plan_id=plan.id).delete()



            existing_equipment = set(

                Equipment.objects.filter(id__in=equipment_ids).values_list("id", flat=True)

            )

            existing_personnel = set(

                Personnel.objects.filter(id__in=personnel_ids).values_list("id", flat=True)

            )



            ProductionPlanEquipment.objects.bulk_create(

                [

                    ProductionPlanEquipment(

                        production_plan_id=plan.id,

                        equipment_id=eid,

                        hours_required=0,

                    )

                    for eid in sorted(existing_equipment)

                ]

            )

            ProductionPlanPersonnel.objects.bulk_create(

                [

                    ProductionPlanPersonnel(

                        production_plan_id=plan.id,

                        personnel_id=pid,

                        hours_assigned=0,

                    )

                    for pid in sorted(existing_personnel)

                ]

            )



        return Response(

            {

                "project_id": project_id,

                "plan_id": plan.id,

                "equipment_count": len(existing_equipment),

                "personnel_count": len(existing_personnel),

            }

        )



    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:

        project = self.get_object()

        project_id = project.id

        svc = ProjectManagementService(

            project_repo=ProjectRepository(),

            equipment_repo=EquipmentRepository(),

            personnel_repo=PersonnelRepository(),

        )

        released_links = svc.release_project_resources(project_id)

        response = super().destroy(request, *args, **kwargs)

        response.data = {"status": "deleted", "project_id": project_id, "released_links": released_links}

        return response



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
            raw = xml_file.read()
            decode_error: Exception | None = None
            for encoding in ("utf-8-sig", "utf-8", "cp1251"):
                try:
                    xml_content = raw.decode(encoding)
                    decode_error = None
                    break
                except UnicodeDecodeError as exc:
                    decode_error = exc
            if decode_error is not None:
                raise decode_error

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





class EquipmentViewSet(viewsets.ModelViewSet):

    queryset = Equipment.objects.all().order_by("name")

    serializer_class = EquipmentSerializer





class PersonnelViewSet(viewsets.ModelViewSet):

    queryset = Personnel.objects.all().order_by("full_name")

    serializer_class = PersonnelSerializer





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



    @action(detail=False, methods=["post"], url_path="chart-data")

    def chart_data(self, request: Request) -> Response:

        project_id = int(request.data.get("project_id", 0))

        if project_id <= 0:

            return Response({"detail": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        params = request.data.get("params", {}) or {}

        service = OptimizationService(

            project_repo=ProjectRepository(),

            product_repo=ProductRepository(),

            component_repo=ComponentRepository(),

        )

        result = service.build_algorithm_chart_data(project_id, **params)

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

        deadline = Project.objects.filter(id=project_id).values_list("deadline", flat=True).first()

        start_date = Project.objects.filter(id=project_id).values_list("start_date", flat=True).first()

        target_days = 0.0

        if deadline and start_date:

            target_days = max(1.0, float((deadline - start_date).days + 1))



        def _deadline_score(duration: float) -> float:

            if target_days <= 0:

                return 0.0

            return max(0.0, min(1.0, target_days / max(duration, 1.0)))



        records = [

            AlgorithmComparison(

                project_id=project_id,

                algorithm_name="CPM",

                total_duration=cpm_time,

                resource_utilization=max(0.0, cpm_time / max(target_days, 1.0)) if target_days else 0.0,

                deadline_satisfaction=_deadline_score(cpm_time),

                computed_date=now,

            ),

            AlgorithmComparison(

                project_id=project_id,

                algorithm_name="GA",

                total_duration=ga_fit,

                resource_utilization=max(0.0, ga_fit / max(target_days, 1.0)) if target_days else 0.0,

                deadline_satisfaction=_deadline_score(ga_fit),

                computed_date=now,

            ),

            AlgorithmComparison(

                project_id=project_id,

                algorithm_name="SA",

                total_duration=sa_cost,

                resource_utilization=max(0.0, sa_cost / max(target_days, 1.0)) if target_days else 0.0,

                deadline_satisfaction=_deadline_score(sa_cost),

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
    @staticmethod
    def _load_cyrillic_font() -> str:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        for font_path in candidates:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont("ReportCyrillic", font_path))
                    return "ReportCyrillic"
                except Exception:
                    continue
        return "Helvetica"

    @staticmethod
    def _collect_operations_rows(project_id: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        links = (
            ComponentTechProcess.objects.filter(component__product__project_id=project_id)
            .select_related("component", "tech_process")
            .order_by("component__id", "tech_process__sequence_order")
        )
        for link in links:
            tp = link.tech_process
            eq = tp.equipment_required if isinstance(tp.equipment_required, dict) else {}
            rows.append(
                {
                    "component": link.component.name,
                    "operation_no": tp.sequence_order or "",
                    "operation_name": tp.name,
                    "prep_time": tp.prep_time or 0,
                    "unit_time": tp.unit_time or 0,
                    "equipment": eq.get("name", "") if isinstance(eq, dict) else "",
                }
            )
        return rows

    @staticmethod
    def _collect_assigned_resources(plan: ProductionPlan | None) -> tuple[list[str], list[str]]:
        if plan is None:
            return [], []
        equipment_rows = (
            ProductionPlanEquipment.objects.filter(production_plan=plan)
            .select_related("equipment")
            .order_by("equipment__name")
        )
        personnel_rows = (
            ProductionPlanPersonnel.objects.filter(production_plan=plan)
            .select_related("personnel")
            .order_by("personnel__full_name")
        )
        equipment = [f"{row.equipment.name} ({row.hours_required or 0} ч)" for row in equipment_rows]
        personnel = [f"{row.personnel.full_name} ({row.hours_assigned or 0} ч)" for row in personnel_rows]
        return equipment, personnel

    @staticmethod
    def _pdf_line(pdf: canvas.Canvas, text: str, y: float, left: int, page_h: float, font_name: str) -> float:
        if y < 60:
            pdf.showPage()
            y = page_h - 40
            pdf.setFont(font_name, 9)
        pdf.drawString(left, y, text[:120])
        return y - 14

    @staticmethod
    def _extract_gantt_rows(plan: ProductionPlan | None) -> list[dict[str, Any]]:
        if plan is None or not isinstance(plan.schedule, dict):
            return []
        rows: list[dict[str, Any]] = []
        schedule = plan.schedule
        operations = schedule.get("operations")
        if isinstance(operations, dict):
            for _, op in operations.items():
                if not isinstance(op, dict):
                    continue
                start = float(op.get("earliest_start", op.get("start", op.get("start_day", 0))) or 0)
                end = float(op.get("earliest_finish", op.get("end", op.get("end_day", start))) or start)
                rows.append(
                    {
                        "name": str(op.get("name", "Операция")),
                        "start": start,
                        "end": max(start, end),
                    }
                )
        list_schedule = schedule.get("schedule")
        if isinstance(list_schedule, list):
            for item in list_schedule:
                if not isinstance(item, dict):
                    continue
                start = float(item.get("start", item.get("start_day", 0)) or 0)
                end = float(item.get("end", item.get("end_day", start + item.get("duration", 0))) or start)
                rows.append(
                    {
                        "name": str(item.get("operation_name", item.get("name", "Операция"))),
                        "start": start,
                        "end": max(start, end),
                    }
                )
        return rows

    @action(detail=False, methods=["get"], url_path="gantt")

    def gantt(self, request: Request) -> Response:

        project_id = int(request.query_params.get("project_id", "0"))

        svc = ReportingService(

            project_repo=ProjectRepository(),

            plan_repo=ProductionPlanRepository(),

            comparison_repo=AlgorithmComparisonRepository(),

        )

        try:

            report_data = svc.get_project_summary_report_data(project_id)

        except ValueError as exc:

            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        selected_plan = ProductionPlan.objects.filter(project_id=project_id).order_by("-created_date", "-id").first()

        equipment_lines, personnel_lines = self._collect_assigned_resources(selected_plan)
        gantt_rows = self._extract_gantt_rows(selected_plan)

        font_name = self._load_cyrillic_font()
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        _, h = A4
        margin = 40
        y = h - margin
        proj = report_data["project"]

        pdf.setFont(font_name, 14)
        pdf.drawString(margin, y, f"Отчет по проекту: {proj.get('name', '')} (ID {proj['id']})")
        y -= 22
        pdf.setFont(font_name, 10)
        y = self._pdf_line(
            pdf,
            f"Статус: {proj.get('status', '')}, старт: {proj.get('start_date', '')}, дедлайн: {proj.get('deadline', '')}",
            y,
            margin,
            h,
            font_name,
        )

        pdf.setFont(font_name, 11)
        y = self._pdf_line(pdf, "Сравнение алгоритмов", y - 6, margin, h, font_name)
        pdf.setFont(font_name, 9)
        for row in report_data.get("algorithm_comparisons", []):
            line = (
                f"{row.get('algorithm_name', '')}: длительность={row.get('total_duration', '')}, "
                f"утилизация={row.get('resource_utilization', '')}, дедлайн={row.get('deadline_satisfaction', '')}"
            )
            y = self._pdf_line(pdf, line, y, margin + 8, h, font_name)

        pdf.setFont(font_name, 11)
        y = self._pdf_line(pdf, "Планы производства", y - 4, margin, h, font_name)
        pdf.setFont(font_name, 9)
        for p in report_data.get("production_plans", []):
            y = self._pdf_line(
                pdf,
                f"План #{p.get('id')} | {p.get('algorithm_used', '')} | {p.get('status', '')} | {p.get('created_date', '')}",
                y,
                margin + 8,
                h,
                font_name,
            )

        pdf.setFont(font_name, 11)
        y = self._pdf_line(pdf, "Назначенные работники", y - 4, margin, h, font_name)
        pdf.setFont(font_name, 9)
        if personnel_lines:
            for line in personnel_lines:
                y = self._pdf_line(pdf, line, y, margin + 8, h, font_name)
        else:
            y = self._pdf_line(pdf, "Нет назначений персонала.", y, margin + 8, h, font_name)

        pdf.setFont(font_name, 11)
        y = self._pdf_line(pdf, "Назначенное оборудование", y - 4, margin, h, font_name)
        pdf.setFont(font_name, 9)
        if equipment_lines:
            for line in equipment_lines:
                y = self._pdf_line(pdf, line, y, margin + 8, h, font_name)
        else:
            y = self._pdf_line(pdf, "Нет назначений оборудования.", y, margin + 8, h, font_name)

        y = self._pdf_line(pdf, "Диаграмма Ганта", y - 4, margin, h, font_name)
        chart_x = margin + 8
        chart_y = y - 140
        chart_w = 500
        chart_h = 130
        if gantt_rows:
            min_start = min(r["start"] for r in gantt_rows)
            max_end = max(r["end"] for r in gantt_rows)
            span = max(1.0, max_end - min_start)
            pdf.rect(chart_x, chart_y, chart_w, chart_h, stroke=1, fill=0)
            row_h = max(8, min(16, int((chart_h - 10) / max(1, len(gantt_rows)))))
            for i, row in enumerate(gantt_rows[:10]):
                ry = chart_y + chart_h - 8 - (i + 1) * row_h
                left = chart_x + ((row["start"] - min_start) / span) * (chart_w - 160) + 150
                width = max(4, ((row["end"] - row["start"]) / span) * (chart_w - 160))
                pdf.setFont(font_name, 7)
                pdf.drawString(chart_x + 4, ry + 2, str(row["name"])[:28])
                pdf.rect(left, ry, width, row_h - 2, stroke=1, fill=1)
            y = chart_y - 10
        else:
            y = self._pdf_line(pdf, "Нет данных расписания для построения Ганта.", y, margin + 8, h, font_name)

        pdf.showPage()

        pdf.save()

        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")

        response["Content-Disposition"] = f'attachment; filename="gantt_project_{project_id}.pdf"'

        return response



    @action(detail=False, methods=["get"], url_path="tech-card")

    def tech_card(self, request: Request) -> Response:

        project_id = int(request.query_params.get("project_id", "0"))

        svc = ReportingService(

            project_repo=ProjectRepository(),

            plan_repo=ProductionPlanRepository(),

            comparison_repo=AlgorithmComparisonRepository(),

        )

        try:

            report_data = svc.get_project_summary_report_data(project_id)

        except ValueError as exc:

            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        selected_plan = ProductionPlan.objects.filter(project_id=project_id).order_by("-created_date", "-id").first()
        equipment_lines, personnel_lines = self._collect_assigned_resources(selected_plan)
        operation_rows = self._collect_operations_rows(project_id)

        wb = Workbook()

        ws = wb.active

        assert ws is not None

        ws.title = "Сводка"

        header_font = Font(bold=True)

        ws.append(["Поле", "Значение"])

        for c in ws[1]:

            c.font = header_font

        proj = report_data["project"]

        ws.append(["ID проекта", str(proj.get("id", ""))])
        ws.append(["Название проекта", str(proj.get("name", ""))])
        ws.append(["Статус", str(proj.get("status", ""))])
        ws.append(["Дата старта", str(proj.get("start_date", ""))])
        ws.append(["Дедлайн", str(proj.get("deadline", ""))])
        ws.append(["Дата завершения", str(proj.get("end_date", ""))])

        ws2 = wb.create_sheet("Сравнение алгоритмов")

        ws2.append(["Алгоритм", "Длительность", "Утилизация", "Соответствие дедлайну", "Дата расчета"])

        for c in ws2[1]:

            c.font = header_font

        for row in report_data.get("algorithm_comparisons", []):

            ws2.append(

                [

                    row.get("algorithm_name", ""),

                    row.get("total_duration", ""),

                    row.get("resource_utilization", ""),

                    row.get("deadline_satisfaction", ""),

                    str(row.get("computed_date", "")),

                ]

            )

        ws3 = wb.create_sheet("Планы")

        ws3.append(["ID плана", "Алгоритм", "Статус", "Дата создания"])

        for c in ws3[1]:

            c.font = header_font

        for p in report_data.get("production_plans", []):

            ws3.append(

                [

                    p.get("id", ""),

                    p.get("algorithm_used", ""),

                    p.get("status", ""),

                    str(p.get("created_date", "")),

                ]

            )

        ws4 = wb.create_sheet("Ресурсы")
        ws4.append(["Тип", "Наименование", "Часы"])
        for c in ws4[1]:
            c.font = header_font
        for line in personnel_lines:
            name, hours = line.rsplit("(", 1)
            ws4.append(["Персонал", name.strip(), hours.replace(")", "").strip()])
        for line in equipment_lines:
            name, hours = line.rsplit("(", 1)
            ws4.append(["Оборудование", name.strip(), hours.replace(")", "").strip()])

        ws5 = wb.create_sheet("Операции")
        ws5.append(
            [
                "Компонент",
                "№ операции",
                "Название операции",
                "Подготовительное время",
                "Поштучное время",
                "Оборудование",
            ]
        )
        for c in ws5[1]:
            c.font = header_font
        for row in operation_rows:
            ws5.append(
                [
                    row["component"],
                    row["operation_no"],
                    row["operation_name"],
                    row["prep_time"],
                    row["unit_time"],
                    row["equipment"],
                ]
            )

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