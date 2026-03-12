from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from planner.models import Component, TechProcess


OperationId = Tuple[int, int]  # (component_id, sequence_order)


@dataclass(frozen=True)
class Operation:
    id: OperationId
    name: str
    duration: float
    component: Component
    tech_process: TechProcess


def build_operation_graph(components: List[Component]) -> Tuple[Dict[OperationId, Operation], Dict[OperationId, List[OperationId]]]:
    """
    Build a graph of operations from components and their tech processes.

    - Node: (component_id, sequence_order)
    - Edges: from dependency sequence to operation sequence within the same component,
      based on Component.dependencies["operations"] structure.
    """
    operations: Dict[OperationId, Operation] = {}
    edges: Dict[OperationId, List[OperationId]] = {}

    for component in components:
        tech_processes = list(component.tech_processes.all())
        by_seq: Dict[int, TechProcess] = {
            tp.sequence_order: tp for tp in tech_processes if tp.sequence_order is not None
        }

        deps_data = (component.dependencies or {}).get("operations", [])  # type: ignore[union-attr]
        deps_by_seq: Dict[int, Any] = {}
        for item in deps_data:
            seq = item.get("sequence")
            if isinstance(seq, int):
                deps_by_seq[seq] = item

        for seq, tp in by_seq.items():
            op_id: OperationId = (component.id, seq)
            duration = float(tp.unit_time or 1)
            operations[op_id] = Operation(
                id=op_id,
                name=tp.name,
                duration=duration,
                component=component,
                tech_process=tp,
            )
            edges.setdefault(op_id, [])

        for seq, meta in deps_by_seq.items():
            op_id = (component.id, seq)
            if op_id not in operations:
                continue
            depends_on = meta.get("depends_on", []) or []
            for dep_seq in depends_on:
                dep_id = (component.id, int(dep_seq))
                if dep_id in operations:
                    edges.setdefault(dep_id, []).append(op_id)

    return operations, edges


class BaseOptimizer(ABC):
    @abstractmethod
    def optimize(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute optimization for a given project and return a dict-like plan representation.
        """

