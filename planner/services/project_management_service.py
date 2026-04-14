from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from planner.models import ProductionPlan, ProductionPlanEquipment, ProductionPlanPersonnel
from planner.repositories.project import ProjectRepository
from planner.repositories.equipment import EquipmentRepository
from planner.repositories.personnel import PersonnelRepository


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
    equipment_repo: EquipmentRepository | None = None
    personnel_repo: PersonnelRepository | None = None

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

    def validate_resource_capacity_for_project(
        self,
        *,
        required_hours: Decimal,
        start_date: Optional[date],
        deadline: Optional[date],
    ) -> dict[str, float]:
        if required_hours <= 0:
            return {"required_hours": 0.0, "personnel_hours": 0.0, "equipment_hours": 0.0}
        if start_date is None or deadline is None or deadline < start_date:
            raise ValueError("Для проверки ресурсов укажите корректные start_date и deadline")
        if self.personnel_repo is None or self.equipment_repo is None:
            raise ValueError("Resource repositories are required for capacity validation")

        total_days = (deadline - start_date).days + 1
        months_factor = total_days / 30.0

        personnel = list(self.personnel_repo.list())
        equipment = list(self.equipment_repo.list())
        if not personnel or not equipment:
            raise ValueError("Недостаточно ресурсов: требуется минимум 1 сотрудник и 1 единица оборудования")

        personnel_hours = 0.0
        for p in personnel:
            norm = float(p.monthly_hours_norm or 0)
            load = float(p.current_load_percent or 0)
            availability = max(0.0, 1.0 - (load / 100.0))
            personnel_hours += norm * availability * months_factor

        equipment_hours = 0.0
        for e in equipment:
            equipment_hours += self._equipment_available_hours(e.work_schedule, months_factor)

        required = float(required_hours)
        if personnel_hours < required or equipment_hours < required:
            raise ValueError(
                "Недостаточно ресурсов для проекта: "
                f"требуется {required:.2f} ч, персонал {personnel_hours:.2f} ч, оборудование {equipment_hours:.2f} ч"
            )

        return {
            "required_hours": required,
            "personnel_hours": personnel_hours,
            "equipment_hours": equipment_hours,
        }

    def release_project_resources(self, project_id: int) -> int:
        plan_ids = list(
            ProductionPlan.objects.filter(project_id=project_id).values_list("id", flat=True)
        )
        if not plan_ids:
            return 0
        removed_links = ProductionPlanEquipment.objects.filter(production_plan_id__in=plan_ids).delete()[0]
        removed_links += ProductionPlanPersonnel.objects.filter(production_plan_id__in=plan_ids).delete()[0]
        ProductionPlan.objects.filter(id__in=plan_ids).update(status="paused")
        return int(removed_links)

    def _equipment_available_hours(self, schedule: Any, months_factor: float) -> float:
        default_monthly = 160.0
        if not isinstance(schedule, dict):
            return default_monthly * months_factor
        monthly = schedule.get("monthly_hours")
        try:
            monthly_float = float(monthly)
            if monthly_float <= 0:
                monthly_float = default_monthly
        except (TypeError, ValueError):
            monthly_float = default_monthly
        return monthly_float * months_factor

