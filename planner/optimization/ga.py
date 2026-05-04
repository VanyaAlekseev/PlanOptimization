from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from planner.optimization.base import BaseOptimizer, OperationId, build_operation_graph
from planner.optimization.resource_scheduler import compute_cpm_makespan, simulate_schedule_stage1
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository
from planner.models import Equipment, Personnel, ProductionPlanEquipment, ProductionPlanPersonnel


Genome = List[OperationId]


@dataclass(frozen=True)
class GeneticAlgorithmOptimizer(BaseOptimizer):
    """
    Genetic Algorithm для stage-1 RCPSP (resource-constrained scheduling):
    - genome трактуется как priority-вектор для выбора следующей операции из множества ready
    - fitness оценивается симуляцией расписания с лимитом экземпляров оборудования/персонала
    """

    project_repo: ProjectRepository
    product_repo: ProductRepository
    component_repo: ComponentRepository

    population_size: int = 20
    generations: int = 30
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2

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

    def _topological_genome(self, edges: Dict[OperationId, List[OperationId]]) -> Genome:
        in_degree: Dict[OperationId, int] = {}
        for src, dsts in edges.items():
            in_degree.setdefault(src, 0)
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = [node for node, deg in in_degree.items() if deg == 0]
        random.shuffle(queue)
        result: Genome = []

        while queue:
            node = queue.pop(random.randrange(len(queue)))
            result.append(node)
            for succ in edges.get(node, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        return result

    def _evaluate(
        self,
        genome: Genome,
        *,
        alpha: float,
        beta: float,
        gamma: float,
        operations: Dict[OperationId, Any],
        edges: Dict[OperationId, List[OperationId]],
        equipment_pool: List[Equipment],
        personnel_pool: List[Personnel],
        use_work_schedule: bool,
        strict_missing_resources: bool,
        calendar_start_date: Any,
        cpm_makespan: float,
    ) -> float:
        sim = simulate_schedule_stage1(
            genome=genome,
            operations=operations,  # type: ignore[arg-type]
            edges=edges,
            equipment_pool=equipment_pool,
            personnel_pool=personnel_pool,
            build_schedule=False,
            use_work_schedule=use_work_schedule,
            calendar_start_date=calendar_start_date,
            cpm_makespan=cpm_makespan,
        )

        makespan_norm = float(sim.get("makespan_norm", 0.0))
        human_hours_norm = float(sim.get("human_hours_norm", 0.0))
        resource_delay_norm = float(sim.get("resource_delay_norm", 0.0))

        score = alpha * makespan_norm + beta * human_hours_norm + gamma * resource_delay_norm
        missing = int(sim.get("missing_resources_count", 0) or 0)
        if missing > 0:
            if strict_missing_resources:
                return 1e12 + float(missing) * 1e9
            # Нехватка ресурсов => штраф.
            score += float(missing) * 100.0
        return float(score)

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

    def _crossover(self, parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
        if random.random() > self.crossover_rate:
            return parent1[:], parent2[:]

        size = len(parent1)
        a, b = sorted(random.sample(range(size), 2))
        slice1 = parent1[a:b]
        child1 = slice1 + [g for g in parent2 if g not in slice1]
        slice2 = parent2[a:b]
        child2 = slice2 + [g for g in parent1 if g not in slice2]
        return child1, child2

    def _mutate(self, genome: Genome) -> Genome:
        if random.random() > self.mutation_rate or len(genome) < 2:
            return genome
        i, j = sorted(random.sample(range(len(genome)), 2))
        genome[i], genome[j] = genome[j], genome[i]
        return genome

    def optimize(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        operations, edges, start_date = self._load_graph(project_id)
        if not operations:
            return {"project_id": project_id, "best_fitness": 0.0, "schedule": []}

        equipment_pool, personnel_pool = self._load_resource_pools(project_id)

        alpha = float(kwargs.get("alpha", 0.6))
        beta = float(kwargs.get("beta", 0.2))
        gamma = float(kwargs.get("gamma", 0.2))

        # Нормализуем веса до суммы 1.
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

        base_genome = self._topological_genome(edges)

        population: List[Genome] = []
        for _ in range(self.population_size):
            g = base_genome[:]
            random.shuffle(g)
            population.append(g)

        def fitness(g: Genome) -> float:
            return self._evaluate(
                g,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
                operations=operations,
                edges=edges,
                equipment_pool=equipment_pool,
                personnel_pool=personnel_pool,
                use_work_schedule=use_work_schedule,
                strict_missing_resources=strict_missing_resources,
                calendar_start_date=start_date,
                cpm_makespan=cpm_makespan,
            )

        best_genome = min(population, key=fitness)
        best_score = fitness(best_genome)

        for _ in range(self.generations):
            scored = sorted(((fitness(g), g) for g in population), key=lambda x: x[0])
            population = [g for _, g in scored[: max(2, self.population_size // 2)]]

            while len(population) < self.population_size:
                parents = random.sample(population, 2)
                child1, child2 = self._crossover(parents[0], parents[1])
                child1 = self._mutate(child1)
                child2 = self._mutate(child2)
                population.extend([child1, child2])

            candidate = min(population, key=fitness)
            candidate_score = fitness(candidate)
            if candidate_score < best_score:
                best_score = candidate_score
                best_genome = candidate

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
            "best_fitness": float(best_sim["makespan"]),
            "schedule": best_sim["schedule"],
            "human_hours": float(best_sim["human_hours"]),
            "resource_delay": float(best_sim["resource_delay"]),
            "makespan_norm": float(best_sim.get("makespan_norm", 0.0)),
            "human_hours_norm": float(best_sim.get("human_hours_norm", 0.0)),
            "resource_delay_norm": float(best_sim.get("resource_delay_norm", 0.0)),
            "missing_resources_count": int(best_sim.get("missing_resources_count", 0) or 0),
            "calendar_conflicts_count": int(best_sim.get("calendar_conflicts_count", 0) or 0),
            "use_work_schedule": use_work_schedule,
            "strict_missing_resources": strict_missing_resources,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        }

