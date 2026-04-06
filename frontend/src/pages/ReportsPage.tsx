import { Button, FormControl, Grid, InputLabel, MenuItem, Paper, Select, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";

import { api } from "../api/client";
import type { ProjectDto } from "../api/types";

export const ReportsPage = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [projectId, setProjectId] = useState<number | "">("");
  const [projects, setProjects] = useState<ProjectDto[]>([]);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const { data } = await api.get<ProjectDto[]>("/projects/");
        setProjects(data);
      } catch {
        enqueueSnackbar("Не удалось загрузить список проектов", { variant: "error" });
      }
    };
    void loadProjects();
  }, [enqueueSnackbar]);

  const handleDownload = async (type: "gantt" | "tech-card") => {
    try {
      if (!projectId) {
        enqueueSnackbar("Укажите ID проекта", { variant: "warning" });
        return;
      }
      const url = type === "gantt" ? "/reports/gantt/" : "/reports/tech-card/";
      const response = await api.get<Blob>(url, {
        params: { project_id: projectId },
        responseType: "blob"
      });
      const ext = type === "gantt" ? "pdf" : "xlsx";
      const blob = response.data;
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${type}-project-${projectId}.${ext}`;
      link.click();
      enqueueSnackbar("Отчёт сформирован и скачан", { variant: "success" });
    } catch {
      enqueueSnackbar("Ошибка генерации отчёта", { variant: "error" });
    }
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Отчёты и аналитика
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Отчёты формируются на backend и скачиваются в PDF/XLSX.
      </Typography>
      <FormControl sx={{ minWidth: 280, mb: 2 }}>
        <InputLabel id="reports-project-select-label">Проект</InputLabel>
        <Select
          labelId="reports-project-select-label"
          label="Проект"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value === "" ? "" : Number(e.target.value))}
        >
          {projects.map((p) => (
            <MenuItem key={p.id} value={p.id}>
              {p.id}: {p.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Диаграмма Ганта (PDF)</Typography>
            <Button sx={{ mt: 2 }} variant="contained" onClick={() => void handleDownload("gantt")}>
              Скачать
            </Button>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Технологическая карта (Excel)</Typography>
            <Button sx={{ mt: 2 }} variant="contained" onClick={() => void handleDownload("tech-card")}>
              Скачать
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </>
  );
};

