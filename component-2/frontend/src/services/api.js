import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 10000,
});

// Health
export const getHealth = () => api.get("/health");

// Readings
export const getLatestReading = () => api.get("/readings/latest", {
  params: { _ts: Date.now() },
});
export const getReadings = (params = {}) => api.get("/readings", {
  params: { ...params, _ts: Date.now() },
});

// Alerts
export const getAlerts = (params = {}) => api.get("/alerts", {
  params: { ...params, _ts: Date.now() },
});
export const acknowledgeAlert = (alertId) => api.put(`/alerts/${alertId}/acknowledge`);

// Dashboard
export const getDashboardStats = () => api.get("/dashboard/stats", {
  params: { _ts: Date.now() },
});
export const getChartData = (params = {}) => api.get("/dashboard/chart-data", {
  params: { ...params, _ts: Date.now() },
});

export default api;
