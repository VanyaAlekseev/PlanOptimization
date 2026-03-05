from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet

from planner.models import Component

from .base import BaseRepository


class ComponentRepository(BaseRepository[Component]):
    def __init__(self) -> None:
        super().__init__(model=Component)

    def list_by_product(self, product_id: int) -> QuerySet[Component]:
        return self.model.objects.filter(product_id=product_id).order_by("id")

    def list_roots(self, product_id: int) -> QuerySet[Component]:
        return self.model.objects.filter(product_id=product_id, parent_component_id__isnull=True).order_by("id")

    def list_children(self, parent_component_id: int) -> QuerySet[Component]:
        return self.model.objects.filter(parent_component_id=parent_component_id).order_by("id")

    def get_with_tech_processes(self, component_id: int) -> Optional[Component]:
        return self.model.objects.filter(pk=component_id).prefetch_related("tech_processes").first()

