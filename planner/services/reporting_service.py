from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from planner.repositories.algorithm_comparison import AlgorithmComparisonRepository
from planner.repositories.production_plan import ProductionPlanRepository
from planner.repositories.project import ProjectRepository


@dataclass(frozen=True)
class ReportingService:
    """
    Reporting data generation.

    At this stage it provides stable method signatures and placeholders.
    """

    project_repo: ProjectRepository
    plan_repo: ProductionPlanRepository
    comparison_repo: AlgorithmComparisonRepository

    def get_project_summary_report_data(self, project_id: int) -> dict[str, Any]:
        project = self.project_repo.get_with_related(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        plans = list(self.plan_repo.list_by_project(project_id).values("id", "status", "algorithm_used", "created_date"))
        comparisons = list(
            self.comparison_repo.list_by_project(project_id).values(
                "id",
                "algorithm_name",
                "total_duration",
                "resource_utilization",
                "deadline_satisfaction",
                "computed_date",
            )
        )

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "start_date": project.start_date,
                "deadline": project.deadline,
                "end_date": project.end_date,
            },
            "production_plans": plans,
            "algorithm_comparisons": comparisons,
        }

