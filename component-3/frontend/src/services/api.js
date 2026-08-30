const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8003';

export async function optimizeProcess(data) {
  const response = await fetch(`${BASE_URL}/api/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getHistory() {
  const response = await fetch(`${BASE_URL}/api/history`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getHealth() {
  const response = await fetch(`${BASE_URL}/api/health`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getMaterials() {
  const response = await fetch(`${BASE_URL}/api/materials`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getPendingDetections() {
  try {
    const response = await fetch(`${BASE_URL}/api/detections/pending`);
    if (!response.ok) return { count: 0, detections: [] };
    return await response.json();
  } catch {
    // Backend not reachable — just skip this poll
    return { count: 0, detections: [] };
  }
}

// ── Reports ────────────────────────────────────────────────────────────
// Every report is computed from the real optimization_results collection —
// same source /api/history reads from. No mock data.

export async function generateReport(filters) {
  const response = await fetch(`${BASE_URL}/api/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function listReports(limit = 50) {
  const response = await fetch(`${BASE_URL}/api/reports?limit=${limit}`);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function getReport(id) {
  const response = await fetch(`${BASE_URL}/api/reports/${id}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function deleteReport(id) {
  const response = await fetch(`${BASE_URL}/api/reports/${id}`, { method: 'DELETE' });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function getReportFilterOptions() {
  const response = await fetch(`${BASE_URL}/api/reports/filter-options`);
  if (!response.ok) return { materials: [], waste_types: [], safety_statuses: [], report_types: [] };
  return await response.json();
}

export async function getLatestMoisture() {
  try {
    const response = await fetch(`${BASE_URL}/api/sensor/moisture/latest`);
    if (!response.ok) return { moisture_status: null, raw_value: null };
    return await response.json();
  } catch {
    // Sensor not connected — return null gracefully
    return { moisture_status: null, raw_value: null };
  }
}