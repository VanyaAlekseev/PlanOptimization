from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List

from planner.optimization.base import BaseOptimizer, OperationId, build_operation_graph
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository


Genome = List[OperationId]


@dataclass(frozen=True)
class SimulatedAnnealingOptimizer(BaseOptimizer):
    """
    Оптимизатор на основе метода имитации отжига, направленный на минимизацию общего трудозатрат.

Цель: total_time (сумма продолжительности операций).
    """

    project_repo: ProjectRepository
    product_repo: ProductRepository
    component_repo: ComponentRepository

    initial_temperature: float = 10.0
    cooling_rate: float = 0.95
    iterations_per_temp: int = 20

    def _load_graph(self, project_id: int):
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        products = list(project.products.all())
        components = []
        for p in products:
            components.extend(list(self.component_repo.list_by_product(p.id)))
        return build_operation_graph(components)

    def _initial_genome(self, edges) -> Genome:
        # Simple topological-like order ignoring randomness here.
        in_degree: Dict[OperationId, int] = {}
        for src, dsts in edges.items():
            in_degree.setdefault(src, 0)
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1
        queue = [n for n, d in in_degree.items() if d == 0]
        result: Genome = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for succ in edges.get(node, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)
        return result

    def _cost(self, genome: Genome, durations: Dict[OperationId, float]) -> float:
        return sum(durations[g] for g in genome)

    def _neighbor(self, genome: Genome) -> Genome:
        g = genome[:]
        if len(g) < 2:
            return g
        i, j = sorted(random.sample(range(len(g)), 2))
        g[i], g[j] = g[j], g[i]
        return g

    def optimize(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        operations, edges = self._load_graph(project_id)
        if not operations:
            return {"project_id": project_id, "best_cost": 0.0, "schedule": []}

        durations = {op_id: float(op.duration) for op_id, op in operations.items()}

        current_genome = self._initial_genome(edges)
        current_cost = self._cost(current_genome, durations)
        best_genome = current_genome[:]
        best_cost = current_cost

        temperature = float(kwargs.get("initial_temperature", self.initial_temperature))
        cooling_rate = float(kwargs.get("cooling_rate", self.cooling_rate))
        iterations_per_temp = int(kwargs.get("iterations_per_temp", self.iterations_per_temp))

        while temperature > 1e-3:
            for _ in range(iterations_per_temp):
                neighbor = self._neighbor(current_genome)
                neighbor_cost = self._cost(neighbor, durations)
                delta = neighbor_cost - current_cost
                if delta < 0:
                    current_genome, current_cost = neighbor, neighbor_cost
                else:
                    prob = math.exp(-delta / temperature)
                    if random.random() < prob:
                        current_genome, current_cost = neighbor, neighbor_cost

                if current_cost < best_cost:
                    best_cost = current_cost
                    best_genome = current_genome[:]

            temperature *= cooling_rate

        schedule = [
            {
                "component_id": cid,
                "sequence": seq,
                "operation_name": operations[(cid, seq)].name,
                "duration": operations[(cid, seq)].duration,
            }
            for (cid, seq) in best_genome
        ]

        return {
            "project_id": project_id,
            "best_cost": best_cost,
            "schedule": schedule,
            "initial_temperature": temperature,
            "cooling_rate": cooling_rate,
        }

