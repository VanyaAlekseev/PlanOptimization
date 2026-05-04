from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List

from planner.optimization.base import BaseOptimizer, OperationId, build_operation_graph
from planner.optimization.resource_scheduler import compute_cpm_makespan, simulate_schedule_stage1
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository
from planner.models import Equipment, Personnel, ProductionPlanEquipment, ProductionPlanPersonnel


Genome = List[OperationId]


@dataclass(frozen=True)
class SimulatedAnnealingOptimizer(BaseOptimizer):
    """
    Simulated Annealing для stage-1 RCPSP (resource-constrained scheduling).
    Вычисление cost производится симуляцией расписания с ограниченными экземплярами ресурсов.
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
        operations, edges = build_operation_graph(components)
        return operations, edges, project.start_date

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

    def _load_resource_pools(self, project_id: int) -> tuple[List[Equipment], List[Personnel]]:
        eq_links = (
            ProductionPlanEquipment.objects.filter(production_plan__project_id=project_id).select_related("equipment")
        )
        equipment_by_id: dict[int, Equipment] = {}
        for link in eq_links:
            equipment_by_id[link.equipment_id] = link.equipment

        pers_links = (
            ProductionPlanPersonnel.objects.filter(production_plan__project_id=project_id).select_related("personnel")
        )
        personnel_by_id: dict[int, Personnel] = {}
        for link in pers_links:
            personnel_by_id[link.personnel_id] = link.personnel

        return list(equipment_by_id.values()), list(personnel_by_id.values())

    def _neighbor(self, genome: Genome) -> Genome:
        g = genome[:]
        if len(g) < 2:
            return g
        i, j = sorted(random.sample(range(len(g)), 2))
        g[i], g[j] = g[j], g[i]
        return g

    def optimize(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        operations, edges, start_date = self._load_graph(project_id)
        if not operations:
            return {"project_id": project_id, "best_cost": 0.0, "schedule": []}

        equipment_pool, personnel_pool = self._load_resource_pools(project_id)

        alpha = float(kwargs.get("alpha", 0.6))
        beta = float(kwargs.get("beta", 0.2))
        gamma = float(kwargs.get("gamma", 0.2))

        s = alpha + beta + gamma
        if s <= 0:
            alpha, beta, gamma = 1.0, 0.0, 0.0
        else:
            alpha /= s
            beta /= s
            gamma /= s

        use_work_schedule = bool(kwargs.get("use_work_schedule", False))
        strict_missing_resources = bool(kwargs.get("strict_missing_resources", False))
        cpm_makespan = compute_cpm_makespan(operations, edges)

        current_genome = self._initial_genome(edges)

        def score(genome: Genome) -> float:
            sim = simulate_schedule_stage1(
                genome=genome,
                operations=operations,
                edges=edges,
                equipment_pool=equipment_pool,
                personnel_pool=personnel_pool,
                build_schedule=False,
                use_work_schedule=use_work_schedule,
                calendar_start_date=start_date,
                cpm_makespan=cpm_makespan,
            )
            makespan_norm = float(sim.get("makespan_norm", 0.0))
            human_hours_norm = float(sim.get("human_hours_norm", 0.0))
            resource_delay_norm = float(sim.get("resource_delay_norm", 0.0))
            sc = alpha * makespan_norm + beta * human_hours_norm + gamma * resource_delay_norm
            missing = int(sim.get("missing_resources_count", 0) or 0)
            if missing > 0:
                if strict_missing_resources:
                    return 1e12 + float(missing) * 1e9
                sc += float(missing) * 100.0
            return float(sc)

        current_cost = score(current_genome)
        best_genome = current_genome[:]
        best_score = current_cost

        temperature = float(kwargs.get("initial_temperature", self.initial_temperature))
        cooling_rate = float(kwargs.get("cooling_rate", self.cooling_rate))
        iterations_per_temp = int(kwargs.get("iterations_per_temp", self.iterations_per_temp))

        while temperature > 1e-3:
            for _ in range(iterations_per_temp):
                neighbor = self._neighbor(current_genome)
                neighbor_cost = score(neighbor)
                delta = neighbor_cost - current_cost
                if delta < 0:
                    current_genome, current_cost = neighbor, neighbor_cost
                else:
                    prob = math.exp(-delta / temperature)
                    if random.random() < prob:
                        current_genome, current_cost = neighbor, neighbor_cost

                if current_cost < best_score:
                    best_score = current_cost
                    best_genome = current_genome[:]

            temperature *= cooling_rate

        best_sim = simulate_schedule_stage1(
            genome=best_genome,
            operations=operations,
            edges=edges,
            equipment_pool=equipment_pool,
            personnel_pool=personnel_pool,
            build_schedule=True,
            use_work_schedule=use_work_schedule,
            calendar_start_date=start_date,
            cpm_makespan=cpm_makespan,
        )

        return {
            "project_id": project_id,
            "best_score": best_score,
            "best_cost": float(best_sim["makespan"]),
            "schedule": best_sim["schedule"],
            "human_hours": float(best_sim["human_hours"]),
            "resource_delay": float(best_sim["resource_delay"]),
            "makespan_norm": float(best_sim.get("makespan_norm", 0.0)),
            "human_hours_norm": float(best_sim.get("human_hours_norm", 0.0)),
            "resource_delay_norm": float(best_sim.get("resource_delay_norm", 0.0)),
            "missing_resources_count": int(best_sim.get("missing_resources_count", 0) or 0),
            "calendar_conflicts_count": int(best_sim.get("calendar_conflicts_count", 0) or 0),
            "initial_temperature": temperature,
            "cooling_rate": cooling_rate,
            "use_work_schedule": use_work_schedule,
            "strict_missing_resources": strict_missing_resources,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        }

