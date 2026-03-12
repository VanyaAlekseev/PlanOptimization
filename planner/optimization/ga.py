from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from planner.optimization.base import BaseOptimizer, OperationId, build_operation_graph
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository


Genome = List[OperationId]


@dataclass(frozen=True)
class GeneticAlgorithmOptimizer(BaseOptimizer):
    """
    Базовый генетический алгоритм для многокритериальной оптимизации.

Функция оценки:
score = alpha * total_time + beta * human_hours + gamma * resource_utilization
где все компоненты в настоящее время аппроксимируются с помощью total_time, чтобы избежать 
скрытых допущений о календарях ресурсов; коэффициенты задаются с помощью kwargs 
(alpha/beta/gamma, по умолчанию 1,0/1,0/1,0).
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
        return build_operation_graph(components)

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
        durations: Dict[OperationId, float],
        *,
        alpha: float,
        beta: float,
        gamma: float,
    ) -> float:
        total_time = sum(durations[g] for g in genome)
        human_hours = total_time
        resource_utilization = total_time
        return alpha * total_time + beta * human_hours + gamma * resource_utilization

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
        operations, edges = self._load_graph(project_id)
        if not operations:
            return {"project_id": project_id, "best_fitness": 0.0, "schedule": []}

        alpha = float(kwargs.get("alpha", 1.0))
        beta = float(kwargs.get("beta", 1.0))
        gamma = float(kwargs.get("gamma", 1.0))

        durations = {op_id: float(op.duration) for op_id, op in operations.items()}
        base_genome = self._topological_genome(edges)

        population: List[Genome] = []
        for _ in range(self.population_size):
            g = base_genome[:]
            random.shuffle(g)
            population.append(g)

        def fitness(g: Genome) -> float:
            return self._evaluate(g, durations, alpha=alpha, beta=beta, gamma=gamma)

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
            "best_fitness": best_score,
            "schedule": schedule,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        }

