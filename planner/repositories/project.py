from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet

from planner.models import Project

from .base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self) -> None:
        super().__init__(model=Project)

    def list_by_status(self, status: str) -> QuerySet[Project]:
        return self.model.objects.filter(status=status).order_by("-id")

    def get_with_related(self, project_id: int) -> Optional[Project]:
        return (
            self.model.objects.filter(pk=project_id)
            .prefetch_related("products", "production_plans", "algorithm_comparisons")
            .first()
        )

