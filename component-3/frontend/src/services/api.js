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

export async function getLatestMoisture() {
  const response = await fetch(`${BASE_URL}/api/sensor/moisture/latest`);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}