# 🏗️ System Architecture — E-Waste Toxic Gas Detection System

> **Research Component Owner:** Sanjula Madushanka  
> **Academic Level:** Final Year Undergraduate Research (Y4S2)  
> **Domain:** IoT · Machine Learning · Environmental Health & Safety  
> **Version:** 2.0 — Complete Architecture (2026)

---

## 📂 Architecture Document Index

| # | Document | Description |
|---|----------|-------------|
| 01 | [`01_system_overview.md`](./01_system_overview.md) | High-level system overview, research gaps, objectives |
| 02 | [`02_folder_structure.md`](./02_folder_structure.md) | Complete project folder and file structure |
| 03 | [`03_data_flow_architecture.md`](./03_data_flow_architecture.md) | End-to-end data flow: Sensor → ML → Dashboard |
| 04 | [`04_hardware_architecture.md`](./04_hardware_architecture.md) | Hardware layer: ESP32, sensors, wiring, pinout |
| 05 | [`05_communication_architecture.md`](./05_communication_architecture.md) | MQTT, REST API, WebSocket communication design |
| 06 | [`06_ml_pipeline_architecture.md`](./06_ml_pipeline_architecture.md) | ML pipeline: Data → Preprocessing → Training → Inference |
| 07 | [`07_backend_architecture.md`](./07_backend_architecture.md) | FastAPI backend: endpoints, services, middleware |
| 08 | [`08_database_architecture.md`](./08_database_architecture.md) | Firebase + PostgreSQL schema design |
| 09 | [`09_frontend_architecture.md`](./09_frontend_architecture.md) | React.js dashboard: pages, components, state |
| 10 | [`10_knowledge_base_architecture.md`](./10_knowledge_base_architecture.md) | Gas–Device–Hazard knowledge base design |
| 11 | [`11_deployment_architecture.md`](./11_deployment_architecture.md) | Cloud deployment: Render, Vercel, Firebase |
| 12 | [`12_research_gaps_and_novelty.md`](./12_research_gaps_and_novelty.md) | Research gap analysis and novel contributions |
| 13 | [`13_technology_stack.md`](./13_technology_stack.md) | Full technology stack with justifications |
| 14 | [`14_datasets_and_validation.md`](./14_datasets_and_validation.md) | Datasets, training strategy, validation plan |
| 15 | [`15_build_roadmap.md`](./15_build_roadmap.md) | Week-by-week build order and milestones |

---

## 🎯 Research Objective (Summary)

Design and implement a **real-time e-waste toxic gas detection and classification system** that:

1. **Detects** toxic gases emitted during e-waste processing (CO, Mercury Vapor, Benzene, Ammonia, H₂S, LPG)
2. **Classifies** gas types using a trained Machine Learning model (Random Forest + comparison baseline)
3. **Identifies** likely source e-waste device using a knowledge base
4. **Assesses** health risk by comparing against WHO/NIOSH safety thresholds
5. **Alerts** operators in real-time via hardware (LED/Buzzer) and digital dashboard (React.js)
6. **Stores** historical data for trend analysis and reporting

---

## ⚠️ Key Research Gaps Addressed

| Gap | How This System Addresses It |
|-----|------------------------------|
| No e-waste specific ML dataset | Custom dataset collection + augmentation from UCI |
| Reactive rather than predictive monitoring | Real-time ML inference on live sensor streams |
| No source attribution | Knowledge base maps gas signature → e-waste device |
| No WHO threshold integration | Automated ppm comparison against WHO/NIOSH limits |
| Siloed monitoring (no history) | PostgreSQL stores full historical data |
| No multi-gas simultaneous detection | 5 MQ sensors covering 6 target gases |

---

*Start reading from `01_system_overview.md` for the full picture.*
