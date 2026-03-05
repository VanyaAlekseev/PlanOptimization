from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet

from planner.models import ProductionPlan

from .base import BaseRepository


class ProductionPlanRepository(BaseRepository[ProductionPlan]):
    def __init__(self) -> None:
        super().__init__(model=ProductionPlan)

    def list_by_project(self, project_id: int) -> QuerySet[ProductionPlan]:
        return self.model.objects.filter(project_id=project_id).order_by("-created_date", "-id")

    def list_by_status(self, status: str) -> QuerySet[ProductionPlan]:
        return self.model.objects.filter(status=status).order_by("-id")

    def get_with_resources(self, plan_id: int) -> Optional[ProductionPlan]:
        return self.model.objects.filter(pk=plan_id).prefetch_related("equipment", "personnel").first()

