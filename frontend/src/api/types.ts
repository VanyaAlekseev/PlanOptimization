// Общие DTO для API backend.

export interface ProjectDto {
  id: number;
  name: string;
  status: string;
  start_date: string | null;
  deadline: string | null;
  end_date: string | null;
}

export interface ProductDto {
  id: number;
  project: number;
  name: string;
  code: string;
  type: string;
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

