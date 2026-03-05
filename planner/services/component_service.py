from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.db import transaction

from planner.models import Component
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository


ComponentTreeNode = dict[str, Any]


@dataclass(frozen=True)
class ComponentService:
    """
    Component hierarchy operations and integrity validation.

    XML import:
    - At this stage it's a stub (placeholder) to be implemented after agreeing XML schema.
    """

    component_repo: ComponentRepository
    product_repo: ProductRepository

    def build_component_tree(self, product_id: int) -> ComponentTreeNode:
        """
        Build a component tree for the given product, using parent_component_id.

        Returns a JSON-serializable structure:
        {
          "product_id": int,
          "roots": [
            {"id": int, "name": str, "type": str, "quantity": int|None, "children": [...]},
            ...
          ]
        }
        """
        product = self.product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        components = list(
            self.component_repo.list_by_product(product_id).values(
                "id",
                "name",
                "type",
                "quantity",
                "parent_component_id",
            )
        )

        by_id: dict[int, ComponentTreeNode] = {}
        roots: list[ComponentTreeNode] = []

        for row in components:
            node: ComponentTreeNode = {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "quantity": row["quantity"],
                "children": [],
            }
            by_id[row["id"]] = node

        for row in components:
            node = by_id[row["id"]]
            parent_id = row["parent_component_id"]
            if parent_id is None:
                roots.append(node)
                continue

            parent = by_id.get(parent_id)
            if parent is None:
                # Broken reference: keep as root to avoid data loss; validation can catch it explicitly.
                roots.append(node)
                continue

            parent["children"].append(node)

        return {"product_id": product_id, "roots": roots}

    def validate_dependencies(self, component: Component) -> list[str]:
        """
        Validate dependency JSON structure.

        Current behavior:
        - only validates that 'dependencies' is a JSON object or null
        - deeper semantic validation is deferred until dependency schema is agreed.
        """
        if component.dependencies is None:
            return []
        if not isinstance(component.dependencies, dict):
            return ["Field 'dependencies' must be a JSON object"]
        return []

    @transaction.atomic
    def import_from_xml_stub(self, product_id: int, xml_content: str, *, overwrite: bool = False) -> None:
        """
        Placeholder for XML import.

        Contract (stub):
        - Validates product existence
        - Optionally deletes existing components if overwrite=True
        - Raises NotImplementedError for actual parsing/mapping
        """
        product = self.product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        if overwrite:
            self.component_repo.list(filters={"product_id": product_id}).delete()

        raise NotImplementedError(
            "XML import is not implemented yet. Please provide/confirm XML schema for products/components."
        )

