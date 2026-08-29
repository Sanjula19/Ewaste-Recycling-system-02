const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8080';

// All requests go through the API Gateway's Component 1 proxy
// (/api/component1/*), never directly to port 8001.
const BASE = `${GATEWAY_URL}/api/component1`;

async function parseJsonOrThrow(res) {
  let body;
  try {
    body = await res.json();
  } catch {
    throw new Error(`Unexpected response (HTTP ${res.status})`);
  }
  if (!res.ok) {
    throw new Error(body?.error || body?.detail || `Request failed (HTTP ${res.status})`);
  }
  return body;
}

export async function checkHealth() {
  const res = await fetch(`${BASE}/health`);
  return parseJsonOrThrow(res);
}

export async function predictWaste(file) {
  const form = new FormData();
  form.append('image', file);
  const res = await fetch(`${BASE}/waste/predict`, { method: 'POST', body: form });
  return parseJsonOrThrow(res);
}

export async function analyzeEwaste(file) {
  const form = new FormData();
  form.append('image', file);
  const res = await fetch(`${BASE}/ewaste/analyze`, { method: 'POST', body: form });
  return parseJsonOrThrow(res);
}
