import { Box, CircularProgress, FormControl, InputLabel, MenuItem, Paper, Select, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { useSnackbar } from "notistack";

import { api } from "../api/client";
import type { PlanningCpmResultDto, ProjectDto } from "../api/types";
import { useAppDispatch, useAppSelector } from "../store";
import { SimpleGantt, SimpleGanttTask } from "../components/SimpleGantt";
import { fetchProjects } from "../store/dashboardSlice";

export const PlanningPage = () => {
  const dispatch = useAppDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const projects = useAppSelector((s) => s.dashboard.projects);
  const [selectedProjectId, setSelectedProjectId] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [cpmResult, setCpmResult] = useState<PlanningCpmResultDto | null>(null);

  useEffect(() => {
    if (projects.length === 0) {
      void dispatch(fetchProjects());
    }
  }, [dispatch, projects.length]);

  useEffect(() => {
    if (!selectedProjectId) return;
    const load = async () => {
      try {
        setLoading(true);
        // Для упрощения сразу запускаем CPM синхронно.
        const { data } = await api.post<{ project_id: number; algorithm: string; result: PlanningCpmResultDto }>(
          "/planning/optimize/",
          { project_id: selectedProjectId, algorithm: "cpm", async_run: false }
        );
        setCpmResult(data.result);
        if (!data.result || Object.keys(data.result.operations ?? {}).length === 0) {
          enqueueSnackbar("Для проекта нет операций. Проверьте, что XML импортирован в изделие этого проекта.", {
            variant: "warning"
          });
        }
      } catch {
        enqueueSnackbar("Ошибка расчёта плана", { variant: "error" });
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [selectedProjectId, enqueueSnackbar]);

  const tasks: SimpleGanttTask[] = useMemo(() => {
    if (!cpmResult) return [];
    const base = new Date();
    const dayMs = 24 * 60 * 60 * 1000;
    return Object.values(cpmResult.operations).map((op) => ({
      id: `${op.component_id}:${op.sequence}`,
      start: new Date(base.getTime() + op.earliest_start * dayMs),
      end: new Date(base.getTime() + op.earliest_finish * dayMs),
      name: op.name,
      isCritical: Math.abs(op.total_float) < 1e-6
    }));
  }, [cpmResult]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Планировщик
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Диаграмма Ганта на основе результата CPM.
      </Typography>

      <FormControl sx={{ minWidth: 280, mb: 2 }}>
        <InputLabel id="project-select-label">Проект</InputLabel>
        <Select
          labelId="project-select-label"
          label="Проект"
          value={selectedProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value === "" ? "" : Number(e.target.value))}
        >
          {projects.map((p: ProjectDto) => (
            <MenuItem key={p.id} value={p.id}>
              {p.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {loading ? (
        <CircularProgress />
      ) : (
        <Paper sx={{ p: 2 }}>
          <SimpleGantt tasks={tasks} />
        </Paper>
      )}
    </Box>
  );
};

