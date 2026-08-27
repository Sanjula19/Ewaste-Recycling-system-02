/*
  Thin fetch wrapper around the Component 4 backend. One function per
  endpoint, all returning parsed JSON (or a Blob for the PDF), and all
  throwing an Error whose .message is the backend's own `detail` text
  when available -- so the UI can show the real reason a request failed
  instead of a generic "something went wrong".
*/

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (networkErr) {
    throw new ApiError('NETWORK_UNREACHABLE', 0);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* response wasn't JSON -- keep the generic message */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json();
}

export function checkHealth() {
  return request('/api/health');
}

export function getSupportedMetals() {
  return request('/api/forecast/supported-metals');
}

export function getForecast(metal, weightKg) {
  return request('/api/forecast/', {
    method: 'POST',
    body: JSON.stringify({ metal, weight_kg: weightKg }),
  });
}

export function getDisposition({ wasteType, weightKg, facilityName, latitude, longitude }) {
  const payload = { waste_type: wasteType, weight_kg: weightKg };
  if (facilityName) payload.facility_name = facilityName;
  if (latitude != null && latitude !== '') payload.latitude = Number(latitude);
  if (longitude != null && longitude !== '') payload.longitude = Number(longitude);
  return request('/api/disposition/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getMarketOverview() {
  return request('/api/market/overview');
}

export function getManifestSummary(cycleId) {
  const q = cycleId != null ? `?cycle_id=${cycleId}` : '';
  return request(`/api/manifest/summary${q}`);
}

export function getManifestCycles() {
  return request('/api/manifest/cycles');
}

export function resetManifestCycle() {
  return request('/api/manifest/reset', { method: 'POST' });
}

/** Downloads the manifest PDF and triggers a browser save -- not JSON, handled separately. */
export async function downloadManifestPdf({ facilityName, cycleId } = {}) {
  const params = new URLSearchParams();
  if (facilityName) params.set('facility_name', facilityName);
  if (cycleId != null) params.set('cycle_id', cycleId);
  const query = params.toString() ? `?${params.toString()}` : '';

  const response = await fetch(`${BASE_URL}/api/manifest/pdf${query}`);
  if (!response.ok) {
    throw new ApiError(`Could not generate the PDF (${response.status})`, response.status);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = cycleId ? `tonnage_manifest_cycle_${cycleId}.pdf` : 'tonnage_manifest.pdf';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export { ApiError };
