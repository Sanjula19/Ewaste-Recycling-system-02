// Central config for the dashboard shell. Backend health always goes
// through the API Gateway — the dashboard never talks to a component
// backend directly. Each stage's "open" URL is that component's own,
// independently-running frontend.
export const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8080';

export const BRAND = 'E-WASTE INTELLIGENCE';

// The four stages of the physical/process flow. `componentKey` is only used
// internally to read the right entry out of the gateway's /health response —
// it is never shown in the UI.
export const STAGES = [
  {
    id: 'detect',
    path: '/detect',
    componentKey: 'component1',
    label: 'Detect',
    tagline: 'Identify and assess waste',
    description:
      'AI-powered waste identification and condition assessment — classify material type, condition, and grade from a photo.',
    openUrl: import.meta.env.VITE_COMPONENT1_FRONTEND_URL || 'http://localhost:5176',
    openLabel: 'Open Detect',
  },
  {
    id: 'protect',
    path: '/protect',
    componentKey: 'component2',
    label: 'Protect',
    tagline: 'Monitor hazardous conditions',
    description:
      'Real-time toxic-gas and environmental safety monitoring around the processing area. Runs as a fully independent service.',
    openUrl: import.meta.env.VITE_COMPONENT2_FRONTEND_URL || 'http://localhost:5174',
    openLabel: 'Open Protect',
    independent: true,
  },
  {
    id: 'process',
    path: '/process',
    componentKey: 'component3',
    label: 'Process',
    tagline: 'Choose the right recycling process',
    description:
      'Recycling and process optimization using material and moisture information, to route each batch through the right treatment.',
    openUrl: import.meta.env.VITE_COMPONENT3_FRONTEND_URL || 'http://localhost:3000',
    openLabel: 'Open Process',
  },
  {
    id: 'recover',
    path: '/recover',
    componentKey: 'component4',
    label: 'Recover',
    tagline: 'Understand recovery value',
    description:
      'Economic valuation, disposition routing, and market analytics for recovered materials.',
    openUrl: import.meta.env.VITE_COMPONENT4_FRONTEND_URL || 'http://localhost:5175',
    openLabel: 'Open Recover',
  },
];
