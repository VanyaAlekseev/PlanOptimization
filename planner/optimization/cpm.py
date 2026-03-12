from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from planner.models import Component
from planner.optimization.base import BaseOptimizer, OperationId, build_operation_graph
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository


@dataclass(frozen=True)
class CriticalPathMethod(BaseOptimizer):
    """
    Classical Critical Path Method implementation over the operation DAG.

    Nodes are (component_id, sequence_order) pairs; durations are taken from TechProcess.unit_time
    (default 1.0 if not specified).
    """

    project_repo: ProjectRepository
    product_repo: ProductRepository
    component_repo: ComponentRepository

    def _load_operations(self, project_id: int) -> Tuple[Dict[OperationId, Any], Dict[OperationId, List[OperationId]]]:
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        products = list(project.products.all())
        components: List[Component] = []
        for product in products:
            components.extend(list(self.component_repo.list_by_product(product.id)))

        return build_operation_graph(components)

    def optimize(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        operations, edges = self._load_operations(project_id)

        if not operations:
            return {
                "project_id": project_id,
                "total_duration": 0.0,
                "operations": {},
                "critical_path": [],
            }

        # Topological sort (Kahn's algorithm)
        in_degree: Dict[OperationId, int] = {op_id: 0 for op_id in operations}
        for src, dsts in edges.items():
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        queue: List[OperationId] = [op_id for op_id, deg in in_degree.items() if deg == 0]
        topo_order: List[OperationId] = []

        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            for succ in edges.get(node, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(topo_order) != len(operations):
            raise ValueError("Operation graph contains cycles; CPM requires a DAG")

        # Forward pass: earliest start/finish
        es: Dict[OperationId, float] = {}
        ef: Dict[OperationId, float] = {}

        for node in topo_order:
            preds = [src for src, dsts in edges.items() if node in dsts]
            es[node] = max((ef[p] for p in preds), default=0.0)
            ef[node] = es[node] + operations[node].duration

        project_duration = max(ef.values())

        # Backward pass: latest start/finish
        ls: Dict[OperationId, float] = {}
        lf: Dict[OperationId, float] = {}

        for node in reversed(topo_order):
            succs = edges.get(node, [])
            lf[node] = min((ls[s] for s in succs), default=project_duration)
            ls[node] = lf[node] - operations[node].duration

        # Floats and critical path
        floats: Dict[OperationId, float] = {}
        for node in topo_order:
            floats[node] = ls[node] - es[node]

        critical_nodes = [node for node in topo_order if abs(floats[node]) < 1e-9]

        op_results: Dict[str, Any] = {}
        for op_id in topo_order:
            comp_id, seq = op_id
            op = operations[op_id]
            key = f"{comp_id}:{seq}"
            op_results[key] = {
                "component_id": comp_id,
                "sequence": seq,
                "name": op.name,
                "duration": op.duration,
                "earliest_start": es[op_id],
                "earliest_finish": ef[op_id],
                "latest_start": ls[op_id],
                "latest_finish": lf[op_id],
                "total_float": floats[op_id],
            }

        crit_path_keys = [f"{c[0]}:{c[1]}" for c in critical_nodes]

        return {
            "project_id": project_id,
            "total_duration": project_duration,
            "operations": op_results,
            "critical_path": crit_path_keys,
        }

