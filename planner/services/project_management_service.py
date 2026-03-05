from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from planner.repositories.project import ProjectRepository


@dataclass(frozen=True)
class ProjectManagementService:
    """
    Project lifecycle management and high-level project metrics.

    Progress is currently computed from project calendar dates:
    - if end_date is set -> 1.0
    - else if start_date and deadline are set -> elapsed/total clamped to [0, 1]
    - else -> None (insufficient data)

    This avoids hidden assumptions about production plan structure at this stage.
    """

    project_repo: ProjectRepository

    def get_progress(self, project_id: int, *, today: Optional[date] = None) -> Optional[float]:
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            return None

        if project.end_date:
            return 1.0

        if not project.start_date or not project.deadline:
            return None

        if today is None:
            today = date.today()

        total_days = (project.deadline - project.start_date).days
        if total_days <= 0:
            return None

        elapsed = (today - project.start_date).days
        progress = elapsed / total_days
        if progress < 0:
            return 0.0
        if progress > 1:
            return 1.0
        return float(progress)

