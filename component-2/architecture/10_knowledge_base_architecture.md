# 10 — Knowledge Base Architecture

## 10.1 Overview

The Knowledge Base is one of the **key novel contributions** of this research. It links:

```
Detected Gas Class
      │
      ▼
Source E-Waste Device  ←── (first system to provide this attribution)
      │
      ▼
Health Hazards (specific to that device context)
      │
      ▼
Recommended Safety Actions (WHO/NIOSH aligned)
```

This attribution chain is what differentiates this system from simple gas detectors.

---

## 10.2 Knowledge Base File Structure

```
backend/knowledge_base/
├── gas_profiles.json        ← Sensor-to-gas characteristics
├── device_hazards.json      ← Gas → Device → Hazard → Action
├── who_thresholds.json      ← WHO/NIOSH/OSHA safety limits
└── action_plans.json        ← Standardized emergency protocols
```

---

## 10.3 Gas-Device-Hazard Mapping Table

| Gas Detected | Source E-Waste Device | Primary Health Risk | NIOSH Limit |
|-------------|----------------------|---------------------|-------------|
| **CO** | PCBs (burning), Soldering | Asphyxiation, death | 35 ppm TWA |
| **LPG/Methane** | Capacitors, Battery packs | Fire/Explosion, asphyxiation | LEL-based |
| **Benzene** | Plastic housings, Cable insulation | Leukemia (carcinogen) | 0.1 ppm |
| **Ammonia** | NiCd/NiMH batteries | Respiratory burns | 25 ppm |
| **Mercury Vapor** | CRT monitors, Fluorescent lamps | Brain/Kidney damage | 0.05 mg/m³ |
| **H₂S** | Li-ion batteries, Solder | Rapid unconsciousness, death | 1 ppm ceiling |

---

## 10.4 `who_thresholds.json` Schema

```json
{
  "version": "1.0",
  "last_updated": "2026-01-01",
  "sources": [
    "WHO Air Quality Guidelines 2021",
    "NIOSH Pocket Guide to Chemical Hazards",
    "OSHA PEL Tables",
    "ACGIH TLV® Documentation"
  ],
  "thresholds": {
    "CO": {
      "gas_name": "Carbon Monoxide",
      "formula": "CO",
      "sensor": "mq7",
      "limits": {
        "who_1hr":      {"value": 25.0,  "unit": "ppm"},
        "niosh_twa":    {"value": 35.0,  "unit": "ppm", "period": "10hr"},
        "osha_pel":     {"value": 50.0,  "unit": "ppm", "period": "8hr"},
        "niosh_idlh":   {"value": 1200.0,"unit": "ppm"},
        "system_green": {"value": 12.5,  "unit": "ppm"},
        "system_yellow":{"value": 25.0,  "unit": "ppm"},
        "system_red":   {"value": 35.0,  "unit": "ppm"}
      }
    },
    "MERCURY": {
      "gas_name": "Mercury Vapor",
      "formula": "Hg",
      "sensor": "mq303",
      "limits": {
        "who_annual":   {"value": 0.001, "unit": "mg/m3"},
        "who_acute":    {"value": 0.025, "unit": "mg/m3", "period": "1hr"},
        "niosh_rel":    {"value": 0.05,  "unit": "mg/m3", "period": "10hr"},
        "osha_ceiling": {"value": 0.1,   "unit": "mg/m3"},
        "niosh_idlh":   {"value": 10.0,  "unit": "mg/m3"},
        "system_green": {"value": 0.0125,"unit": "mg/m3"},
        "system_yellow":{"value": 0.025, "unit": "mg/m3"},
        "system_red":   {"value": 0.05,  "unit": "mg/m3"}
      }
    },
    "H2S": {
      "gas_name": "Hydrogen Sulphide",
      "formula": "H2S",
      "sensor": "mq136",
      "limits": {
        "niosh_ceiling": {"value": 1.0,   "unit": "ppm", "period": "10min"},
        "osha_pel":      {"value": 20.0,  "unit": "ppm"},
        "acgih_tlv":     {"value": 1.0,   "unit": "ppm"},
        "niosh_idlh":    {"value": 100.0, "unit": "ppm"},
        "system_green":  {"value": 0.5,   "unit": "ppm"},
        "system_yellow": {"value": 1.0,   "unit": "ppm"},
        "system_red":    {"value": 5.0,   "unit": "ppm"}
      }
    },
    "BENZENE": {
      "gas_name": "Benzene",
      "formula": "C6H6",
      "sensor": "mq135",
      "limits": {
        "niosh_rel":    {"value": 0.1,   "unit": "ppm"},
        "osha_pel":     {"value": 1.0,   "unit": "ppm"},
        "acgih_tlv":    {"value": 0.5,   "unit": "ppm"},
        "niosh_idlh":   {"value": 500.0, "unit": "ppm"},
        "system_green": {"value": 0.25,  "unit": "ppm"},
        "system_yellow":{"value": 0.5,   "unit": "ppm"},
        "system_red":   {"value": 1.0,   "unit": "ppm"}
      }
    },
    "AMMONIA": {
      "gas_name": "Ammonia",
      "formula": "NH3",
      "sensor": "mq135",
      "limits": {
        "niosh_rel":    {"value": 25.0,  "unit": "ppm"},
        "osha_pel":     {"value": 50.0,  "unit": "ppm"},
        "acgih_tlv":    {"value": 25.0,  "unit": "ppm"},
        "niosh_idlh":   {"value": 300.0, "unit": "ppm"},
        "system_green": {"value": 12.5,  "unit": "ppm"},
        "system_yellow":{"value": 25.0,  "unit": "ppm"},
        "system_red":   {"value": 50.0,  "unit": "ppm"}
      }
    },
    "LPG": {
      "gas_name": "Liquefied Petroleum Gas",
      "formula": "C3H8/C4H10",
      "sensor": "mq2",
      "limits": {
        "lower_explosive_limit": {"value": 21000, "unit": "ppm"},
        "system_green":  {"value": 500,   "unit": "ppm"},
        "system_yellow": {"value": 1000,  "unit": "ppm"},
        "system_red":    {"value": 2100,  "unit": "ppm"}
      }
    }
  }
}
```

