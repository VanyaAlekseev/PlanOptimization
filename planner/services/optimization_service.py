from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from planner.optimization import CriticalPathMethod, GeneticAlgorithmOptimizer, SimulatedAnnealingOptimizer
from planner.models import Equipment, Personnel
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

    def build_algorithm_chart_data(self, project_id: int, **kwargs: Any) -> Dict[str, Any]:
        result = self.compare_algorithms(project_id, **kwargs)
        rate = self._effective_hour_rate()
        return {
            "project_id": project_id,
            "hour_rate": rate,
            "cpm": self._series_from_cpm(result["cpm"], rate),
            "ga": self._series_from_schedule(result["ga"], rate, "best_fitness"),
            "sa": self._series_from_schedule(result["sa"], rate, "best_cost"),
        }

    def _effective_hour_rate(self) -> float:
        equipment_rates = [
            float(v)
            for v in Equipment.objects.exclude(cost_per_hour__isnull=True).values_list("cost_per_hour", flat=True)
        ]
        personnel_rates = [
            max(1.0, float(v) / 100.0)
            for v in Personnel.objects.exclude(monthly_hours_norm__isnull=True).values_list("monthly_hours_norm", flat=True)
        ]
        merged = equipment_rates + personnel_rates
        if not merged:
            return 1.0
        return sum(merged) / len(merged)

    def _series_from_cpm(self, cpm: Dict[str, Any], rate: float) -> Dict[str, Any]:
        ops = sorted(
            cpm.get("operations", {}).values(),
            key=lambda x: (float(x.get("earliest_finish", 0)), float(x.get("duration", 0))),
        )
        time_series: List[Dict[str, float]] = []
        money_series: List[Dict[str, float]] = []
        cumulative_time = 0.0
        cumulative_money = 0.0
        for idx, op in enumerate(ops, start=1):
            duration = float(op.get("duration", 0))
            cumulative_time = max(cumulative_time, float(op.get("earliest_finish", 0)))
            cumulative_money += duration * rate
            time_series.append({"step": float(idx), "value": cumulative_time})
            money_series.append({"step": float(idx), "value": cumulative_money})
        return {"kpi": float(cpm.get("total_duration", 0) or 0), "time_series": time_series, "money_series": money_series}

    def _series_from_schedule(self, payload: Dict[str, Any], rate: float, kpi_key: str) -> Dict[str, Any]:
        schedule = payload.get("schedule", []) or []
        time_series: List[Dict[str, float]] = []
        money_series: List[Dict[str, float]] = []
        cumulative_time = 0.0
        cumulative_money = 0.0
        for idx, item in enumerate(schedule, start=1):
            duration = float(item.get("duration", 0))
            cumulative_time += duration
            cumulative_money += duration * rate
            time_series.append({"step": float(idx), "value": cumulative_time})
            money_series.append({"step": float(idx), "value": cumulative_money})
        return {"kpi": float(payload.get(kpi_key, 0) or 0), "time_series": time_series, "money_series": money_series}

