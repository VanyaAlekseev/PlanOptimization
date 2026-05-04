from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from planner.models import Equipment, Personnel
from planner.optimization.base import Operation, OperationId


@dataclass
class _ResourceInstanceEquipment:
    equipment: Equipment
    free_time: float = 0.0
    busy_intervals: List[Tuple[datetime, datetime]] | None = None
    available_intervals: List[Tuple[datetime, datetime]] | None = None


@dataclass
class _ResourceInstancePersonnel:
    personnel: Personnel
    free_time: float = 0.0
    busy_intervals: List[Tuple[datetime, datetime]] | None = None
    available_intervals: List[Tuple[datetime, datetime]] | None = None


def _parse_iso_dt(value: object) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_calendar(schedule: object) -> tuple[List[Tuple[datetime, datetime]] | None, List[Tuple[datetime, datetime]] | None]:
    """
    Поддерживает ту же базовую схему, что ResourceAllocationService:
    - {"busy": [{"start": ISO, "end": ISO}, ...]}
    - {"available": [{"start": ISO, "end": ISO}, ...]}
    Прочие ключи (например monthly_hours) игнорируются.
    """
    if not isinstance(schedule, dict):
        return None, None

    busy_raw = schedule.get("busy")
    available_raw = schedule.get("available")
    if busy_raw is not None and available_raw is not None:
        # Конфликтующая схема -> игнорируем календарь для оптимизатора.
        return None, None

    def _parse_intervals(raw: object) -> List[Tuple[datetime, datetime]] | None:
        if raw is None:
            return None
        if not isinstance(raw, list):
            return None
        out: List[Tuple[datetime, datetime]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            s = _parse_iso_dt(item.get("start"))
            e = _parse_iso_dt(item.get("end"))
            if s is None or e is None or e <= s:
                continue
            out.append((s, e))
        if not out:
            return None
        out.sort(key=lambda x: x[0])
        return out

    return _parse_intervals(busy_raw), _parse_intervals(available_raw)


def _hours_to_dt(hours_since_start: float, base_date: date) -> datetime:
    return datetime.combine(base_date, time.min) + timedelta(hours=float(hours_since_start))


def _dt_to_hours(dt: datetime, base_date: date) -> float:
    base = datetime.combine(base_date, time.min)
    return (dt - base).total_seconds() / 3600.0


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _resource_available_at(
    start: datetime,
    end: datetime,
    *,
    busy_intervals: List[Tuple[datetime, datetime]] | None,
    available_intervals: List[Tuple[datetime, datetime]] | None,
) -> bool:
    if busy_intervals:
        for s, e in busy_intervals:
            if _overlaps(start, end, s, e):
                return False
    if available_intervals:
        for s, e in available_intervals:
            if start >= s and end <= e:
                return True
        return False
    return True


def _next_resource_time(
    candidate: datetime,
    duration_hours: float,
    *,
    busy_intervals: List[Tuple[datetime, datetime]] | None,
    available_intervals: List[Tuple[datetime, datetime]] | None,
) -> Optional[datetime]:
    end = candidate + timedelta(hours=duration_hours)
    if _resource_available_at(candidate, end, busy_intervals=busy_intervals, available_intervals=available_intervals):
        return candidate

    # Если есть доступные окна, ищем ближайшее окно, в которое помещается операция.
    if available_intervals:
        best: Optional[datetime] = None
        for s, e in available_intervals:
            start = max(candidate, s)
            if start + timedelta(hours=duration_hours) <= e:
                if best is None or start < best:
                    best = start
        return best

    # Если только busy-интервалы, сдвигаем старт к концу ближайшего пересечения.
    if busy_intervals:
        next_candidate = candidate
        moved = False
        for s, e in busy_intervals:
            if _overlaps(next_candidate, next_candidate + timedelta(hours=duration_hours), s, e):
                if e > next_candidate:
                    next_candidate = e
                    moved = True
        return next_candidate if moved else candidate

    return candidate


def _equipment_required_matches(equipment: Equipment, equipment_required: object) -> bool:
    """
    TechProcess.equipment_required в текущем импорте часто имеет вид {"name": "..."}.
    На stage-1 допускаем и {"type": "..."}.
    """
    if equipment_required is None or equipment_required == "" or equipment_required == {}:
        return True

    if isinstance(equipment_required, str):
        # Иногда оборудование может храниться как строка.
        return equipment.name == equipment_required or equipment.type == equipment_required

    if isinstance(equipment_required, dict):
        required_type = equipment_required.get("type")
        if required_type:
            return equipment.type == required_type

        required_name = equipment_required.get("name")
        if required_name:
            # Часто в данных "equipment" может быть либо именем экземпляра, либо типом.
            return equipment.name == required_name or equipment.type == required_name

        # Неизвестная структура -> считаем, что ограничений нет.
        return True

    return True


def _personnel_required_matches(personnel: Personnel, required_qualification: object) -> bool:
    if required_qualification is None:
        return True
    if isinstance(required_qualification, str):
        req = required_qualification.strip()
        if not req:
            return True
        return personnel.qualification == req
    # На всякий случай: если тип не строка, считаем что ограничений нет.
    return True


def compute_cpm_makespan(operations: Dict[OperationId, Operation], edges: Dict[OperationId, List[OperationId]]) -> float:
    """
    Ресурс-независимая длительность по DAG (CPM lower bound).
    """
    if not operations:
        return 0.0

    in_degree: Dict[OperationId, int] = {op_id: 0 for op_id in operations}
    predecessors: Dict[OperationId, List[OperationId]] = {op_id: [] for op_id in operations}
    for src, dsts in edges.items():
        for dst in dsts:
            if dst in in_degree:
                in_degree[dst] += 1
                predecessors[dst].append(src)

    queue: List[OperationId] = [op_id for op_id, deg in in_degree.items() if deg == 0]
    topo: List[OperationId] = []
    while queue:
        node = queue.pop(0)
        topo.append(node)
        for succ in edges.get(node, []):
            if succ not in in_degree:
                continue
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(topo) != len(operations):
        # Невалидный граф, но не падаем.
        return sum(float(op.duration) for op in operations.values())

    earliest_finish: Dict[OperationId, float] = {}
    for op_id in topo:
        ready = max((earliest_finish[p] for p in predecessors.get(op_id, []) if p in earliest_finish), default=0.0)
        earliest_finish[op_id] = ready + float(operations[op_id].duration)
    return max(earliest_finish.values(), default=0.0)


def simulate_schedule_stage1(
    *,
    genome: List[OperationId],
    operations: Dict[OperationId, Operation],
    edges: Dict[OperationId, List[OperationId]],
    equipment_pool: List[Equipment],
    personnel_pool: List[Personnel],
    build_schedule: bool = False,
    use_work_schedule: bool = False,
    calendar_start_date: Optional[date] = None,
    cpm_makespan: Optional[float] = None,
) -> dict:
    """
    Stage-1 RCPSP:
    - порядок исполнения задается через priority-вектор genome (позиция в списке)
    - календарей смен нет: ресурс доступен, если экземпляр не занят другой операцией
    """

    if not operations:
        return {"makespan": 0.0, "human_hours": 0.0, "resource_delay": 0.0, "invalid": False, "schedule": []}

    genome_pos: Dict[OperationId, int] = {op_id: i for i, op_id in enumerate(genome)}

    predecessors: Dict[OperationId, List[OperationId]] = {op_id: [] for op_id in operations}
    for src, dsts in edges.items():
        for dst in dsts:
            if dst in predecessors:
                predecessors[dst].append(src)

    remaining_predecessors_count: Dict[OperationId, int] = {op_id: len(preds) for op_id, preds in predecessors.items()}

    ready: List[OperationId] = [op_id for op_id, cnt in remaining_predecessors_count.items() if cnt == 0]
    scheduled: set[OperationId] = set()

    equipment_instances: List[_ResourceInstanceEquipment] = []
    for equipment in equipment_pool:
        busy, available = _extract_calendar(getattr(equipment, "work_schedule", None))
        equipment_instances.append(
            _ResourceInstanceEquipment(
                equipment=equipment,
                free_time=0.0,
                busy_intervals=busy if use_work_schedule else None,
                available_intervals=available if use_work_schedule else None,
            )
        )
    personnel_instances: List[_ResourceInstancePersonnel] = []
    for personnel in personnel_pool:
        busy, available = _extract_calendar(getattr(personnel, "work_schedule", None))
        personnel_instances.append(
            _ResourceInstancePersonnel(
                personnel=personnel,
                free_time=0.0,
                busy_intervals=busy if use_work_schedule else None,
                available_intervals=available if use_work_schedule else None,
            )
        )

    end_time: Dict[OperationId, float] = {}
    resource_delay: float = 0.0
    missing_resources_count: int = 0
    calendar_conflicts_count: int = 0

    schedule: List[dict] = []
    base_date = calendar_start_date or date.today()

    while len(scheduled) < len(operations):
        if not ready:
            # Теоретически для корректного DAG не должно случаться.
            # Чтобы алгоритм не падал, завершаем "как есть".
            break

        ready.sort(
            key=lambda op_id: (
                genome_pos.get(op_id, 10**9),
                op_id[0],
                op_id[1],
            )
        )
        op_id = ready.pop(0)

        # ready_time = max(end_time(pred))
        preds = predecessors.get(op_id, [])
        ready_time = max((end_time[p] for p in preds if p in end_time), default=0.0)

        op = operations[op_id]
        tech_process = op.tech_process

        # Подбор ресурсов
        equip_candidates = [
            inst
            for inst in equipment_instances
            if _equipment_required_matches(inst.equipment, tech_process.equipment_required)
        ]
        pers_candidates = [
            inst
            for inst in personnel_instances
            if _personnel_required_matches(inst.personnel, tech_process.required_qualification)
        ]

        chosen_equip: Optional[_ResourceInstanceEquipment] = None
        chosen_pers: Optional[_ResourceInstancePersonnel] = None
        chosen_start: Optional[float] = None

        if not equip_candidates or not pers_candidates:
            missing_resources_count += 1

            # Fallback: чтобы schedule можно было построить, но такие решения будут "плохими".
            chosen_equip = equip_candidates[0] if equip_candidates else (equipment_instances[0] if equipment_instances else None)
            chosen_pers = pers_candidates[0] if pers_candidates else (personnel_instances[0] if personnel_instances else None)
            chosen_start = ready_time
        else:
            best_end = None
            for eq_inst in equip_candidates:
                for pers_inst in pers_candidates:
                    start = max(ready_time, eq_inst.free_time, pers_inst.free_time)
                    duration_h = float(op.duration)
                    if use_work_schedule:
                        # Ищем earliest feasible start с учетом календарей (stage-2).
                        for _ in range(200):
                            start_dt = _hours_to_dt(start, base_date)
                            eq_next_dt = _next_resource_time(
                                start_dt,
                                duration_h,
                                busy_intervals=eq_inst.busy_intervals,
                                available_intervals=eq_inst.available_intervals,
                            )
                            pers_next_dt = _next_resource_time(
                                start_dt,
                                duration_h,
                                busy_intervals=pers_inst.busy_intervals,
                                available_intervals=pers_inst.available_intervals,
                            )
                            if eq_next_dt is None or pers_next_dt is None:
                                start = None  # type: ignore[assignment]
                                break
                            candidate_dt = max(eq_next_dt, pers_next_dt)
                            candidate_h = _dt_to_hours(candidate_dt, base_date)
                            end_dt = candidate_dt + timedelta(hours=duration_h)
                            eq_ok = _resource_available_at(
                                candidate_dt,
                                end_dt,
                                busy_intervals=eq_inst.busy_intervals,
                                available_intervals=eq_inst.available_intervals,
                            )
                            pers_ok = _resource_available_at(
                                candidate_dt,
                                end_dt,
                                busy_intervals=pers_inst.busy_intervals,
                                available_intervals=pers_inst.available_intervals,
                            )
                            if eq_ok and pers_ok:
                                start = candidate_h
                                break
                            start = candidate_h + 1.0
                        if start is None:
                            calendar_conflicts_count += 1
                            continue

                    end = start + duration_h
                    if best_end is None or end < best_end or (end == best_end and start < (chosen_start or start)):
                        best_end = end
                        chosen_equip = eq_inst
                        chosen_pers = pers_inst
                        chosen_start = start

        if chosen_start is None and (equip_candidates and pers_candidates):
            # Кандидаты по типу/квалификации есть, но календари не дали feasible-окно.
            missing_resources_count += 1
            chosen_equip = equip_candidates[0]
            chosen_pers = pers_candidates[0]
            chosen_start = ready_time

        start = float(chosen_start if chosen_start is not None else ready_time)
        end = start + float(op.duration)

        # Ждем ресурсов (если экземпляр занят) - это и есть resource_delay в stage-1.
        resource_delay += max(0.0, start - ready_time)

        end_time[op_id] = end
        scheduled.add(op_id)

        if chosen_equip is not None:
            chosen_equip.free_time = end
        if chosen_pers is not None:
            chosen_pers.free_time = end

        if build_schedule:
            eq_payload = None
            pers_payload = None
            if chosen_equip is not None:
                eq_payload = {
                    "id": chosen_equip.equipment.id,
                    "name": chosen_equip.equipment.name,
                    "type": chosen_equip.equipment.type,
                }
            if chosen_pers is not None:
                pers_payload = {
                    "id": chosen_pers.personnel.id,
                    "full_name": chosen_pers.personnel.full_name,
                    "qualification": chosen_pers.personnel.qualification,
                }

            cid, seq = op_id
            schedule.append(
                {
                    "component_id": cid,
                    "sequence": seq,
                    "operation_name": op.name,
                    "duration": op.duration,
                    "start": start,
                    "end": end,
                    "assigned_equipment": eq_payload,
                    "assigned_personnel": pers_payload,
                }
            )

        # Update ready set using remaining predecessor counts
        for succ in edges.get(op_id, []):
            if succ not in remaining_predecessors_count:
                continue
            remaining_predecessors_count[succ] -= 1
            if remaining_predecessors_count[succ] == 0:
                ready.append(succ)

    makespan = max(end_time.values(), default=0.0)
    human_hours = sum(float(op.duration) for op in operations.values())
    invalid = missing_resources_count > 0

    if build_schedule and schedule:
        # Для Ганта/экспортов удобнее иметь операции отсортированными по старту.
        schedule = sorted(schedule, key=lambda item: (float(item.get("start", 0) or 0), float(item.get("end", 0) or 0)))

    op_count = max(1, len(operations))
    total_duration = sum(float(op.duration) for op in operations.values())
    cpm_baseline = float(cpm_makespan) if cpm_makespan and cpm_makespan > 0 else compute_cpm_makespan(operations, edges)
    if cpm_baseline <= 0:
        cpm_baseline = 1.0

    makespan_norm = float(makespan) / cpm_baseline
    human_hours_norm = float(human_hours) / max(1e-9, float(total_duration))
    resource_delay_norm = float(resource_delay) / max(1e-9, cpm_baseline * float(op_count))

    return {
        "makespan": float(makespan),
        "human_hours": float(human_hours),
        "resource_delay": float(resource_delay),
        "cpm_makespan": float(cpm_baseline),
        "makespan_norm": float(makespan_norm),
        "human_hours_norm": float(human_hours_norm),
        "resource_delay_norm": float(resource_delay_norm),
        "invalid": invalid,
        "missing_resources_count": missing_resources_count,
        "calendar_conflicts_count": calendar_conflicts_count,
        "schedule": schedule,
    }

