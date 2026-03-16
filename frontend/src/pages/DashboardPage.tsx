import { Card, CardContent, CircularProgress, Grid, LinearProgress, Typography } from "@mui/material";
import { useEffect } from "react";
import { useSnackbar } from "notistack";

import { useAppDispatch, useAppSelector } from "../store";
import { fetchProjects } from "../store/dashboardSlice";

export const DashboardPage = () => {
  const dispatch = useAppDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const { projects, loading, error } = useAppSelector((s) => s.dashboard);

  useEffect(() => {
    void dispatch(fetchProjects());
  }, [dispatch]);

  useEffect(() => {
    if (error) {
      enqueueSnackbar(error, { variant: "error" });
    }
  }, [error, enqueueSnackbar]);

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Дашборд
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Сводка по активным проектам.
      </Typography>
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
    </>
  );
};

