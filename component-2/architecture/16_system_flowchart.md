# 16 — System Flowchart (Hand-Draw Reference)

> **Purpose:** Simple flowchart to explain the system to your supervisor.  
> Draw this on paper — box by box, arrow by arrow.

---

```
                    ┌─────────────────────────┐
                    │                         │
                    │      E-WASTE ITEMS       │
                    │   (CRT, PCB, Battery)    │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 │  releases toxic gases
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │                         │
                    │    GAS SENSORS (×5)      │
                    │  MQ-2, MQ-7, MQ-135,    │
                    │   MQ-303, MQ-136         │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 │  analog voltage reading
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │                         │
                    │       ESP32 (MCU)        │
                    │   converts voltage →     │
                    │        ppm value         │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 │  sends data via WiFi (MQTT)
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │                         │
                    │    CLOUD MQTT BROKER     │
                    │       (HiveMQ)           │+
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 │  message received
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │                         │
                    │    BACKEND (FastAPI)      │
                    │                         │
                    └────┬──────────┬─────────┘
                         │          │
              ┌──────────┘          └──────────┐
              │                                │
              ▼                                ▼
  ┌───────────────────┐            ┌───────────────────────┐
  │                   │            │                       │
  │   ML MODEL         │            │   WHO THRESHOLD        │
  │ (Random Forest)   │            │     COMPARISON         │
  │                   │            │                       │
  │  Input: 7 sensor  │            │  ppm reading vs limit  │
  │  values           │            │                       │
  │                   │            │  < limit  → GREEN      │
  │  Output:          │            │  near limit → YELLOW   │
  │  Gas Type +       │            │  over limit → RED      │
  │  Confidence %     │            │                       │
  └────────┬──────────┘            └───────────┬───────────┘
           │                                   │
           │  gas class                         │  risk level
           │                                   │
           └──────────────┬────────────────────┘
                          │
                          ▼
             ┌────────────────────────┐
        
        
            │                        │
             │     KNOWLEDGE BASE      │
             │                        │
             │  Gas Type              │
             │     → Source Device    │
             │     → Health Risks     │
             │     → Actions to Take  │
             │                        │
             └────────────┬───────────┘
                          │
                          │  full alert object ready
                          │
                          ▼
             ┌────────────────────────┐
             │                        │
             │     ALERT GENERATED    │
             │                        │
             └────────┬───────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
┌──────────────────┐   ┌──────────────────────┐
│                  │   │                      │
│  HARDWARE ALERT  │   │   WEB DASHBOARD      │
│                  │   │                      │
│  RED LED ON      │   │  Live gas readings   │
│  BUZZER BEEPS    │   │  Hazard alert card   │
│  LCD displays:   │   │  Source device       │
│  "MERCURY - RED" │   │  Health risks        │
│                  │   │  Actions to take     │
│                  │   │  Historical data     │
│                  │   │  ML model accuracy   │
└──────────────────┘   └──────────────────────┘
```

---

## How to Draw This by Hand

Draw **9 boxes** connected by **arrows going downward**.

| Step | Box Label | What It Does |
|------|-----------|--------------|
| 1 | **E-Waste Items** | The source — CRT monitor, PCB, battery, etc. |
| 2 | **Gas Sensors ×5** | Detect the toxic gas in the air |
| 3 | **ESP32 (MCU)** | Reads sensor voltage, converts to ppm |
| 4 | **MQTT Broker** | Carries the data from device to server via WiFi |
| 5 | **Backend (FastAPI)** | The brain — splits into two checks |
| 6a | **ML Model** | Identifies *which gas* it is |
| 6b | **WHO Threshold** | Checks *how dangerous* it is |
| 7 | **Knowledge Base** | Links gas → device → health risk → action |
| 8 | **Alert** | Decision point — Green / Yellow / Red |
| 9a | **Hardware Alert** | LED + Buzzer on the physical device |
| 9b | **Web Dashboard** | Shows everything on screen |

---

## Simple One-Line Explanation for Supervisor

> *"The sensors detect gas → ESP32 reads the values → sent to cloud → ML model identifies gas type → compared against WHO safety limits → knowledge base finds source device and risks → alert sent to screen and hardware."*

---

## Key Decision Point (Important for Supervisor)

```
         Is gas level over WHO limit?
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
      GREEN       YELLOW      RED
      (Safe)    (Caution)   (Danger)
    No action   Monitor    Evacuate
                closely   immediately
```

---

## What Makes This System Different (Novel Contributions)

| Normal Gas Detector | This System |
|--------------------|-------------|
| Detects gas — done | Detects + **classifies** gas type |
| Shows ppm number | Compares against **WHO safety limits** |
| No source info | Tells you **which device caused it** |
| No action guide | Gives **step-by-step actions** |
| No history | **Stores all readings** for trend analysis |
