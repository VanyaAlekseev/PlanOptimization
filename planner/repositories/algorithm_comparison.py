from __future__ import annotations

from django.db.models import QuerySet

from planner.models import AlgorithmComparison

from .base import BaseRepository


class AlgorithmComparisonRepository(BaseRepository[AlgorithmComparison]):
    def __init__(self) -> None:
        super().__init__(model=AlgorithmComparison)

    def list_by_project(self, project_id: int) -> QuerySet[AlgorithmComparison]:
        return self.model.objects.filter(project_id=project_id).order_by("-computed_date", "-id")

