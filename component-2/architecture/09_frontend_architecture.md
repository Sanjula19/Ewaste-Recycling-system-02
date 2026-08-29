# 09 — Frontend Architecture

## 9.1 Frontend Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React.js | 18+ | UI framework with hooks + context |
| React Router | v6 | Client-side routing (4 pages) |
| Recharts | 2.x | Gas level charts, trend lines |
| Firebase JS SDK | 10.x | Real-time data subscription |
| Axios | 1.x | REST API calls to FastAPI backend |
| Context API | Built-in | Global state management |
| CSS Modules / Tailwind | — | Component styling |

---

## 9.2 Application Routing (4 Pages)

```
/                       → LiveMonitor.jsx     (default redirect)
/monitor                → LiveMonitor.jsx     (Page 1)
/alerts                 → HazardAlert.jsx     (Page 2)
/history                → HistoricalData.jsx  (Page 3)
/ml-performance         → MLPerformance.jsx   (Page 4)
```

---

## 9.3 Component Tree

```
<App>
├── <Navbar>                    ← Navigation + system status badge
├── <Sidebar>                   ← Page links + active alert count badge
│
├── <Route: /monitor>
│   └── <LiveMonitor>
│       ├── <StatusIndicator>   ← ESP32 Online/Offline
│       ├── <GasReadingCard>    (×5, one per sensor)
│       │   ├── Sensor name
│       │   ├── Current ppm
│       │   ├── WHO limit
│       │   └── <AlertBadge>    ← G/Y/R
│       ├── <GasLevelGauge>     ← Animated gauge chart (Recharts RadialBar)
│       ├── <TrendLineChart>    ← Last 60 readings line chart
│       └── <CurrentAlertBanner> ← Floating RED banner if danger
│
├── <Route: /alerts>
│   └── <HazardAlert>
│       ├── <AlertCard>         ← Detailed alert with actions
│       │   ├── Gas name + confidence badge
│       │   ├── WHO comparison bar
│       │   ├── Source device
│       │   ├── Health risk list
│       │   └── Action checklist
│       └── <AlertHistory>      ← Table of past alerts
│
├── <Route: /history>
│   └── <HistoricalData>
│       ├── <DateRangePicker>
│       ├── <TrendLineChart>    ← Full historical trend (multi-line)
│       ├── <SummaryStatsCards> ← Total readings, RED events, etc.
│       ├── <DataTable>         ← Paginated readings table
│       └── <ExportButton>      ← Download as CSV
│
└── <Route: /ml-performance>
    └── <MLPerformance>
        ├── <ModelSummaryCard>  ← Active model, version, accuracy
        ├── <ModelCompareBar>   ← Bar chart: RF vs SVM vs DT vs NB
        ├── <ConfusionMatrix>   ← Heatmap visualization
        └── <FeatureImportance> ← Horizontal bar chart
```

---

## 9.4 State Management (Context API)

```jsx
// store/AppContext.jsx

const AppContext = createContext();

const initialState = {
  // Live monitor
  currentReading: null,
  deviceStatus:   'offline',
  riskLevel:      'GREEN',

  // Alerts
  activeAlerts:   [],
  alertCount:     0,

  // System
  isLoading:      false,
  lastUpdated:    null,
};

function appReducer(state, action) {
  switch (action.type) {
    case 'SET_READING':     return { ...state, currentReading: action.payload };
    case 'SET_RISK_LEVEL':  return { ...state, riskLevel: action.payload };
    case 'ADD_ALERT':       return { ...state, activeAlerts: [action.payload, ...state.activeAlerts] };
    case 'SET_DEVICE_STATUS': return { ...state, deviceStatus: action.payload };
    default: return state;
  }
}
```

---

## 9.5 Firebase Real-Time Hook

```jsx
// hooks/useFirebase.js

import { useEffect, useState } from 'react';
import { ref, onValue } from 'firebase/database';
import { db } from '../services/firebase';

export function useCurrentReading(deviceId) {
  const [reading, setReading] = useState(null);

  useEffect(() => {
    const dbRef = ref(db, `ewaste_system/devices/${deviceId}/current_reading`);

    const unsubscribe = onValue(dbRef, (snapshot) => {
      if (snapshot.exists()) {
        setReading(snapshot.val());
      }
    });

    return () => unsubscribe();  // Cleanup on unmount
  }, [deviceId]);

  return reading;
}
```

---

## 9.6 Dashboard Pages — Detailed Design

### Page 1: Live Gas Monitor

