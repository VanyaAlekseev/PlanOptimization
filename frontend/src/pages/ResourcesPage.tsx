import {
  Box,
  Button,
  Grid,
  MenuItem,
  Paper,
  Tab,
  Tabs,
  TextField,
  Typography
} from "@mui/material";
import { AxiosError } from "axios";
import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";

import { api } from "../api/client";
import type { EquipmentDto, PersonnelDto } from "../api/types";

const EQUIPMENT_TYPES = [
  "Токарный станок",
  "Фрезерный станок",
  "Сверлильный станок",
  "Шлифовальный станок",
  "Лазерный резак",
  "3D-принтер",
  "Паяльная станция",
  "Станок ЧПУ",
  "Пресс",
  "Печь термообработки",
  "Сборочный стол",
  "Контрольно-измерительный стенд",
  "Конвейер",
  "Камера испытаний",
  "Упаковочная линия"
];

export const ResourcesPage = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [tab, setTab] = useState(0);
  const [equipment, setEquipment] = useState<EquipmentDto[]>([]);
  const [personnel, setPersonnel] = useState<PersonnelDto[]>([]);
  const [equipmentForm, setEquipmentForm] = useState<Partial<EquipmentDto>>({
    name: "",
    type: EQUIPMENT_TYPES[0],
    maintenance_requirements: "",
    cost_per_hour: null,
    specifications: {},
    work_schedule: { monthly_hours: 160 }
  });
  const [personnelForm, setPersonnelForm] = useState<Partial<PersonnelDto>>({
    full_name: "",
    position: "",
    qualification: "",
    specialization: "",
    monthly_hours_norm: 160,
    current_load_percent: 0,
    work_schedule: {}
  });

  const loadData = async () => {
    const [eq, ps] = await Promise.all([
      api.get<EquipmentDto[]>("/equipment/"),
      api.get<PersonnelDto[]>("/personnel/")
    ]);
    setEquipment(eq.data);
    setPersonnel(ps.data);
  };

  useEffect(() => {
    const run = async () => {
      try {
        await loadData();
      } catch {
        enqueueSnackbar("Не удалось загрузить ресурсы", { variant: "error" });
      }
    };
    void run();
  }, [enqueueSnackbar]);

  const handleCreateEquipment = async () => {
    try {
      if (!equipmentForm.name?.trim()) {
        enqueueSnackbar("Укажите название оборудования", { variant: "warning" });
        return;
      }
      await api.post("/equipment/", equipmentForm);
      enqueueSnackbar("Оборудование создано", { variant: "success" });
      setEquipmentForm((prev) => ({ ...prev, name: "" }));
      await loadData();
    } catch (err) {
      const message = err instanceof AxiosError ? JSON.stringify(err.response?.data) : "Ошибка создания оборудования";
      enqueueSnackbar(message, { variant: "error" });
    }
  };

  const handleCreatePersonnel = async () => {
    try {
      if (!personnelForm.full_name?.trim()) {
        enqueueSnackbar("Укажите ФИО сотрудника", { variant: "warning" });
        return;
      }
      await api.post("/personnel/", personnelForm);
      enqueueSnackbar("Сотрудник создан", { variant: "success" });
      setPersonnelForm((prev) => ({ ...prev, full_name: "" }));
      await loadData();
    } catch (err) {
      const message = err instanceof AxiosError ? JSON.stringify(err.response?.data) : "Ошибка создания сотрудника";
      enqueueSnackbar(message, { variant: "error" });
    }
  };

  const handleDeleteEquipment = async (id: number) => {
    await api.delete(`/equipment/${id}/`);
    enqueueSnackbar("Оборудование удалено", { variant: "success" });
    await loadData();
  };

  const handleDeletePersonnel = async (id: number) => {
    await api.delete(`/personnel/${id}/`);
    enqueueSnackbar("Сотрудник удален", { variant: "success" });
    await loadData();
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Ресурсы
      </Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Оборудование" />
        <Tab label="Персонал" />
      </Tabs>

      {tab === 0 ? (
        <Grid container spacing={2}>
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Добавить оборудование
              </Typography>
              <TextField
                fullWidth
                label="Название"
                value={equipmentForm.name ?? ""}
                onChange={(e) => setEquipmentForm((prev) => ({ ...prev, name: e.target.value }))}
                sx={{ mb: 1 }}
              />
              <TextField
                select
                fullWidth
                label="Тип"
                value={equipmentForm.type ?? EQUIPMENT_TYPES[0]}
                onChange={(e) => setEquipmentForm((prev) => ({ ...prev, type: e.target.value }))}
                sx={{ mb: 1 }}
              >
                {EQUIPMENT_TYPES.map((type) => (
                  <MenuItem key={type} value={type}>
                    {type}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                fullWidth
                type="number"
                label="Стоимость/час"
                value={equipmentForm.cost_per_hour ?? ""}
                onChange={(e) => setEquipmentForm((prev) => ({ ...prev, cost_per_hour: e.target.value === "" ? null : Number(e.target.value) }))}
                sx={{ mb: 1 }}
              />
              <Button variant="contained" onClick={() => void handleCreateEquipment()}>
                Создать
              </Button>
            </Paper>
          </Grid>
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Список оборудования
              </Typography>
              {equipment.map((item) => (
                <Box key={item.id} sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography>
                    #{item.id} {item.name} ({item.type})
                  </Typography>
                  <Button color="error" size="small" onClick={() => void handleDeleteEquipment(item.id)}>
                    Удалить
                  </Button>
                </Box>
              ))}
            </Paper>
          </Grid>
        </Grid>
      ) : (
        <Grid container spacing={2}>
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Добавить сотрудника
              </Typography>
              <TextField
                fullWidth
                label="ФИО"
                value={personnelForm.full_name ?? ""}
                onChange={(e) => setPersonnelForm((prev) => ({ ...prev, full_name: e.target.value }))}
                sx={{ mb: 1 }}
              />
              <TextField
                fullWidth
                label="Должность"
                value={personnelForm.position ?? ""}
                onChange={(e) => setPersonnelForm((prev) => ({ ...prev, position: e.target.value }))}
                sx={{ mb: 1 }}
              />
              <TextField
                fullWidth
                type="number"
                label="Норма часов в месяц"
                value={personnelForm.monthly_hours_norm ?? ""}
                onChange={(e) => setPersonnelForm((prev) => ({ ...prev, monthly_hours_norm: e.target.value === "" ? null : Number(e.target.value) }))}
                sx={{ mb: 1 }}
              />
              <Button variant="contained" onClick={() => void handleCreatePersonnel()}>
                Создать
              </Button>
            </Paper>
          </Grid>
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Список сотрудников
              </Typography>
              {personnel.map((item) => (
                <Box key={item.id} sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography>
                    #{item.id} {item.full_name} ({item.position || "без должности"})
                  </Typography>
                  <Button color="error" size="small" onClick={() => void handleDeletePersonnel(item.id)}>
                    Удалить
                  </Button>
                </Box>
              ))}
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

