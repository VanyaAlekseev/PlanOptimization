import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { api } from "../api/client";
import type { ProjectDto } from "../api/types";

export interface DashboardState {
  projects: ProjectDto[];
  loading: boolean;
  error: string | null;
}

const initialState: DashboardState = {
  projects: [],
  loading: false,
  error: null
};

// Загрузка списка проектов с backend.
export const fetchProjects = createAsyncThunk<ProjectDto[]>(
  "dashboard/fetchProjects",
  async () => {
    const { data } = await api.get<ProjectDto[]>("/projects/");
    return data;
  }
);

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchProjects.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.loading = false;
        state.projects = action.payload;
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? "Ошибка загрузки проектов";
      });
  }
});

export default dashboardSlice.reducer;

