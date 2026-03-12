from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from xml.etree import ElementTree as ET

from django.db import transaction

from planner.models import Component, ComponentTechProcess
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.tech_process import TechProcessRepository


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
    tech_process_repo: TechProcessRepository

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
    def import_from_xml(self, product_id: int, xml_content: str, *, overwrite: bool = False) -> None:
        """
        Import product component structure and tech processes from an XML document.

        Assumptions based on the provided example:
        - Root element contains <product> with nested <components>.
        - Each <component> has attributes: id (XML identifier), name, type, quantity.
        - Nested <tech_process>/<operation> describe operations for a component.
        - Operation dependencies are expressed as:
          <dependencies><depends_on operation_id="1"/></dependencies>
          and are stored in Component.dependencies JSON as:
          {"operations": [{"sequence": int, "depends_on": [int, ...]}, ...]}.
        - Child components are nested under <children>.
        """
        product = self.product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        if overwrite:
            self.component_repo.list(filters={"product_id": product_id}).delete()

        root = ET.fromstring(xml_content)

        xml_product = root.find(".//product")
        if xml_product is None:
            raise ValueError("XML does not contain <product> element")

        # Optionally sync basic attributes from XML.
        product.name = xml_product.get("name", product.name)
        code = xml_product.get("code")
        if code:
            product.code = code
        p_type = xml_product.get("type")
        if p_type:
            product.type = p_type
        product.save(update_fields=["name", "code", "type"])

        components_root = xml_product.find("components")
        if components_root is None:
            return

        xml_id_to_component: dict[str, Component] = {}

        def _parse_component(elem: ET.Element, parent: Optional[Component]) -> Component:
            xml_id = elem.get("id")
            name = elem.get("name") or ""
            c_type = elem.get("type") or ""
            quantity_raw = elem.get("quantity")
            quantity = int(quantity_raw) if quantity_raw is not None else None

            component = self.component_repo.create(
                product=product,
                parent_component=parent,
                name=name,
                type=c_type,
                quantity=quantity,
            )

            if xml_id:
                xml_id_to_component[xml_id] = component

            # Parse tech_process / operations for this component.
            tech_process_elem = elem.find("tech_process")
            if tech_process_elem is not None:
                operations_meta: list[dict[str, Any]] = []
                for op_elem in tech_process_elem.findall("operation"):
                    op_name = op_elem.get("name") or ""
                    seq_raw = op_elem.get("sequence")
                    sequence = int(seq_raw) if seq_raw is not None else None

                    tech_proc = self.tech_process_repo.create(
                        name=op_name,
                        description="",
                        required_qualification="",
                        equipment_required=None,
                        prep_time=None,
                        unit_time=None,
                        sequence_order=sequence,
                    )
                    ComponentTechProcess.objects.create(component=component, tech_process=tech_proc)

                    depends_on_ids: list[int] = []
                    deps_elem = op_elem.find("dependencies")
                    if deps_elem is not None:
                        for dep in deps_elem.findall("depends_on"):
                            dep_raw = dep.get("operation_id")
                            if dep_raw is not None:
                                try:
                                    depends_on_ids.append(int(dep_raw))
                                except ValueError:
                                    continue

                    operations_meta.append(
                        {
                            "sequence": sequence,
                            "depends_on": depends_on_ids,
                        }
                    )

                if operations_meta:
                    component.dependencies = {"operations": operations_meta}
                    component.save(update_fields=["dependencies"])

            # Recurse into children.
            children_elem = elem.find("children")
            if children_elem is not None:
                for child in children_elem.findall("component"):
                    _parse_component(child, parent=component)

            return component

        for comp_elem in components_root.findall("component"):
            _parse_component(comp_elem, parent=None)


