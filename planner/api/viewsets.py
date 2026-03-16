from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from celery.result import AsyncResult
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
        component_service = ComponentService(component_repo=component_repo, product_repo=product_repo, tech_process_repo=None)  # type: ignore[arg-type]

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
        overwrite = bool(request.data.get("overwrite", False))
        from planner.repositories.tech_process import TechProcessRepository

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
        return Response({"project_id": project_id, "gantt": {"status": "stub", "data": []}})

    @action(detail=False, methods=["get"], url_path="tech-card")
    def tech_card(self, request: Request) -> Response:
        project_id = int(request.query_params.get("project_id", "0"))
        return Response({"project_id": project_id, "tech_card": {"status": "stub", "data": []}})


class ProductionPlanViewSet(viewsets.ModelViewSet):
    queryset = ProductionPlan.objects.all()
    serializer_class = ProductionPlanSerializer


class AlgorithmComparisonViewSet(viewsets.ModelViewSet):
    queryset = AlgorithmComparison.objects.all()
    serializer_class = AlgorithmComparisonSerializer

