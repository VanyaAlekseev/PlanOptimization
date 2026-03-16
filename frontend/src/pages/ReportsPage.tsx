import { Button, Grid, Paper, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useSnackbar } from "notistack";

import { api } from "../api/client";

const downloadJson = (data: unknown, filename: string) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
};

export const ReportsPage = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [projectId, setProjectId] = useState<number | "">("");

  const handleDownload = async (type: "gantt" | "tech-card") => {
    try {
      if (!projectId) {
        enqueueSnackbar("Укажите ID проекта", { variant: "warning" });
        return;
      }
      const url = type === "gantt" ? "/reports/gantt/" : "/reports/tech-card/";
      const { data } = await api.get(url, { params: { project_id: projectId } });
      downloadJson(data, `${type}-project-${projectId}.json`);
      enqueueSnackbar("Отчёт сгенерирован (JSON-заглушка)", { variant: "success" });
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
        Пока отчёты скачиваются в виде JSON-заглушек. Позже backend начнёт отдавать PDF/Excel.
      </Typography>
      <TextField
        label="ID проекта"
        type="number"
        value={projectId}
        onChange={(e) => setProjectId(e.target.value === "" ? "" : Number(e.target.value))}
        sx={{ mb: 2 }}
      />
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Диаграмма Ганта (JSON сейчас, PDF позже)</Typography>
            <Button sx={{ mt: 2 }} variant="contained" onClick={() => void handleDownload("gantt")}>
              Скачать
            </Button>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Технологическая карта</Typography>
            <Button sx={{ mt: 2 }} variant="contained" onClick={() => void handleDownload("tech-card")}>
              Скачать
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </>
  );
};

