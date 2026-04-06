import { Button, Card, CardContent, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Grid, LinearProgress, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";

import { useAppDispatch, useAppSelector } from "../store";
import { fetchProjects } from "../store/dashboardSlice";
import { api } from "../api/client";

export const DashboardPage = () => {
  const dispatch = useAppDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const { projects, loading, error } = useAppSelector((s) => s.dashboard);
  const [openCreate, setOpenCreate] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectStatus, setProjectStatus] = useState("draft");

  useEffect(() => {
    void dispatch(fetchProjects());
  }, [dispatch]);

  useEffect(() => {
    if (error) {
      enqueueSnackbar(error, { variant: "error" });
    }
  }, [error, enqueueSnackbar]);

  const handleCreateProject = async () => {
    try {
      if (!projectName.trim()) {
        enqueueSnackbar("Укажите имя проекта", { variant: "warning" });
        return;
      }
      await api.post("/projects/", {
        name: projectName,
        description: "",
        status: projectStatus,
        start_date: null,
        end_date: null,
        deadline: null,
        total_labor_planned: null,
        total_labor_actual: null
      });
      enqueueSnackbar("Проект создан", { variant: "success" });
      setOpenCreate(false);
      setProjectName("");
      void dispatch(fetchProjects());
    } catch {
      enqueueSnackbar("Ошибка создания проекта", { variant: "error" });
    }
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Дашборд
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Сводка по активным проектам.
      </Typography>
      <Button variant="contained" sx={{ mb: 2 }} onClick={() => setOpenCreate(true)}>
        Создать проект
      </Button>
      {loading ? (
        <CircularProgress />
      ) : (
        <Grid container spacing={2}>
          {projects.map((p) => {
            const progress = 0; // пока прогресс берём с backend отдельно через /metrics
            return (
              <Grid item xs={12} md={4} key={p.id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6">{p.name}</Typography>
                    <Typography color="text.secondary">{p.status}</Typography>
                    <LinearProgress variant="determinate" value={progress} sx={{ mt: 2 }} />
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Прогресс: {progress.toFixed(0)}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Новый проект</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Название проекта"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            fullWidth
            label="Статус"
            value={projectStatus}
            onChange={(e) => setProjectStatus(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)}>Отмена</Button>
          <Button variant="contained" onClick={() => void handleCreateProject()}>
            Создать
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

