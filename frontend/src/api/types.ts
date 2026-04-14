// Общие DTO для API backend.

export interface ProjectDto {
  id: number;
  name: string;
  description: string;
  status: string;
  start_date: string | null;
  deadline: string | null;
  end_date: string | null;
  total_labor_planned: number | null;
  total_labor_actual: number | null;
}

export interface ProductDto {
  id: number;
  project: number;
  name: string;
  code: string;
  type: string;
  structure_tree: Record<string, unknown> | null;
  tech_requirements: string;
  norm_hours: number | null;
}

export interface ComponentTreeNodeDto {
  id: number;
  name: string;
  type: string;
  quantity: number | null;
  children: ComponentTreeNodeDto[];
}

export interface ComponentTreeDto {
  product_id: number;
  roots: ComponentTreeNodeDto[];
}

export interface ComponentDto {
  id: number;
  product: number;
  parent_component: number | null;
  name: string;
  type: string;
  quantity: number | null;
  parameters: Record<string, unknown> | null;
  labor_per_operation: number | null;
  dependencies: Record<string, unknown> | null;
}

export interface AlgorithmComparisonDto {
  id: number;
  project: number;
  algorithm_name: string;
  total_duration: number;
  resource_utilization: number;
  deadline_satisfaction: number;
  computed_date: string | null;
}

export interface EquipmentDto {
  id: number;
  name: string;
  type: string;
  specifications: Record<string, unknown> | null;
  work_schedule: Record<string, unknown> | null;
  maintenance_requirements: string;
  cost_per_hour: number | null;
}

export interface PersonnelDto {
  id: number;
  full_name: string;
  position: string;
  qualification: string;
  specialization: string;
  work_schedule: Record<string, unknown> | null;
  monthly_hours_norm: number | null;
  current_load_percent: number | null;
}

export interface PlanningCpmOperationDto {
  component_id: number;
  sequence: number;
  name: string;
  duration: number;
  earliest_start: number;
  earliest_finish: number;
  latest_start: number;
  latest_finish: number;
  total_float: number;
}

export interface PlanningCpmResultDto {
  project_id: number;
  total_duration: number;
  operations: Record<string, PlanningCpmOperationDto>;
  critical_path: string[];
}

export interface PlanningCompareResultDto {
  project_id: number;
  cpm: PlanningCpmResultDto;
  ga: unknown;
  sa: unknown;
}

export interface ChartPointDto {
  step: number;
  value: number;
}

export interface AlgorithmChartDto {
  kpi: number;
  time_series: ChartPointDto[];
  money_series: ChartPointDto[];
}

export interface PlanningChartDataDto {
  project_id: number;
  hour_rate: number;
  cpm: AlgorithmChartDto;
  ga: AlgorithmChartDto;
  sa: AlgorithmChartDto;
}

export interface ProjectResourceSummaryDto {
  project_id: number;
  personnel_count: number;
  equipment_count: number;
  equipment_types: string[];
}

