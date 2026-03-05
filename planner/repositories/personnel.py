from __future__ import annotations

from django.db.models import QuerySet

from planner.models import Personnel

from .base import BaseRepository


class PersonnelRepository(BaseRepository[Personnel]):
    def __init__(self) -> None:
        super().__init__(model=Personnel)

    def list_by_position(self, position: str) -> QuerySet[Personnel]:
        return self.model.objects.filter(position=position).order_by("full_name")

