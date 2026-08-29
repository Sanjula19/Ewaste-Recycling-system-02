# E-Waste Toxic Gas Detection System

> **Final Year Research Project** | Year 4, Semester 2  
> **Domain:** IoT · Machine Learning · Environmental Health & Safety  
> **Research Component Owner:** Sanjula Madushanka

---

## 🎯 Overview

A real-time toxic gas detection and classification system for e-waste processing environments. Detects CO, Mercury Vapor, Benzene, Ammonia, H₂S, and LPG using a multi-sensor IoT array, classifies gas types using Machine Learning (Random Forest), identifies the source e-waste device via a knowledge base, and alerts operators through hardware indicators and a web dashboard.

---

## 🏗️ System Architecture

See the [`architecture/`](./architecture/) folder for the complete 15-document architecture specification.

---

## 📁 Project Structure

```
├── architecture/     ← System architecture documents (START HERE)
├── hardware/         ← ESP32 firmware and circuit schematics
├── ml/               ← Machine learning pipeline (datasets, notebooks, models)
├── backend/          ← FastAPI Python backend
├── frontend/         ← React.js dashboard
├── docs/             ← Research paper, presentations, validation
└── data/             ← Shared data assets
```

---

## 🚀 Quick Start

See [`architecture/15_build_roadmap.md`](./architecture/15_build_roadmap.md) for the week-by-week build plan.

---

## 🔧 Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Hardware | ESP32 + MQ-2/7/135/303/136 + DHT22 |
| Firmware | Arduino C++ + PubSubClient MQTT |
| ML | Python + Scikit-learn (Random Forest) |
| Backend | FastAPI + PostgreSQL + Firebase |
| Frontend | React.js + Recharts + Firebase RT DB |
| Deployment | Render + Vercel + Supabase + HiveMQ |

---

## 💰 Total Cost

- **Hardware:** ~$34 (one-time)
- **Software/Cloud:** $0 (all free tiers)

---

## ⚠️ Security

Never commit `.env` files or Firebase service account keys. Use `.env.example` as template.
