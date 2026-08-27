# EcoVision Frontend — Component 4

React + Vite dashboard for the Predictive Economic Valuation & Strategic
Disposition backend. Built to be usable by non-technical municipal council
and e-waste centre staff, not just a developer-facing UI.

## What's implemented against your requirements

| Requirement | Where |
|---|---|
| 3 languages (English, Sinhala, Tamil) with a select dropdown | Header language selector; `src/i18n/en.js` / `si.js` / `ta.js` |
| Live date and time | Header clock, locale-aware formatting (updates every second) |
| Dark and light mode | Header toggle, persisted, respects system preference on first visit |
| Tonnage manifest PDF download | Manifest page — current cycle and any past cycle |
| Professional, municipal-council-appropriate UI | See "Design notes" below |

## Setup

```bash
npm install
cp .env.example .env      # edit VITE_API_BASE_URL if your backend isn't on localhost:8000
npm run dev
```

Opens on `http://localhost:5173` by default — this matches the CORS origin
already configured in the backend's `main.py`, so no backend changes are
needed. **Start the backend first** (`uvicorn main:app --reload`); the app
detects and clearly reports when it can't reach it, rather than showing a
blank page.

### Production build

```bash
npm run build      # outputs to dist/
npm run preview    # serve the built version locally to check it
```

`dist/` is static files — deployable to any static host (nginx, GitHub
Pages, Netlify, etc.), pointed at wherever the backend actually runs in
production via `VITE_API_BASE_URL`.

## Translation accuracy — please verify before real deployment

The Sinhala and Tamil translations are my best effort at accurate,
standard technical/civic register for this domain, and I verified
programmatically that all three language files have **exactly the same
125 keys** (no missing or mistranslated-into-the-wrong-slot strings) — but
I'm not a certified native speaker of either language. Before this goes in
front of an actual municipal council, it's worth having a native Sinhala
and Tamil speaker read through `src/i18n/si.js` and `src/i18n/ta.js` — the
structure and completeness are verified; the phrasing quality isn't.

## Design notes

Palette and typography were chosen for this specific brief, not a
template default:

- **Deep teal + copper accent** — teal for civic/environmental trust,
  copper because it's literally one of the tracked materials, not a
  decorative color choice.
- **Material identity colors** (`src/utils/materials.js` +
  `src/styles/tokens.css`) — every material (aluminium, copper, PVC,
  glass, ...) keeps the same color everywhere it appears: dropdowns,
  chart lines, table rows. This is the app's one consistent signature
  element rather than a one-off hero graphic, which fits a dashboard
  people will use daily more than a marketing-style opener would.
- **Noto Serif / Noto Sans + their Sinhala and Tamil companions** — this
  is a hard requirement, not a style pick: most distinctive display fonts
  don't have Sinhala or Tamil glyphs, so a typeface that couldn't render
  all three scripts would break the moment someone switches languages.

## What I could verify here, and what I couldn't

This was built in a sandboxed environment with no access to the npm
registry, so `npm install` / `npm run build` / `npm run dev` were never
actually run against this code. What I *did* verify programmatically
before handing this over:

- All three translation files (`en.js`, `si.js`, `ta.js`) have identical
  key structure — checked by actually importing all three via Node's ESM
  loader and deep-comparing every key path, not by eye.
- Every `t('...')` call across all 19 source files resolves to a real key
  that exists in the dictionaries — same method, not a visual scan.
- Every field name the frontend reads from an API response (e.g.
  `result.energy_recovery_kwh`, `result.nearest_treatment_facility.name`)
  was cross-checked line-by-line against the actual Pydantic schemas in
  the backend, not assumed.
- Brace/paren balance on every `.jsx`/`.js` file, and valid JSON on
  `package.json`.

Treat your first `npm run dev` as a real first test, not a formality —
there could be a typo or an import path issue I couldn't catch without an
actual bundler running.