```
┌─────────────────────────────────────────────────────────────────┐
│  🟢 ESP32 Online  │  Last updated: 3 sec ago  │  [⚡ LIVE]     │
├──────────┬────────┬────────┬────────┬─────────────────────────-─┤
│ MQ-2     │ MQ-7   │MQ-135  │MQ-303  │ MQ-136                   │
│ LPG      │ CO     │ VOC    │Mercury │ H₂S                      │
│          │        │        │        │                           │
│ 45.3 ppm │12.1 ppm│ 8.7ppm │0.022mg │ 0.5 ppm                 │
│ [GREEN]  │[GREEN] │[GREEN] │ [RED!] │ [GREEN]                  │
└──────────┴────────┴────────┴────────┴─────────────────────────-─┘
│                                                                 │
│  📊 Trend - Last 30 readings (5-sec intervals)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    [Line Chart]                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🌡 Temperature: 28.4°C    💧 Humidity: 65.2%                   │
└─────────────────────────────────────────────────────────────────┘
```

### Page 2: Hazard Alert

```
┌─────────────────────────────────────────────────────────────────┐
│  🔴 ACTIVE HAZARD ALERT                                         │
│                                                                 │
│  Gas Detected:   Mercury Vapor (Hg)        Confidence: 94.3%   │
│  Risk Level:     ████████████████████ EXCEEDED BY 80%          │
│  WHO Limit:      0.025 mg/m³                                    │
│  Current Level:  0.045 mg/m³                                    │
│                                                                 │
│  Likely Source:  CRT Monitor / Flat-screen Display              │
│                                                                 │
│  ⚠ Health Risks:                                               │
│  • Neurological damage         • Brain damage                  │
│  • Kidney failure              • Respiratory damage            │
│                                                                 │
│  📋 Required Actions:                                           │
│  ☐ 1. Evacuate area immediately                                │
│  ☐ 2. Wear supplied-air respirator                             │
│  ☐ 3. Notify safety officer                                    │
│  ☐ 4. Do not handle device                                     │
│                                                                 │
│  Time: 2026-07-31 14:52:10    Device: Workstation 3           │
│                                                [ACKNOWLEDGE]   │
└─────────────────────────────────────────────────────────────────┘

  📜 Alert History
  ┌────────────┬──────────┬──────────┬───────────┬───────────┐
  │ Time       │ Gas      │ Level    │ Device    │ Status    │
  ├────────────┼──────────┼──────────┼───────────┼───────────┤
  │ 14:52:10   │ Mercury  │ 🔴 RED  │ WS-3      │ Active    │
  │ 12:30:05   │ CO       │ 🟡 WARN │ WS-3      │ Cleared   │
  └────────────┴──────────┴──────────┴───────────┴───────────┘
```

### Page 3: Historical Data

```
┌──────────────────────────────────────────────────────────────────┐
│  📅 Date Range: [07/01/2026] → [07/31/2026]   [🔍 Filter]       │
│                                                                  │
│  Summary Cards:                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 8,640    │ │   45     │ │  120     │ │Mercury   │           │
│  │ Readings │ │🔴 Red    │ │🟡 Yellow │ │Most freq.│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  [Multi-line trend chart: 30-day]                                │
│                                                                  │
│  Data Table (paginated, 20 rows/page):                           │
│  ┌──────────┬───────┬───────┬────────┬────────┬────────┬──────┐ │
│  │Timestamp │MQ2 ppm│MQ7 ppm│Gas     │Risk    │Conf%   │Action│ │
│  ├──────────┼───────┼───────┼────────┼────────┼────────┼──────┤ │
│  │14:52:10  │ 45.3  │ 12.1  │Mercury │🔴 RED │ 94.3%  │View  │ │
│  └──────────┴───────┴───────┴────────┴────────┴────────┴──────┘ │
│                                                                  │
│  [⬇ Download CSV]   [⬇ Download PDF Report]                     │
└──────────────────────────────────────────────────────────────────┘
```

### Page 4: ML Performance

```
┌──────────────────────────────────────────────────────────────────┐
│  🤖 Active Model: Random Forest v1                               │
│  Trained: 2026-06-15  |  Dataset: 4,850 samples  |  7 classes   │
│                                                                  │
│  Model Comparison:                                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Random Forest  ████████████████████████████  97.3%     │    │
│  │ SVM            ██████████████████████        93.1%     │    │
│  │ Decision Tree  ████████████████████          89.4%     │    │
│  │ Naive Bayes    ████████████████              82.6%     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Confusion Matrix:          Feature Importance:                  │
│  [Heatmap]                  [Horizontal bar chart]               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9.7 Color System (Theme)

```css
/* Risk levels */
--color-green:  #22c55e;   /* Safe */
--color-yellow: #f59e0b;   /* Caution */
--color-red:    #ef4444;   /* Danger */
--color-red-bg: #fef2f2;   /* Alert background */

/* Brand */
--color-primary:   #1e40af;  /* Deep blue */
--color-bg:        #0f172a;  /* Dark mode background */
--color-surface:   #1e293b;  /* Card background */
--color-text:      #f1f5f9;  /* Primary text */
--color-muted:     #94a3b8;  /* Muted text */
--color-border:    #334155;  /* Borders */
```