---

## 10.5 Knowledge Base Query Service

```python
# services/knowledge_base_service.py

import json
from pathlib import Path

class KnowledgeBaseService:
    def __init__(self):
        KB_DIR = Path("knowledge_base/")
        with open(KB_DIR / "device_hazards.json") as f:
            self.hazards = json.load(f)
        with open(KB_DIR / "who_thresholds.json") as f:
            self.thresholds = json.load(f)

    def get_device_hazard(self, gas_class: str) -> dict:
        """
        Given a gas class label, return:
          - source devices
          - health risks
          - recommended actions
        """
        gas_data = self.hazards["gas_to_device"].get(gas_class.upper())
        if not gas_data:
            return {
                "source_devices": ["Unknown"],
                "health_risks":   ["Monitor situation"],
                "actions":        ["Continue monitoring"]
            }
        return gas_data

    def get_threshold(self, gas_class: str) -> dict:
        """Return WHO/NIOSH threshold for a gas class."""
        return self.thresholds["thresholds"].get(gas_class.upper(), {})

    def get_risk_level(self, gas_class: str, reading_value: float) -> str:
        """Compare reading to threshold and return GREEN/YELLOW/RED."""
        threshold = self.get_threshold(gas_class)
        if not threshold:
            return "YELLOW"  # Unknown gas → caution

        limits = threshold["limits"]
        green  = limits.get("system_green",  {}).get("value", 0)
        yellow = limits.get("system_yellow", {}).get("value", 0)

        if reading_value < green:
            return "GREEN"
        elif reading_value < yellow:
            return "YELLOW"
        else:
            return "RED"
```

---

## 10.6 Academic Citation for Knowledge Base Sources

The knowledge base thresholds must be cited in your research paper:

| Source | What it provides |
|--------|-----------------|
| WHO Air Quality Guidelines (2021) | Mercury annual/acute limits, general air quality |
| NIOSH Pocket Guide to Chemical Hazards | IDLH, REL, ceiling values for all gases |
| OSHA Permissible Exposure Limits (PEL) | Regulatory 8-hour TWA limits |
| ACGIH Threshold Limit Values (TLV) | Industry-recommended exposure limits |
| Global E-Waste Monitor 2020 (Forti et al.) | E-waste gas hazard identification |
| ForensicsDetectors Gas Exposure Limit Tables | Consolidated reference for system calibration |
