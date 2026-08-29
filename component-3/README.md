# Ewaste-Recycling-system-02

<h1 align="center">
♻️ AI-Powered Automated Waste Segregation & E-Waste Recycling System
</h1>

<p align="center">
<img src="https://img.shields.io/badge/AI-Waste%20Management-green"/>
<img src="https://img.shields.io/badge/YOLOv8-Detection-blue"/>
<img src="https://img.shields.io/badge/FastAPI-Backend-teal"/>
<img src="https://img.shields.io/badge/React-Frontend-61DAFB"/>
<img src="https://img.shields.io/badge/Status-Research-orange"/>
</p>

<p align="center">
🌍 Transforming Waste into Value using AI & Smart Recycling
</p>

---

## 🎯 Project Overview

This research project introduces an **AI-powered intelligent waste segregation and e-waste recycling system** that improves traditional recycling by:

✅ Detecting waste contamination  
✅ Identifying hazardous materials  
✅ Optimizing recycling processes  
✅ Predicting economic value of recovered materials  

The system supports a **Zero-Waste Circular Economy** model.

---

## 🎥 System Demo

<p align="center">
<img src="docs/demo.gif" width="700"/>
</p>

---

# 🧠 System Architecture

This project consists of **4 Intelligent Components**

---

## 🔍 Component 01 — Smart Contamination Detection
- CNN + GLCM Texture Analysis
- Detects grease, rust, mud
- Assigns quality grade (A, B, C)

Output:
Grade A → Clean
Grade B → Wash Required
Grade C → Energy Recovery


---

## ⚠️ Component 02 — Hazard & Material Identification
- YOLOv8 device detection
- Material knowledge mapping
- Hazard explanation system
- PPE recommendations

Example:
Device: Smartphone
Hazard: Lithium Battery
Risk: Thermal Runaway


---

## ⚙️ Component 03 — Smart Process Optimization
- Moisture-based adaptive recycling
- Plastic drying recommendations
- Organic waste decomposition logic
- C:N ratio calculation

---

## 📈 Component 04 — Predictive Economic Valuation
- ARIMA Forecasting Model
- Metal price prediction (Gold, Copper, Lithium)
- Sell / Hold recommendation
- Zero landfill strategy

---

# 🛠️ Technology Stack

### Frontend
- React.js
- Tailwind CSS
- Recharts

### Backend
- FastAPI (Python)
- Microservices Architecture

### AI Models
- YOLOv8
- ResNet50
- ARIMA
- Decision Trees

### Database
- PostgreSQL
- Neo4j Graph DB

---

# 📊 Datasets Used

| Category | Dataset |
|----------|---------|
| Waste Images | TrashNet |
| Waste Images | TACO |
| Waste Images | RealWaste |
| E-Waste | Custom Dataset |
| Materials | iFixit |
| Safety Data | PubChem |
| Economic Data | Kaggle Metals |
| Forecast Data | World Bank |

---

# 🚀 Installation

### Clone Repository

git clone https://github.com/your-username/AI-Waste-System.git
cd AI-Waste-System

📂 Project Structure

AI-Waste-System
│
├── frontend
├── backend
├── datasets
├── models
├── docs
└── README.md


