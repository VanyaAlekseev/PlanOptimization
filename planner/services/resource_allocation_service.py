from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

from planner.repositories.equipment import EquipmentRepository
from planner.repositories.personnel import PersonnelRepository


ResourceType = Literal["equipment", "personnel"]


class TimeInterval(TypedDict):
    """
    Supported schedule interval representation (ISO-8601):
    {"start": "2026-02-25T08:00:00+03:00", "end": "2026-02-25T12:00:00+03:00"}
    """

    start: str
    end: str


def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover
        raise ValueError(f"Invalid ISO datetime: {value}") from exc


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


@dataclass(frozen=True)
class ResourceAllocationService:
    """
    Resource availability checks and allocation decisions.

    work_schedule JSON (supported minimal schema):
    - None: treated as "no constraints" -> available
    - {"busy": [ {"start": ISO, "end": ISO}, ... ]}: available iff requested interval does NOT overlap any busy interval
    - {"available": [ {"start": ISO, "end": ISO}, ... ]}: available iff requested interval is fully contained in at least one interval

    If schema is present but unsupported -> raises ValueError (explicit, no hidden assumptions).
    """

    equipment_repo: EquipmentRepository
    personnel_repo: PersonnelRepository

    def check_availability(
        self,
        resource_type: ResourceType,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        schedule = self._get_work_schedule(resource_type=resource_type, resource_id=resource_id)
        if schedule is None:
            return True

        if not isinstance(schedule, dict):
            raise ValueError("work_schedule must be a JSON object")

        busy = schedule.get("busy")
        available = schedule.get("available")

        if busy is not None and available is not None:
            raise ValueError("work_schedule must contain only one of: 'busy' or 'available'")

        if busy is not None:
            intervals = self._parse_intervals(busy)
            return not any(_overlaps(start_time, end_time, s, e) for s, e in intervals)

        if available is not None:
            intervals = self._parse_intervals(available)
            return any(start_time >= s and end_time <= e for s, e in intervals)

        raise ValueError("Unsupported work_schedule schema. Expected keys: 'busy' or 'available'.")

    def _get_work_schedule(self, *, resource_type: ResourceType, resource_id: int) -> Optional[Any]:
        if resource_type == "equipment":
            obj = self.equipment_repo.get_by_id(resource_id)
            if obj is None:
                raise ValueError(f"Equipment {resource_id} not found")
            return obj.work_schedule

        if resource_type == "personnel":
            obj = self.personnel_repo.get_by_id(resource_id)
            if obj is None:
                raise ValueError(f"Personnel {resource_id} not found")
            return obj.work_schedule

        raise ValueError(f"Unsupported resource_type: {resource_type}")

    def _parse_intervals(self, raw: Any) -> list[tuple[datetime, datetime]]:
        if not isinstance(raw, list):
            raise ValueError("Schedule intervals must be a JSON array")

        parsed: list[tuple[datetime, datetime]] = []
        for item in raw:
            if not isinstance(item, dict) or "start" not in item or "end" not in item:
                raise ValueError("Each interval must be an object with 'start' and 'end'")
            s = _parse_dt(str(item["start"]))
            e = _parse_dt(str(item["end"]))
            if e <= s:
                raise ValueError("Interval end must be after start")
            parsed.append((s, e))

        return parsed

