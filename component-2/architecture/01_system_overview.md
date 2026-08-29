# 01 — System Overview

## 1.1 Research Title

**"Real-Time Toxic Gas Detection and Classification System for E-Waste Processing Environments Using IoT Sensors and Machine Learning"**

---

## 1.2 Problem Statement

Electronic waste (e-waste) is the world's fastest-growing solid waste stream, generating **53.6 million metric tonnes per year** (Global E-Waste Monitor, 2019). During informal and semi-formal e-waste dismantling and recycling, workers are exposed to a range of highly toxic gases released from components such as printed circuit boards, CRT monitors, batteries, and capacitors.

**Current systems fail because:**
- Manual/visual inspection is reactive, not preventive
- Single-gas detectors cannot identify the *source device* of contamination
- No integration of WHO/NIOSH safety thresholds with real-time feedback
- No machine learning classification to distinguish gas types from sensor array patterns
- Collected data is siloed — no historical trend analysis or reporting

---

## 1.3 Research Objectives

| # | Objective | Type |
|---|-----------|------|
| O1 | Design a multi-sensor IoT hardware system capable of simultaneously detecting CO, Mercury Vapor, Benzene, Ammonia, H₂S, and LPG | Hardware |
| O2 | Train and evaluate a multi-class ML classifier (Random Forest vs SVM vs Decision Tree vs Naive Bayes) for gas-type identification | ML |
| O3 | Build a knowledge base linking gas signatures → e-waste source devices → health hazards → recommended actions | Knowledge |
| O4 | Implement a WHO/NIOSH threshold comparison engine with GREEN/YELLOW/RED risk assessment | Safety |
| O5 | Develop a real-time web dashboard for live monitoring, historical analysis, and alert management | Frontend |
| O6 | Validate system performance using collected real-world + benchmark datasets | Validation |

---

## 1.4 System Architecture Layers (High-Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: HARDWARE                            │
│   ESP32 + [MQ-2, MQ-7, MQ-135, MQ-303, MQ-136] + DHT22            │
│   + LCD 16x2 + LEDs (R/Y/G) + Active Buzzer                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ MQTT over WiFi (HiveMQ Cloud)
┌──────────────────────────▼──────────────────────────────────────────┐
│                     LAYER 2: COMMUNICATION                          │
│   MQTT Broker (HiveMQ) ──► FastAPI Subscriber → Message Queue      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Internal API calls
┌──────────────────────────▼──────────────────────────────────────────┐
│                       LAYER 3: BACKEND                              │
│   FastAPI (Python)                                                  │
│   ├── MQTT Subscriber Service                                       │
│   ├── ML Inference Service (Random Forest .pkl)                     │
│   ├── Knowledge Base Query Engine                                   │
│   ├── WHO Threshold Comparison Engine                               │
│   ├── Alert Manager                                                 │
│   └── REST API (for Dashboard + ESP32 commands)                     │
└──────────┬────────────────────────────────────────┬────────────────┘
           │                                        │
┌──────────▼──────────┐               ┌────────────▼───────────────┐
│   LAYER 4: DATABASE │               │    LAYER 5: ML PIPELINE    │
│                     │               │                            │
│  Firebase RT DB     │               │  Training Notebooks        │
│  (live readings)    │               │  (Jupyter)                 │
│                     │               │                            │
│  PostgreSQL         │               │  Random Forest (main)      │
│  (history, alerts,  │               │  SVM / DT / NB (compare)   │
│   reports)          │               │                            │
│                     │               │  Saved model → .pkl        │
│  JSON Knowledge     │               │  → loaded by FastAPI       │
│  Base               │               └────────────────────────────┘
└──────────┬──────────┘
           │ Firebase SDK + REST
┌──────────▼──────────────────────────────────────────────────────────┐
│                      LAYER 6: FRONTEND                              │
│   React.js Dashboard                                                │
│   ├── Page 1: Live Gas Monitor (5-sec refresh)                      │
│   ├── Page 2: Hazard Alert + Device Source + Action Plan            │
│   ├── Page 3: Historical Data + CSV Export                          │
│   └── Page 4: ML Model Performance Metrics                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1.5 Target Gases and Sensor Mapping

| Gas | Sensor | WHO/NIOSH Limit | Source E-Waste Device |
|-----|--------|------------------|-----------------------|
| Carbon Monoxide (CO) | MQ-7 | 25 ppm (NIOSH TWA) | PCBs during burning, soldering |
| LPG / Propane / Methane | MQ-2 | 1000 ppm (LEL check) | Batteries, capacitors |
| Benzene (VOC) | MQ-135 | 0.5 ppm (OSHA TWA) | Plastics, insulation |
| Ammonia (NH₃) | MQ-135 | 25 ppm (NIOSH TWA) | Batteries (NiCd, NiMH) |
| Mercury Vapor (Hg) | MQ-303 | 0.025 mg/m³ (WHO) | CRT monitors, fluorescent lamps |
| Hydrogen Sulphide (H₂S) | MQ-136 | 1 ppm (NIOSH ceiling) | Lithium batteries, solder |

---

## 1.6 Novel Contributions

1. **Multi-sensor gas array** specifically calibrated for e-waste toxic gas profiles
2. **Gas-to-device knowledge base** — first of its kind mapping gas signatures to source e-waste items
3. **WHO-integrated risk engine** with real-time automated threshold comparison
4. **Comparative ML study** in the e-waste context (RF vs SVM vs DT vs NB)
5. **Collected real-world dataset** from simulated e-waste lab environment
6. **End-to-end integrated platform** from hardware sensor to web dashboard

---

## 1.7 System Boundaries

**In scope:**
- Indoor e-waste processing facility monitoring
- Static sensor node (one ESP32 unit)
- 6 target toxic gases listed in 1.5
- ML classification (not prediction / forecasting)

**Out of scope:**
- Outdoor/mobile monitoring
- GPS tracking of gas plumes
- Multi-node sensor networks (future work)
- Gas concentration quantification (ppm regression) — classification only
