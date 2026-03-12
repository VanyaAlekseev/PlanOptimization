from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from planner.optimization import CriticalPathMethod, GeneticAlgorithmOptimizer, SimulatedAnnealingOptimizer
from planner.repositories.component import ComponentRepository
from planner.repositories.product import ProductRepository
from planner.repositories.project import ProjectRepository


@dataclass(frozen=True)
class OptimizationService:
    """
    Facade over available optimization algorithms.

    compare_algorithms(project_id) executes CPM, GA and SA and returns a dict
    suitable for later persistence into AlgorithmComparison entities.
    """

    project_repo: ProjectRepository
    product_repo: ProductRepository
    component_repo: ComponentRepository

    def _build_cpm(self) -> CriticalPathMethod:
        return CriticalPathMethod(
            project_repo=self.project_repo,
            product_repo=self.product_repo,
            component_repo=self.component_repo,
        )

    def _build_ga(self) -> GeneticAlgorithmOptimizer:
        return GeneticAlgorithmOptimizer(
            project_repo=self.project_repo,
            product_repo=self.product_repo,
            component_repo=self.component_repo,
        )

    def _build_sa(self) -> SimulatedAnnealingOptimizer:
        return SimulatedAnnealingOptimizer(
            project_repo=self.project_repo,
            product_repo=self.product_repo,
            component_repo=self.component_repo,
        )

    def compare_algorithms(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        cpm = self._build_cpm().optimize(project_id, **kwargs)
        ga = self._build_ga().optimize(project_id, **kwargs)
        sa = self._build_sa().optimize(project_id, **kwargs)

        return {
            "project_id": project_id,
            "cpm": cpm,
            "ga": ga,
            "sa": sa,
        }

