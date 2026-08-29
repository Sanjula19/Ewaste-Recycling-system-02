# Common Dashboard — E-Waste Recycling System

A thin navigation shell that makes the four independent components feel like
one system. **It contains no business logic and does not embed or rewrite
any component's UI** — every "Open" action launches that component's own
existing frontend in a new tab, unchanged.

---

## What this is NOT

- Not a merged frontend — each component keeps its own `package.json`,
  dependencies, dev server, and UI.
- Not an iframe wrapper — components open in their own tab so their own
  routing/cookies/CORS behave exactly as before.
- Not an orchestrator — it has no knowledge of the C1 → C3 → C4 workflow and
  makes no business-logic calls. It only reads `GET /health` from the API
  Gateway to show status dots.

---

## Start

```bash
cd dashboard
npm install
cp .env.example .env   # optional — defaults match the documented port map
npm run dev
# Dashboard available at http://localhost:3010
```

## Routes

| Route | Page |
|---|---|
| `/` | redirects to `/dashboard` |
| `/dashboard` | System Overview — cards for all 4 components + status |
| `/component1` | Component 1 — AI Waste Assessment (Shehan) |
| `/component2` | Component 2 — Toxic Gas Detection (Sanjula) — **independent** |
| `/component3` | Component 3 — Smart Process Optimization (Wisu) |
| `/component4` | Component 4 — Economic Valuation (Mayashi) |

## How each component is opened

Every component page has an **Open** button that opens `target="_blank"` to
the component's own dev server:

| Component | Opens |
|---|---|
| Component 1 | `http://localhost:8001` (no web frontend exists — backend API/docs link only) |
| Component 2 | `http://localhost:5174` (existing Toxic Gas Detection dashboard) |
| Component 3 | `http://localhost:3000` (existing frontend — see limitation note below) |
| Component 4 | `http://localhost:5175` (existing EcoVision dashboard) |

Configurable via `.env` (`VITE_COMPONENT{1..4}_*_URL`) — never hard-coded
inside components, only in `src/config.js`.

## Status indicators

Status dots (Online / Offline / Unhealthy / Unknown) come from a single
`GET {VITE_GATEWAY_URL}/health` call (default `http://localhost:8080/health`),
polled every 15s. The dashboard never calls component backends directly —
only the gateway's existing aggregator. If the gateway itself is unreachable,
every status shows Unknown and a banner is shown on the Overview page.

## Component 3 limitation

The real Smart Process Optimization backend is not present in this
repository yet (see `integration/INTEGRATION_STATUS.md`). The `/component3`
page shows an explicit warning banner about this and still links to the
existing frontend — clicking through may show broken API calls in that
frontend until the real backend is deployed on port 8003. This dashboard
does not fabricate or fake any Component 3 result.

## Independence

- No dependency on any component's `package.json` — this app has its own.
- No component source code was copied or modified to build this shell.
- Component 2 is explicitly called out as independent on its detail page,
  and is not referenced by, and does not reference, any other component's
  page or data.
