from __future__ import annotations

from typing import Any, Dict

from celery import shared_task

from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository
from planner.services.optimization_service import OptimizationService


@shared_task(bind=True)
def run_optimization_task(self, *, project_id: int, algorithm: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    service = OptimizationService(
        project_repo=ProjectRepository(),
        product_repo=ProductRepository(),
        component_repo=ComponentRepository(),
    )
    all_results = service.compare_algorithms(project_id, **(params or {}))
    result = all_results.get(algorithm)
    return {"project_id": project_id, "algorithm": algorithm, "result": result}


@shared_task(bind=True)
def compare_algorithms_task(self, *, project_id: int, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    service = OptimizationService(
        project_repo=ProjectRepository(),
        product_repo=ProductRepository(),
        component_repo=ComponentRepository(),
    )
    return service.compare_algorithms(project_id, **(params or {}))

