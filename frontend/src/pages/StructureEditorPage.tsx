import { Box, Button, Checkbox, Grid, ListItemText, MenuItem, Paper, TextField, Typography } from "@mui/material";
import { AxiosError } from "axios";
import { Tree, TreeApi } from "react-arborist";
import { useEffect, useRef, useState } from "react";
import { useSnackbar } from "notistack";

import { useAppDispatch, useAppSelector } from "../store";
import { ComponentNode, setSelectedNodeId, setTree } from "../store/structureSlice";
import { api } from "../api/client";
import type { ComponentDto, ComponentTreeDto, EquipmentDto, PersonnelDto, ProductDto, ProjectDto } from "../api/types";
import { fetchProjects } from "../store/dashboardSlice";

export const StructureEditorPage = () => {
  const dispatch = useAppDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const tree = useAppSelector((s) => s.structure.tree);
  const selectedNodeId = useAppSelector((s) => s.structure.selectedNodeId);
  const treeRef = useRef<TreeApi<ComponentNode>>(null);
  const [productId, setProductId] = useState<number | "">("");
  const [xmlFile, setXmlFile] = useState<File | null>(null);
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
  const [productForm, setProductForm] = useState<Partial<ProductDto>>({
    name: "",
    code: "",
    type: "assembly",
    structure_tree: null,
    tech_requirements: "",
    norm_hours: null
  });
  const [newProjectId, setNewProjectId] = useState<number | null>(null);
  const [equipment, setEquipment] = useState<EquipmentDto[]>([]);
  const [personnel, setPersonnel] = useState<PersonnelDto[]>([]);
  const [selectedEquipmentIds, setSelectedEquipmentIds] = useState<number[]>([]);
  const [selectedPersonnelIds, setSelectedPersonnelIds] = useState<number[]>([]);
  const [componentForm, setComponentForm] = useState<{ name: string; type: string; quantity: number }>({
    name: "",
    type: "",
    quantity: 1
  });
  const [componentLoading, setComponentLoading] = useState(false);

  const loadTree = async (pid: number) => {
    const { data } = await api.get<ComponentTreeDto>("/components/tree", {
      params: { product_id: pid }
    });
    const mapNode = (n: any): ComponentNode => ({
      id: String(n.id),
      name: n.name,
      type: n.type,
      quantity: n.quantity ?? 1,
      children: (n.children ?? []).map(mapNode)
    });
    dispatch(setTree(data.roots.map(mapNode)));
  };

  useEffect(() => {
    const loadSelected = async () => {
      if (!selectedNodeId) {
        setComponentForm({ name: "", type: "", quantity: 1 });
        return;
      }
      const numericId = Number(selectedNodeId);
      if (!Number.isFinite(numericId)) {
        return;
      }
      try {
        setComponentLoading(true);
        const { data } = await api.get<ComponentDto>(`/components/${numericId}/`);
        setComponentForm({
          name: data.name,
          type: data.type,
          quantity: data.quantity ?? 1
        });
      } catch {
        enqueueSnackbar("Не удалось загрузить свойства компонента", { variant: "error" });
      } finally {
        setComponentLoading(false);
      }
    };
    void loadSelected();
  }, [selectedNodeId, enqueueSnackbar]);

  useEffect(() => {
    const loadResources = async () => {
      try {
        const [eq, ps] = await Promise.all([
          api.get<EquipmentDto[]>("/equipment/"),
          api.get<PersonnelDto[]>("/personnel/")
        ]);
        setEquipment(eq.data);
        setPersonnel(ps.data);
      } catch {
        enqueueSnackbar("Не удалось загрузить ресурсы. Управляйте ими на вкладке Ресурсы.", { variant: "warning" });
      }
    };
    void loadResources();
  }, [enqueueSnackbar]);

  const handleImportXml = async () => {
    try {
      if (!productId) {
        enqueueSnackbar("Укажите ID изделия", { variant: "warning" });
        return;
      }
      if (!xmlFile) {
        enqueueSnackbar("Выберите XML-файл", { variant: "warning" });
        return;
      }
      const { data: targetProduct } = await api.get<ProductDto>(`/products/${productId}/`);
      if (newProjectId && targetProduct.project !== newProjectId) {
        enqueueSnackbar(
          `Выбранное изделие #${productId} относится к проекту #${targetProduct.project}, а не к только что созданному #${newProjectId}`,
          { variant: "error" }
        );
        return;
      }
      const form = new FormData();
      form.append("product_id", String(productId));
      form.append("overwrite", "true");
      form.append("xml_file", xmlFile);
      await api.post("/components/import-xml/", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      await loadTree(productId);
      enqueueSnackbar("XML успешно импортирован", { variant: "success" });
    } catch {
      enqueueSnackbar("Ошибка импорта XML", { variant: "error" });
    }
  };

  const handleCreateProjectAndProduct = async () => {
    try {
      if (!projectForm.name?.trim() || !productForm.name?.trim()) {
        enqueueSnackbar("Укажите название проекта и изделия", { variant: "warning" });
        return;
      }
      const p = await api.post("/projects/", projectForm);
      const createdProjectId = p.data.id as number;
      setNewProjectId(createdProjectId);
      const product = await api.post("/products/", {
        ...productForm,
        project: createdProjectId
      });
      const createdProductId = product.data.id as number;
      setProductId(createdProductId);
      await api.post(`/projects/${createdProjectId}/assign-resources/`, {
        equipment_ids: selectedEquipmentIds,
        personnel_ids: selectedPersonnelIds
      });
      await dispatch(fetchProjects());
      enqueueSnackbar(`Проект #${createdProjectId} и изделие #${createdProductId} созданы`, { variant: "success" });
    } catch (err) {
      const responseData = err instanceof AxiosError ? err.response?.data : null;
      const detail =
        typeof responseData === "string"
          ? responseData
          : typeof responseData === "object" && responseData
            ? JSON.stringify(responseData)
            : "Ошибка создания проекта/изделия";
      enqueueSnackbar(detail, { variant: "error" });
    }
  };

  const handleUpdateProduct = async () => {
    try {
      if (!productId) {
        enqueueSnackbar("Укажите ID изделия", { variant: "warning" });
        return;
      }
      await api.patch(`/products/${productId}/`, productForm);
      enqueueSnackbar("Изделие обновлено", { variant: "success" });
    } catch {
      enqueueSnackbar("Ошибка обновления изделия", { variant: "error" });
    }
  };

  const handleLoadProduct = async () => {
    try {
      if (!productId) return;
      const { data } = await api.get<ProductDto>(`/products/${productId}/`);
      setProductForm(data);
    } catch {
      enqueueSnackbar("Не удалось загрузить изделие", { variant: "error" });
    }
  };

  const handleSaveComponent = async () => {
    if (!selectedNodeId) {
      enqueueSnackbar("Выберите компонент в дереве", { variant: "warning" });
      return;
    }
    if (!productId) {
      enqueueSnackbar("Укажите ID изделия", { variant: "warning" });
      return;
    }
    const componentId = Number(selectedNodeId);
    if (!Number.isFinite(componentId)) {
      enqueueSnackbar("Некорректный ID компонента", { variant: "error" });
      return;
    }
    try {
      await api.patch(`/components/${componentId}/`, {
        name: componentForm.name,
        type: componentForm.type,
        quantity: componentForm.quantity
      });
      enqueueSnackbar("Свойства компонента сохранены", { variant: "success" });
      await loadTree(productId);
    } catch {
      enqueueSnackbar("Ошибка сохранения компонента", { variant: "error" });
    }
  };

  const handleDeleteComponent = async () => {
    if (!selectedNodeId) {
      enqueueSnackbar("Выберите компонент в дереве", { variant: "warning" });
      return;
    }
    if (!productId) {
      enqueueSnackbar("Укажите ID изделия", { variant: "warning" });
      return;
    }
    const componentId = Number(selectedNodeId);
    if (!Number.isFinite(componentId)) {
      enqueueSnackbar("Некорректный ID компонента", { variant: "error" });
      return;
    }
    try {
      await api.delete(`/components/${componentId}/`);
      dispatch(setSelectedNodeId(null));
      enqueueSnackbar("Компонент удален", { variant: "success" });
      await loadTree(productId);
    } catch {
      enqueueSnackbar("Ошибка удаления компонента", { variant: "error" });
    }
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Typography variant="h4">Редактор структуры изделия</Typography>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, height: 500, overflow: "auto" }}>
          <Typography variant="subtitle1" gutterBottom>
            Структура (drag-and-drop mock)
          </Typography>
          <Tree<ComponentNode>
            ref={treeRef}
            data={tree}
            // react-arborist использует childrenAccessor, чтобы извлекать children из data-узла
            childrenAccessor={(d) => d.children ?? null}
            onSelect={(nodes) => dispatch(setSelectedNodeId(nodes[0]?.id ?? null))}
          >
            {({ node }) => (
              <Box sx={{ p: 0.5 }}>
                {node.data.name} ({node.data.type}) ×{node.data.quantity}
              </Box>
            )}
          </Tree>
        </Paper>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Создание проекта и изделия
          </Typography>
          <TextField
            label="Название проекта"
            fullWidth
            value={projectForm.name ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, name: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            label="Описание проекта"
            fullWidth
            value={projectForm.description ?? ""}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, description: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            label="Статус проекта"
            fullWidth
            value={projectForm.status ?? "draft"}
            onChange={(e) => setProjectForm((prev) => ({ ...prev, status: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <Grid container spacing={1} sx={{ mb: 1 }}>
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
          <TextField
            label="Плановые трудозатраты (ч)"
            fullWidth
            type="number"
            value={projectForm.total_labor_planned ?? ""}
            onChange={(e) =>
              setProjectForm((prev) => ({
                ...prev,
                total_labor_planned: e.target.value === "" ? null : Number(e.target.value)
              }))
            }
            sx={{ mb: 1 }}
          />
          <TextField
            label="Название изделия"
            fullWidth
            value={productForm.name ?? ""}
            onChange={(e) => setProductForm((prev) => ({ ...prev, name: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            label="Код изделия"
            fullWidth
            value={productForm.code ?? ""}
            onChange={(e) => setProductForm((prev) => ({ ...prev, code: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            label="Тип изделия"
            fullWidth
            value={productForm.type ?? ""}
            onChange={(e) => setProductForm((prev) => ({ ...prev, type: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            label="Тех. требования"
            fullWidth
            value={productForm.tech_requirements ?? ""}
            onChange={(e) => setProductForm((prev) => ({ ...prev, tech_requirements: e.target.value }))}
            sx={{ mb: 1 }}
          />
          <TextField
            label="Нормо-часы"
            fullWidth
            type="number"
            value={productForm.norm_hours ?? ""}
            onChange={(e) => setProductForm((prev) => ({ ...prev, norm_hours: e.target.value === "" ? null : Number(e.target.value) }))}
            sx={{ mb: 1 }}
          />
          <Button variant="contained" onClick={() => void handleCreateProjectAndProduct()} sx={{ mb: 2 }}>
            Создать проект и изделие
          </Button>
          {newProjectId ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Создан проект ID: {newProjectId}
            </Typography>
          ) : null}

          <Typography variant="subtitle1" gutterBottom>
            Импорт из XML
          </Typography>
          <TextField
            label="ID изделия (product_id)"
            type="number"
            value={productId}
            onChange={(e) => setProductId(e.target.value === "" ? "" : Number(e.target.value))}
            sx={{ mb: 2 }}
          />
          <Button variant="outlined" component="label" sx={{ mb: 2 }}>
            Выбрать XML-файл
            <input
              type="file"
              accept=".xml,text/xml,application/xml"
              hidden
              onChange={(e) => setXmlFile(e.target.files?.[0] ?? null)}
            />
          </Button>
          {xmlFile ? (
            <Typography variant="body2" sx={{ mb: 2 }}>
              Файл: {xmlFile.name}
            </Typography>
          ) : null}
          <Button variant="contained" onClick={() => void handleImportXml()}>
            Импортировать XML
          </Button>
          <Button variant="outlined" onClick={() => void handleLoadProduct()} sx={{ ml: 1 }}>
            Загрузить изделие
          </Button>
          <Button variant="outlined" onClick={() => void handleUpdateProduct()} sx={{ ml: 1 }}>
            Сохранить изделие
          </Button>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            XML загружается на backend `/api/components/import-xml/` как файл.
          </Typography>
          <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
            Ресурсы (просмотр)
          </Typography>
          <TextField
            fullWidth
            select
            label="Выбрать оборудование (несколько)"
            value={selectedEquipmentIds}
            SelectProps={{
              multiple: true,
              renderValue: (selected) =>
                (selected as number[])
                  .map((id) => equipment.find((item) => item.id === id)?.name)
                  .filter(Boolean)
                  .join(", ")
            }}
            onChange={(e) => {
              const raw = e.target.value as unknown as Array<number | string>;
              setSelectedEquipmentIds(raw.map(Number));
            }}
            sx={{ mb: 1 }}
          >
            {equipment.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                <Checkbox checked={selectedEquipmentIds.indexOf(item.id) > -1} />
                <ListItemText primary={`${item.name} (${item.type})`} />
              </MenuItem>
            ))}
          </TextField>
          <TextField
            fullWidth
            select
            label="Выбрать сотрудников (несколько)"
            value={selectedPersonnelIds}
            SelectProps={{
              multiple: true,
              renderValue: (selected) =>
                (selected as number[])
                  .map((id) => personnel.find((item) => item.id === id)?.full_name)
                  .filter(Boolean)
                  .join(", ")
            }}
            onChange={(e) => {
              const raw = e.target.value as unknown as Array<number | string>;
              setSelectedPersonnelIds(raw.map(Number));
            }}
            sx={{ mb: 1 }}
          >
            {personnel.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                <Checkbox checked={selectedPersonnelIds.indexOf(item.id) > -1} />
                <ListItemText primary={`${item.full_name} (${item.position || "без должности"})`} />
              </MenuItem>
            ))}
          </TextField>
          <Typography variant="body2" color="text.secondary">
            Выбранных: оборудование {selectedEquipmentIds.length}, сотрудники {selectedPersonnelIds.length}.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Создание/удаление ресурсов перенесено на вкладку "Ресурсы".
          </Typography>
        </Paper>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Свойства компонента
          </Typography>
          {selectedNodeId ? (
            <>
              <Typography sx={{ mb: 1 }}>Выбран компонент: {selectedNodeId}</Typography>
              <TextField
                fullWidth
                label="Название"
                value={componentForm.name}
                onChange={(e) => setComponentForm((prev) => ({ ...prev, name: e.target.value }))}
                sx={{ mb: 1 }}
                disabled={componentLoading}
              />
              <TextField
                fullWidth
                label="Тип"
                value={componentForm.type}
                onChange={(e) => setComponentForm((prev) => ({ ...prev, type: e.target.value }))}
                sx={{ mb: 1 }}
                disabled={componentLoading}
              />
              <TextField
                fullWidth
                label="Количество"
                type="number"
                value={componentForm.quantity}
                onChange={(e) =>
                  setComponentForm((prev) => ({
                    ...prev,
                    quantity: Number.isNaN(Number(e.target.value)) ? 1 : Number(e.target.value)
                  }))
                }
                sx={{ mb: 2 }}
                disabled={componentLoading}
              />
            </>
          ) : (
            <Typography color="text.secondary">Выберите компонент в дереве.</Typography>
          )}
          <Button sx={{ mt: 1, mr: 1 }} variant="contained" onClick={() => void handleSaveComponent()} disabled={!selectedNodeId}>
            Сохранить изменения
          </Button>
          <Button sx={{ mt: 1 }} variant="outlined" color="error" onClick={() => void handleDeleteComponent()} disabled={!selectedNodeId}>
            Удалить компонент
          </Button>
        </Paper>
      </Grid>
    </Grid>
  );
};

