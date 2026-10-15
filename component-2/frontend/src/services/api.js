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

// ML Prediction (classify latest reading + create alerts)
export const getPrediction = () => api.get("/predict/status", {
  params: { _ts: Date.now() },
});

// Alerts
export const getAlerts = (params = {}) => api.get("/alerts", {
  params: { ...params, _ts: Date.now() },
});
export const getRecentAlerts = (limit = 5) => api.get("/alerts", {
  params: { limit, skip: 0, _ts: Date.now() },
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

