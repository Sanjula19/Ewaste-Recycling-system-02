# Component 1 - AI Waste Assessment

## Overview

Component 1 is responsible for AI-based waste assessment and IoT data acquisition.

It receives:

- Image from ESP32-CAM
- Weight from Load Cell -> HX711 -> Arduino UNO -> Raspberry Pi
- Waste mode: GENERAL or EWASTE

## System Flow

### General Waste

Image + Weight
-> Raspberry Pi
-> FastAPI
-> ResNet50 Waste Type Classification
-> ResNet50 Condition Classification
-> Grade A / B / C

Supported waste classes:

- Plastic
- Glass
- Metal
- Paper
- Cardboard

Condition classes:

- Clean
- Contaminated
- Damaged

Grade mapping:

- Clean -> A
- Contaminated -> B
- Damaged -> C

### E-Waste

Image + Weight
-> Raspberry Pi
-> FastAPI
-> YOLOv8n
-> E-Waste Type Detection
-> Hazard Knowledge Base
-> Hazard / PPE / Handling Guidance

Supported E-Waste classes:

- Smartphone
- Laptop
- Battery
- PCB

E-Waste YOLO test results:

- Precision: 88.1%
- Recall: 91.9%
- mAP@50: 94.0%
- mAP@50-95: 78.9%

Important:

YOLO identifies the e-waste device/component class only.
Hazard information is retrieved from the knowledge base.
It does not visually confirm chemical composition.

## API Endpoints

Health check:

GET /health

General waste:

POST /waste/predict

E-Waste:

POST /ewaste/analyze

Image requests use multipart/form-data with:

image = uploaded image

## IoT Architecture

Load Cell
-> HX711
-> Arduino UNO
-> USB Serial
-> Raspberry Pi

ESP32-CAM
-> Wi-Fi
-> Raspberry Pi

Raspberry Pi
-> FastAPI AI Backend

## Integration Flow

The intended integrated system flow is:

IoT
-> Component 1
-> Component 2
-> Component 4

Component 3 operates independently.

Component 1 provides the waste assessment.

Component 2 consumes relevant Component 1 outputs such as:

- waste/material category
- weight
- condition
- grade
- hazard level where applicable

Component 4 receives the assessment and process-optimization results for monitoring and analytics.

## Folder Structure

component_1/
├── backend/
│   ├── app.py
│   ├── knowledge_base/
│   │   └── ewaste_hazards.json
│   ├── models/
│   │   └── ewaste_yolov8n_best.pt
│   └── requirements.txt
│
├── raspberry_pi/
│   ├── weight_camera.py
│   ├── dashboard.py
│   └── requirements.txt
│
└── README.md

## Model Files

The YOLOv8 e-waste model is included.

The following large TensorFlow model files are NOT stored in this Git repository:

- resnet50_waste_type_final.keras
- resnet50_condition_final.keras

Before running the backend, place them inside:

component_1/backend/models/

## Run Backend

Install dependencies:

pip install -r component_1/backend/requirements.txt

Run:

cd component_1/backend

uvicorn app:app --host 0.0.0.0 --port 8000

## Raspberry Pi

Install dependencies:

pip install -r component_1/raspberry_pi/requirements.txt

Run:

python component_1/raspberry_pi/weight_camera.py

Note:

The Raspberry Pi camera/backend IP addresses depend on the local network and may need to be updated before running.
