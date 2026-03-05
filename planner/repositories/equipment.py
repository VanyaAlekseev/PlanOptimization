from __future__ import annotations

from django.db.models import QuerySet

from planner.models import Equipment

from .base import BaseRepository


class EquipmentRepository(BaseRepository[Equipment]):
    def __init__(self) -> None:
        super().__init__(model=Equipment)

    def list_by_type(self, equipment_type: str) -> QuerySet[Equipment]:
        return self.model.objects.filter(type=equipment_type).order_by("name")

