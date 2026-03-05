from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet

from planner.models import Product

from .base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self) -> None:
        super().__init__(model=Product)

    def list_by_project(self, project_id: int) -> QuerySet[Product]:
        return self.model.objects.filter(project_id=project_id).order_by("name")

    def get_with_components(self, product_id: int) -> Optional[Product]:
        return self.model.objects.filter(pk=product_id).prefetch_related("components_fk").first()

