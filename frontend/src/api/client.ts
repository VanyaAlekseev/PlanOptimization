import axios from "axios";

// Базовый HTTP‑клиент для всех запросов к backend.
export const api = axios.create({
  baseURL: "/api",
  timeout: 15000
});

