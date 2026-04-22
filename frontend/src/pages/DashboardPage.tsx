import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  LinearProgress,
  Tab,
  Tabs,
  TextField,
  Typography
} from "@mui/material";
import { AxiosError } from "axios";
import { useEffect, useMemo, useState } from "react";
import { useSnackbar } from "notistack";

import { useAppDispatch, useAppSelector } from "../store";
import { fetchProjects } from "../store/dashboardSlice";
import { api } from "../api/client";
import type { ProductDto, ProjectDto, ProjectResourceSummaryDto } from "../api/types";

export const DashboardPage = () => {
  const dispatch = useAppDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const { projects, loading, error } = useAppSelector((s) => s.dashboard);
  const [openCreate, setOpenCreate] = useState(false);
  const [openDetails, setOpenDetails] = useState(false);
  const [projectForm, setProjectForm] = useState<Partial<ProjectDto>>({
    name: "",
    description: "",
    status: "draft",
    start_date: null,
    end_date: null,
    deadline: null,
    total_labor_planned: null,
    total_labor_actual: null
  });
  const [activeProject, setActiveProject] = useState<ProjectDto | null>(null);
  const [products, setProducts] = useState<ProductDto[]>([]);
  const [resourceSummary, setResourceSummary] = useState<Record<number, ProjectResourceSummaryDto>>({});
  const [tab, setTab] = useState(0);
  const [projectSearchName, setProjectSearchName] = useState("");
  const [projectSearchStatus, setProjectSearchStatus] = useState("");
  const [productSearchName, setProductSearchName] = useState("");
  const [productSearchCode, setProductSearchCode] = useState("");
  const [productSearchType, setProductSearchType] = useState("");

  const filteredProjects = useMemo(() => {
    const normalizedName = projectSearchName.trim().toLowerCase();
    const normalizedStatus = projectSearchStatus.trim().toLowerCase();
    return projects.filter((project) => {
      const matchesName = !normalizedName || project.name.toLowerCase().includes(normalizedName);
      const matchesStatus = !normalizedStatus || project.status.toLowerCase().includes(normalizedStatus);
      return matchesName && matchesStatus;
    });
  }, [projects, projectSearchName, projectSearchStatus]);

  const filteredProducts = useMemo(() => {
    const normalizedName = productSearchName.trim().toLowerCase();
    const normalizedCode = productSearchCode.trim().toLowerCase();
    const normalizedType = productSearchType.trim().toLowerCase();
    return products.filter((product) => {
      const matchesName = !normalizedName || product.name.toLowerCase().includes(normalizedName);
      const matchesCode = !normalizedCode || (product.code ?? "").toLowerCase().includes(normalizedCode);
      const matchesType = !normalizedType || (product.type ?? "").toLowerCase().includes(normalizedType);
      return matchesName && matchesCode && matchesType;
    });
  }, [products, productSearchName, productSearchCode, productSearchType]);

  useEffect(() => {
    void dispatch(fetchProjects());
  }, [dispatch]);

  useEffect(() => {
    if (error) {
      enqueueSnackbar(error, { variant: "error" });
    }
  }, [error, enqueueSnackbar]);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        const { data } = await api.get<ProductDto[]>("/products/");
        setProducts(data);
      } catch {
        enqueueSnackbar("Не удалось загрузить изделия", { variant: "error" });
      }
    };
    void loadProducts();
  }, [enqueueSnackbar]);

  useEffect(() => {
    const loadResourceSummary = async () => {
      if (projects.length === 0) {
        setResourceSummary({});
        return;
      }
      const entries = await Promise.all(
        projects.map(async (project) => {
          try {
            const { data } = await api.get<ProjectResourceSummaryDto>(`/projects/${project.id}/resource-summary/`);
            return [project.id, data] as const;
          } catch {
            return [
              project.id,
              { project_id: project.id, personnel_count: 0, equipment_count: 0, equipment_types: [] } as ProjectResourceSummaryDto
            ] as const;
          }
        })
      );
      setResourceSummary(Object.fromEntries(entries));
    };
    void loadResourceSummary();
  }, [projects]);

  const handleCreateProject = async () => {
    try {
      if (!projectForm.name?.trim()) {
        enqueueSnackbar("Укажите имя проекта", { variant: "warning" });
        return;
      }
      await api.post("/projects/", projectForm);
      enqueueSnackbar("Проект создан", { variant: "success" });
      setOpenCreate(false);
      setProjectForm({
        name: "",
        description: "",
        status: "draft",
        start_date: null,
        end_date: null,
        deadline: null,
        total_labor_planned: null,
        total_labor_actual: null
      });
      void dispatch(fetchProjects());
    } catch (err) {
      const responseData = err instanceof AxiosError ? err.response?.data : null;
      const detail =
        typeof responseData === "string"
          ? responseData
          : typeof responseData === "object" && responseData
            ? JSON.stringify(responseData)
            : "Ошибка создания проекта";
      enqueueSnackbar(detail, { variant: "error" });
    }
  };

  const handleCardClick = (project: ProjectDto) => {
    setActiveProject(project);
    setProjectForm(project);
    setOpenDetails(true);
  };

  const handleSaveProject = async () => {
    if (!activeProject) return;
    try {
      await api.patch(`/projects/${activeProject.id}/`, projectForm);
      enqueueSnackbar("Проект обновлен", { variant: "success" });
      setOpenDetails(false);
      void dispatch(fetchProjects());
    } catch {
      enqueueSnackbar("Ошибка обновления проекта", { variant: "error" });
    }
  };

  const handlePauseProject = async () => {
    if (!activeProject) return;
    try {
      await api.post(`/projects/${activeProject.id}/pause/`);
      enqueueSnackbar("Проект поставлен на паузу, ресурсы освобождены", { variant: "success" });
      setOpenDetails(false);
      void dispatch(fetchProjects());
    } catch {
      enqueueSnackbar("Ошибка постановки на паузу", { variant: "error" });
    }
  };

  const handleDeleteProject = async () => {
    if (!activeProject) return;
    try {
      await api.delete(`/projects/${activeProject.id}/`);
      enqueueSnackbar("Проект удален, ресурсы освобождены", { variant: "success" });
      setOpenDetails(false);
      void dispatch(fetchProjects());
      const { data } = await api.get<ProductDto[]>("/products/");
      setProducts(data);
    } catch {
      enqueueSnackbar("Ошибка удаления проекта", { variant: "error" });
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
      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Проекты" />
        <Tab label="Изделия" />
      </Tabs>
      {loading ? (
        <CircularProgress />
      ) : tab === 0 ? (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Поиск по названию проекта"
                value={projectSearchName}
                onChange={(e) => setProjectSearchName(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Поиск по статусу проекта"
                value={projectSearchStatus}
                onChange={(e) => setProjectSearchStatus(e.target.value)}
              />
            </Grid>
          </Grid>
          <Grid container spacing={2}>
            {filteredProjects.map((p) => {
            const progress = 0; // пока прогресс берём с backend отдельно через /metrics
            const summary = resourceSummary[p.id];
            return (
              <Grid item xs={12} md={4} key={p.id}>
                <Card onClick={() => handleCardClick(p)} sx={{ cursor: "pointer" }}>
                  <CardContent>
                    <Typography variant="h6">{p.name}</Typography>
                    <Typography color="text.secondary">{p.status}</Typography>
                    <LinearProgress variant="determinate" value={progress} sx={{ mt: 2 }} />
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Прогресс: {progress.toFixed(0)}%
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Сотрудники: {summary?.personnel_count ?? 0}
                    </Typography>
                    <Typography variant="body2">
                      Оборудование: {summary?.equipment_count ?? 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Типы: {summary?.equipment_types?.length ? summary.equipment_types.join(", ") : "—"}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            );
            })}
          </Grid>
        </>
      ) : (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Поиск по названию изделия"
                value={productSearchName}
                onChange={(e) => setProductSearchName(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Поиск по коду изделия"
                value={productSearchCode}
                onChange={(e) => setProductSearchCode(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Поиск по типу изделия"
                value={productSearchType}
                onChange={(e) => setProductSearchType(e.target.value)}
              />
            </Grid>
          </Grid>
          <Grid container spacing={2}>
            {filteredProducts.map((product) => (
              <Grid item xs={12} md={4} key={product.id}>
                <Card
                  sx={{ cursor: "pointer" }}
                  onClick={() => {
                    const project = projects.find((x) => x.id === product.project);
                    if (project) {
                      handleCardClick(project);
                    } else {
                      enqueueSnackbar(`Изделие: ${product.name}. Проект ID: ${product.project}`, { variant: "info" });
                    }
                  }}
                >
                  <CardContent>
                    <Typography variant="h6">{product.name}</Typography>
                    <Typography color="text.secondary">Код: {product.code || "—"}</Typography>
                    <Typography color="text.secondary">Тип: {product.type || "—"}</Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Проект ID: {product.project}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Новый проект</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Название проекта"
            value={projectForm.name ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, name: e.target.value }))}
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            fullWidth
            label="Описание"
            value={projectForm.description ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, description: e.target.value }))}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Статус"
            value={projectForm.status ?? "draft"}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, status: e.target.value }))}
          />
          <Grid container spacing={1} sx={{ mt: 0.5 }}>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Start date"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={projectForm.start_date ?? ""}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, start_date: e.target.value || null }))}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Deadline"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={projectForm.deadline ?? ""}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, deadline: e.target.value || null }))}
              />
            </Grid>
          </Grid>
          <Box sx={{ mt: 1 }}>
            <TextField
              fullWidth
              type="number"
              label="Плановые трудозатраты (ч)"
              value={projectForm.total_labor_planned ?? ""}
              onChange={(e) =>
                setProjectForm((prev) => ({
                  ...prev,
                  total_labor_planned: e.target.value === "" ? null : Number(e.target.value)
                }))
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)}>Отмена</Button>
          <Button variant="contained" onClick={() => void handleCreateProject()}>
            Создать
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={openDetails} onClose={() => setOpenDetails(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Карточка проекта</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Название проекта"
            value={projectForm.name ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, name: e.target.value }))}
            sx={{ mt: 1, mb: 1 }}
          />
          <TextField
            fullWidth
            label="Описание"
            value={projectForm.description ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, description: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            fullWidth
            label="Статус"
            value={projectForm.status ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, status: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Start"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={projectForm.start_date ?? ""}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, start_date: e.target.value || null }))}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Deadline"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={projectForm.deadline ?? ""}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, deadline: e.target.value || null }))}
              />
            </Grid>
          </Grid>
          <TextField
            fullWidth
            type="number"
            label="Плановые трудозатраты"
            value={projectForm.total_labor_planned ?? ""}
            onChange={(e) =>
              setProjectForm((prev) => ({
                ...prev,
                total_labor_planned: e.target.value === "" ? null : Number(e.target.value)
              }))
            }
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDetails(false)}>Закрыть</Button>
          <Button color="warning" onClick={() => void handlePauseProject()}>
            Пауза
          </Button>
          <Button color="error" onClick={() => void handleDeleteProject()}>
            Удалить
          </Button>
          <Button variant="contained" onClick={() => void handleSaveProject()}>
            Сохранить
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

