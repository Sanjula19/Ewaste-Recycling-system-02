# E-Waste Intelligence — Common Dashboard

A product-style shell that tells the story of the platform — **Waste →
Detect → Protect → Process → Recover** — and launches each underlying
application. **It contains no business logic and does not embed or rewrite
any component's UI.** Every "Open" action launches that section's own
existing frontend in a new tab, unchanged.

---

## What this is NOT

- Not a merged frontend — each section keeps its own `package.json`,
  dependencies, dev server, and UI.
- Not an iframe wrapper — sections open in their own tab so their own
  routing/cookies/CORS behave exactly as before.
- Not an orchestrator — it has no knowledge of any cross-service workflow
  and makes no business-logic calls. It only reads `GET /health` from the
  API Gateway to show status.

---

## Start

```bash
cd dashboard
npm install
cp .env.example .env   # optional — defaults match the documented port map
npm run dev
# Dashboard available at http://localhost:3010
```

## Navigation

| Route | Page |
|---|---|
| `/` | Overview — hero, flow diagram, section cards, live status, quick actions |
| `/detect` | AI waste identification and condition assessment |
| `/protect` | Toxic-gas and environmental safety monitoring — **independent service** |
| `/process` | Recycling/process optimization using material and moisture data |
| `/recover` | Economic/disposition/analytics insights |
| `/history` | Links out to each section's own history/logs feature |

Old Step-6 paths (`/dashboard`, `/component1..4`) redirect to the new routes.

## How each section is opened

Every section has an **Open** action using a plain `<a target="_blank">` to
its own running dev server — never an iframe, never merged code:

| Section | Underlying app | Opens |
|---|---|---|
| Detect | Component 1 frontend (new, Step 6B) | `http://localhost:5176` |
| Protect | Component 2's existing dashboard | `http://localhost:5174` |
| Process | Component 3's existing dashboard | `http://localhost:3000` |
| Recover | Component 4's existing dashboard | `http://localhost:5175` |

Configurable via `.env` (`VITE_COMPONENT{1..4}_FRONTEND_URL`).

## Status indicators

Status comes from a single `GET {VITE_GATEWAY_URL}/health` call (default
`http://localhost:8080/health`), polled every 15s. The dashboard never calls
component backends directly — only the gateway's existing aggregator. The
navbar's overall pill mirrors the gateway's own `overall_status`.

## What changed from Step 6

The previous shell presented four labeled "component" cards with owner
names. This version replaces that with the Detect/Protect/Process/Recover
narrative — no component numbers or member names appear in the UI. The
underlying wiring (gateway health polling, new-tab launches, independence of
each section) is unchanged. `Header.jsx`, `Sidebar.jsx`, `ComponentCard.jsx`,
and `ComponentDetail.jsx` were removed and replaced by `Navbar.jsx`,
`FlowDiagram.jsx`, `StageCard.jsx`, and `StageDetail.jsx`.

## Process limitation

The real Process backend is not present in this repository yet (see
`integration/INTEGRATION_STATUS.md`). The `/process` page shows an explicit
warning about this and still links to the existing frontend — this
dashboard does not fabricate or fake any Process result.
