import {
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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
import type { AlgorithmComparisonDto, ProjectDto } from "../api/types";
import { useAppSelector } from "../store";

export const AlgorithmsComparePage = () => {
  const projects = useAppSelector((s) => s.dashboard.projects);
  const { enqueueSnackbar } = useSnackbar();
  const [projectId, setProjectId] = useState<number | "">("");
  const [rows, setRows] = useState<AlgorithmComparisonDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>("");

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
      setLoading(true);
      await api.post("/planning/compare-and-save/", { project_id: projectId, params: {} });
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
      await api.post("/planning/select-algorithm/", {
        project_id: projectId,
        algorithm: selectedAlgorithm.toLowerCase(),
        params: {}
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
    </>
  );
};

