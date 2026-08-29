// Central place for the URLs this shell needs. Backend health always goes
// through the API Gateway — the dashboard never talks to a component
// backend directly. Frontend links are the components' own dev servers.
export const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8080';

export const COMPONENTS = [
  {
    id: 'component1',
    key: 'component1',
    name: 'Component 1 — AI Waste Assessment',
    owner: 'Shehan',
    path: '/component1',
    description:
      'Camera + weight based AI classification of general waste and e-waste at the physical intake point.',
    hasFrontend: false,
    openUrl: import.meta.env.VITE_COMPONENT1_BACKEND_URL || 'http://localhost:8001',
    openLabel: 'Open backend API (/docs)',
    workflow: 'C1 → C3 → C4',
  },
  {
    id: 'component2',
    key: 'component2',
    name: 'Component 2 — Toxic Gas Detection',
    owner: 'Sanjula',
    path: '/component2',
    description:
      'Real-time toxic gas detection via ESP32 + MQ-sensor array. Runs as a fully independent service.',
    hasFrontend: true,
    openUrl: import.meta.env.VITE_COMPONENT2_FRONTEND_URL || 'http://localhost:5174',
    openLabel: 'Open Toxic Gas Detection dashboard',
    workflow: 'INDEPENDENT — not part of C1 → C3 → C4',
  },
  {
    id: 'component3',
    key: 'component3',
    name: 'Component 3 — Smart Process Optimization',
    owner: 'Wisu',
    path: '/component3',
    description:
      'Moisture-based recycling process recommendations for sorted material batches.',
    hasFrontend: true,
    openUrl: import.meta.env.VITE_COMPONENT3_FRONTEND_URL || 'http://localhost:3000',
    openLabel: 'Open Process Optimization dashboard',
    workflow: 'C1 → C3 → C4',
    limitation:
      'The real Smart Process Optimization backend is not yet available in this repository. ' +
      'The frontend may load, but its API calls (e.g. /api/optimize) will fail until the real backend is deployed on port 8003.',
  },
  {
    id: 'component4',
    key: 'component4',
    name: 'Component 4 — Economic Valuation',
    owner: 'Mayashi',
    path: '/component4',
    description:
      'Metal price forecasting and disposition routing for recovered materials.',
    hasFrontend: true,
    openUrl: import.meta.env.VITE_COMPONENT4_FRONTEND_URL || 'http://localhost:5175',
    openLabel: 'Open Economic Valuation dashboard',
    workflow: 'C1 → C3 → C4',
  },
];
