import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";

import { api } from "../api/client";
import type { AlgorithmComparisonDto, PlanningChartDataDto, ProjectDto } from "../api/types";
import { useAppDispatch, useAppSelector } from "../store";
import { fetchProjects } from "../store/dashboardSlice";

const MiniLineChart = ({
  points,
  title,
  yUnit
}: {
  points: { step: number; value: number }[];
  title: string;
  yUnit: string;
}) => {
  const width = 260;
  const height = 140;
  const leftPad = 34;
  const rightPad = 8;
  const topPad = 8;
  const bottomPad = 26;
  if (points.length === 0) {
    return <Typography variant="caption">Нет данных для графика</Typography>;
  }
  const maxX = Math.max(...points.map((p) => p.step), 1);
  const maxY = Math.max(...points.map((p) => p.value), 1);
  const polyline = points
    .map((p) => {
      const x = leftPad + (p.step / maxX) * (width - leftPad - rightPad);
      const y = topPad + (1 - p.value / maxY) * (height - topPad - bottomPad);
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <Box sx={{ border: "1px solid #ddd", borderRadius: 1, p: 1, mb: 1 }}>
      <Typography variant="subtitle2">{title}</Typography>
      <svg width={width} height={height}>
        <line x1={leftPad} y1={height - bottomPad} x2={width - rightPad} y2={height - bottomPad} stroke="#999" strokeWidth="1" />
        <line x1={leftPad} y1={topPad} x2={leftPad} y2={height - bottomPad} stroke="#999" strokeWidth="1" />
        <polyline points={polyline} fill="none" stroke="#1976d2" strokeWidth="2" />
        <text x={leftPad} y={height - bottomPad + 14} fontSize="10" fill="#666">
          0
        </text>
        <text x={width - rightPad - 12} y={height - bottomPad + 14} fontSize="10" fill="#666">
          {maxX}
        </text>
        <text x={6} y={topPad + 6} fontSize="10" fill="#666">
          {maxY.toFixed(1)}
        </text>
        <text x={6} y={height - bottomPad + 2} fontSize="10" fill="#666">
          0
        </text>
        <text x={width / 2 - 30} y={height - 4} fontSize="10" fill="#666">
          Шаг (итерация)
        </text>
        <text x={4} y={height / 2} fontSize="10" fill="#666">
          {yUnit}
        </text>
      </svg>
    </Box>
  );
};

export const AlgorithmsComparePage = () => {
  const dispatch = useAppDispatch();
  const projects = useAppSelector((s) => s.dashboard.projects);
  const { enqueueSnackbar } = useSnackbar();
  const [projectId, setProjectId] = useState<number | "">("");
  const [rows, setRows] = useState<AlgorithmComparisonDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>("");
  const [chartData, setChartData] = useState<PlanningChartDataDto | null>(null);
  const [alpha, setAlpha] = useState(0.6);
  const [beta, setBeta] = useState(0.2);
  const [gamma, setGamma] = useState(0.2);
  const [useWorkSchedule, setUseWorkSchedule] = useState(false);
  const [strictMissingResources, setStrictMissingResources] = useState(false);

  useEffect(() => {
    if (projects.length === 0) {
      void dispatch(fetchProjects());
    }
  }, [dispatch, projects.length]);

  useEffect(() => {
    if (!projectId) return;
    const load = async () => {
      try {
        setLoading(true);
        const { data } = await api.get<AlgorithmComparisonDto[]>("/algorithm-comparisons/");
        setRows(data.filter((r) => r.project === projectId));
      } catch {
        enqueueSnackbar("Ошибка загрузки результатов алгоритмов", { variant: "error" });
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [projectId, enqueueSnackbar]);

  const handleRunCompare = async () => {
    try {
      if (!projectId) {
        enqueueSnackbar("Выберите проект", { variant: "warning" });
        return;
      }
      if (alpha < 0 || beta < 0 || gamma < 0) {
        enqueueSnackbar("Весовые коэффициенты не могут быть отрицательными", { variant: "warning" });
        return;
      }
      if (alpha + beta + gamma <= 0) {
        enqueueSnackbar("Сумма alpha + beta + gamma должна быть больше нуля", { variant: "warning" });
        return;
      }
      const params = {
        alpha,
        beta,
        gamma,
        use_work_schedule: useWorkSchedule,
        strict_missing_resources: strictMissingResources
      };
      setLoading(true);
      await api.post("/planning/compare-and-save/", { project_id: projectId, params });
      const chartResponse = await api.post<PlanningChartDataDto>("/planning/chart-data/", {
        project_id: projectId,
        params
      });
      setChartData(chartResponse.data);
      const { data } = await api.get<AlgorithmComparisonDto[]>("/algorithm-comparisons/");
      setRows(data.filter((r) => r.project === projectId));
      enqueueSnackbar("Сравнение алгоритмов выполнено и сохранено", { variant: "success" });
    } catch {
      enqueueSnackbar("Ошибка запуска сравнения", { variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAlgorithm = async () => {
    try {
      if (!projectId || !selectedAlgorithm) {
        enqueueSnackbar("Выберите проект и алгоритм", { variant: "warning" });
        return;
      }
      if (alpha + beta + gamma <= 0) {
        enqueueSnackbar("Сумма alpha + beta + gamma должна быть больше нуля", { variant: "warning" });
        return;
      }
      await api.post("/planning/select-algorithm/", {
        project_id: projectId,
        algorithm: selectedAlgorithm.toLowerCase(),
        params: {
          alpha,
          beta,
          gamma,
          use_work_schedule: useWorkSchedule,
          strict_missing_resources: strictMissingResources
        }
      });
      enqueueSnackbar(`Алгоритм ${selectedAlgorithm} закреплен за проектом`, { variant: "success" });
    } catch {
      enqueueSnackbar("Ошибка закрепления алгоритма", { variant: "error" });
    }
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Сравнение алгоритмов
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Данные берутся из сущности AlgorithmComparison.
      </Typography>

      <FormControl sx={{ minWidth: 280, mb: 2 }}>
        <InputLabel id="project-select-label">Проект</InputLabel>
        <Select
          labelId="project-select-label"
          label="Проект"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value === "" ? "" : Number(e.target.value))}
        >
          {projects.map((p: ProjectDto) => (
            <MenuItem key={p.id} value={p.id}>
              {p.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Paper sx={{ p: 2, mb: 2, maxWidth: 900 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Параметры оптимизации
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="alpha (makespan)"
              value={alpha}
              inputProps={{ step: 0.1, min: 0 }}
              onChange={(e) => setAlpha(Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="beta (human_hours)"
              value={beta}
              inputProps={{ step: 0.1, min: 0 }}
              onChange={(e) => setBeta(Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="gamma (resource_delay)"
              value={gamma}
              inputProps={{ step: 0.1, min: 0 }}
              onChange={(e) => setGamma(Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary">
              Сумма коэффициентов может быть любой: backend нормализует веса до суммы 1.
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={<Checkbox checked={useWorkSchedule} onChange={(e) => setUseWorkSchedule(e.target.checked)} />}
              label="Учитывать work_schedule (stage 2)"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Checkbox checked={strictMissingResources} onChange={(e) => setStrictMissingResources(e.target.checked)} />
              }
              label="Строго считать отсутствие ресурса недопустимым"
            />
          </Grid>
        </Grid>
      </Paper>
      <Button sx={{ ml: 2, mb: 2 }} variant="contained" onClick={() => void handleRunCompare()}>
        Запустить сравнение
      </Button>

      {loading ? (
        <CircularProgress />
      ) : (
        <Paper sx={{ p: 2, maxWidth: 800 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Выбор</TableCell>
                <TableCell>Алгоритм</TableCell>
                <TableCell>Время проекта</TableCell>
                <TableCell>Человеко-часы</TableCell>
                <TableCell>Загрузка ресурсов</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>
                    <input
                      type="radio"
                      checked={selectedAlgorithm === row.algorithm_name}
                      onChange={() => setSelectedAlgorithm(row.algorithm_name)}
                    />
                  </TableCell>
                  <TableCell>{row.algorithm_name}</TableCell>
                  <TableCell>{row.total_duration}</TableCell>
                  <TableCell>{row.resource_utilization}</TableCell>
                  <TableCell>{row.deadline_satisfaction}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Button sx={{ mt: 2 }} variant="contained" onClick={() => void handleSelectAlgorithm()}>
            Закрепить выбранный алгоритм за проектом
          </Button>
        </Paper>
      )}
      {chartData ? (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Графики алгоритмов (сроки и деньги)
          </Typography>
          <Grid container spacing={2}>
            {(["cpm", "ga", "sa"] as const).map((key) => (
              <Grid item xs={12} md={4} key={key}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>
                    {key.toUpperCase()}
                  </Typography>
                  <MiniLineChart points={chartData[key].time_series} title="Минимизация сроков" yUnit="Дни" />
                  <MiniLineChart points={chartData[key].money_series} title="Минимизация денег" yUnit="Деньги" />
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Box>
      ) : null}
    </>
  );
};

