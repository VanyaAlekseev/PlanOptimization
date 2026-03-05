from __future__ import annotations

from django.db.models import QuerySet

from planner.models import TechProcess

from .base import BaseRepository


class TechProcessRepository(BaseRepository[TechProcess]):
    def __init__(self) -> None:
        super().__init__(model=TechProcess)

    def list_ordered(self) -> QuerySet[TechProcess]:
        return self.model.objects.all().order_by("sequence_order", "id")

