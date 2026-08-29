# Component 1 Frontend — AI Waste Assessment ("Detect")

Simple, independent frontend for Component 1. Did not exist before this
step — Component 1 previously had no web UI (only a Raspberry Pi script).

## Start

```bash
cd component-1/frontend
npm install
npm run dev
# http://localhost:5176
```

## What it does

- Upload an image, pick "General Waste" or "E-Waste" mode, click Analyze.
- Calls the API Gateway only (`VITE_GATEWAY_URL`, default `http://localhost:8080`):
  - `GET /api/component1/health`
  - `POST /api/component1/waste/predict` (General Waste mode)
  - `POST /api/component1/ewaste/analyze` (E-Waste mode)
- Renders only fields the backend actually returns — `waste_type`,
  `waste_confidence`, `condition`, `condition_confidence`, `final_grade` for
  general waste; `detected_type`, `confidence`, `screening_hazard_level`,
  `possible_hazards`, `recommended_ppe`, `handling_instructions`,
  `escalation_rule`, `certainty_note` for e-waste. Nothing is invented.

## Independence

Own `package.json`, own dev server (port 5176), no shared code with the
common dashboard or any other component's frontend.
