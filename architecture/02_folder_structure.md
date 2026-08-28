# 02 — Complete Project Folder Structure

## 2.1 Root Directory Tree

```
EWaste-Toxic-Gas-Detection-System/
│
├── 📁 architecture/                        ← YOU ARE HERE
│   ├── 00_README.md
│   ├── 01_system_overview.md
│   ├── 02_folder_structure.md
│   ├── 03_data_flow_architecture.md
│   ├── 04_hardware_architecture.md
│   ├── 05_communication_architecture.md
│   ├── 06_ml_pipeline_architecture.md
│   ├── 07_backend_architecture.md
│   ├── 08_database_architecture.md
│   ├── 09_frontend_architecture.md
│   ├── 10_knowledge_base_architecture.md
│   ├── 11_deployment_architecture.md
│   ├── 12_research_gaps_and_novelty.md
│   ├── 13_technology_stack.md
│   ├── 14_datasets_and_validation.md
│   └── 15_build_roadmap.md
│
├── 📁 hardware/                            ← ESP32 Firmware
│   ├── firmware/
│   │   ├── main/
│   │   │   ├── main.ino                   ← Primary Arduino sketch
│   │   │   ├── sensor_reader.h            ← Sensor reading functions
│   │   │   ├── sensor_reader.cpp
│   │   │   ├── mqtt_handler.h             ← MQTT publish/subscribe
│   │   │   ├── mqtt_handler.cpp
│   │   │   ├── display_handler.h          ← LCD display functions
│   │   │   ├── display_handler.cpp
│   │   │   ├── alert_handler.h            ← LED + Buzzer control
│   │   │   ├── alert_handler.cpp
│   │   │   └── config.h                   ← WiFi, MQTT credentials
│   │   └── libraries.txt                  ← Required Arduino libraries
│   ├── calibration/
│   │   ├── mq2_calibration.ino            ← Individual sensor calibration
│   │   ├── mq7_calibration.ino
│   │   ├── mq135_calibration.ino
│   │   ├── mq303_calibration.ino
│   │   └── mq136_calibration.ino
│   ├── schematics/
│   │   ├── circuit_diagram.png            ← Full wiring diagram
│   │   ├── pinout_table.md                ← ESP32 pin assignments
│   │   └── pcb_layout.png                 ← Optional PCB layout
│   └── docs/
│       ├── sensor_datasheets/             ← PDF datasheets
│       └── hardware_setup_guide.md
│
├── 📁 ml/                                  ← Machine Learning Pipeline
│   ├── datasets/
│   │   ├── raw/
│   │   │   ├── uci_gas_sensor_drift/      ← UCI Gas Sensor Drift Dataset
│   │   │   │   └── (CSV files)
│   │   │   ├── mq_sensor_2023/            ← MQ Sensor Mendeley Dataset
│   │   │   │   └── (CSV files)
│   │   │   ├── uci_gas_concentration/     ← UCI Gas + Concentration
│   │   │   │   └── (CSV files)
│   │   │   └── who_limits.csv             ← WHO/NIOSH threshold table
│   │   ├── processed/
│   │   │   ├── combined_dataset.csv       ← Merged + cleaned dataset
│   │   │   ├── features_selected.csv      ← After feature selection
│   │   │   └── train_test_split/
│   │   │       ├── X_train.csv
│   │   │       ├── X_test.csv
│   │   │       ├── y_train.csv
│   │   │       └── y_test.csv
│   │   └── collected/
│   │       ├── lab_readings.csv           ← Your own collected data
│   │       └── collection_log.md          ← Data collection notes
│   │
│   ├── notebooks/
│   │   ├── 01_data_exploration.ipynb      ← EDA + visualizations
│   │   ├── 02_preprocessing.ipynb         ← Cleaning, normalization
│   │   ├── 03_feature_engineering.ipynb   ← Feature selection, PCA
│   │   ├── 04_model_training.ipynb        ← RF + SVM + DT + NB training
│   │   ├── 05_model_evaluation.ipynb      ← Accuracy, F1, confusion matrix
│   │   ├── 06_hyperparameter_tuning.ipynb ← GridSearchCV
│   │   └── 07_model_export.ipynb          ← Save .pkl model
│   │
│   ├── models/
│   │   ├── random_forest_v1.pkl           ← Trained RF model
│   │   ├── svm_v1.pkl                     ← Trained SVM model
│   │   ├── decision_tree_v1.pkl           ← Trained DT model
│   │   ├── naive_bayes_v1.pkl             ← Trained NB model
│   │   └── label_encoder.pkl              ← Label encoder for classes
│   │
│   ├── scripts/
│   │   ├── preprocess.py                  ← Preprocessing pipeline script
│   │   ├── train.py                       ← Training pipeline script
│   │   ├── evaluate.py                    ← Evaluation script
│   │   └── predict.py                     ← Single-sample inference
│   │
│   └── results/
│       ├── model_comparison_table.csv     ← Accuracy, F1, Precision, Recall
│       ├── confusion_matrices/
│       │   ├── rf_confusion.png
│       │   ├── svm_confusion.png
│       │   ├── dt_confusion.png
│       │   └── nb_confusion.png
│       └── feature_importance.png         ← RF feature importance chart
│
├── 📁 backend/                             ← FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        ← FastAPI app entry point
│   │   ├── config.py                      ← Environment config
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py              ← API v1 route aggregator
│   │   │   │   ├── gas_readings.py        ← GET/POST gas readings
│   │   │   │   ├── alerts.py              ← Alert CRUD endpoints
│   │   │   │   ├── predictions.py         ← ML inference endpoints
│   │   │   │   ├── reports.py             ← Historical + CSV export
│   │   │   │   └── health.py              ← Health check endpoint
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ml_service.py              ← ML model loader + inference
│   │   │   ├── mqtt_service.py            ← MQTT subscriber (async)
│   │   │   ├── knowledge_base_service.py  ← Gas → Device → Hazard lookup
│   │   │   ├── threshold_service.py       ← WHO/NIOSH comparison engine
│   │   │   ├── alert_service.py           ← Alert creation + notification
│   │   │   └── firebase_service.py        ← Firebase realtime DB writer
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── gas_reading.py             ← Pydantic schemas
│   │   │   ├── alert.py
│   │   │   ├── prediction.py
│   │   │   └── report.py
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py                ← SQLAlchemy engine + session
│   │   │   ├── migrations/                ← Alembic migration files
│   │   │   └── schemas/
│   │   │       ├── gas_readings_schema.sql
│   │   │       ├── alerts_schema.sql
│   │   │       └── reports_schema.sql
│   │   │
│   │   └── middleware/
│   │       ├── cors.py                    ← CORS config
│   │       ├── rate_limiter.py            ← Request rate limiting
│   │       └── auth.py                    ← API key authentication
│   │
│   ├── knowledge_base/
│   │   ├── gas_profiles.json              ← Gas → sensor response mapping
│   │   ├── device_hazards.json            ← Device → gas → health risk
│   │   ├── who_thresholds.json            ← WHO/NIOSH limits
│   │   └── action_plans.json              ← Emergency action plans
│   │
│   ├── ml_models/                         ← Symlink or copy from ml/models/
│   │   └── random_forest_v1.pkl
│   │
│   ├── tests/
│   │   ├── test_ml_service.py
│   │   ├── test_threshold_service.py
│   │   ├── test_knowledge_base.py
│   │   └── test_api_endpoints.py
│   │
│   ├── requirements.txt                   ← Python dependencies
│   ├── .env.example                       ← Environment variable template
│   ├── Dockerfile                         ← Docker containerization
│   └── README.md
│
├── 📁 frontend/                            ← React.js Dashboard
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── index.jsx                      ← React entry point
│   │   ├── App.jsx                        ← Root component + router
│   │   │
│   │   ├── pages/
│   │   │   ├── LiveMonitor.jsx            ← Page 1: Live gas readings
│   │   │   ├── HazardAlert.jsx            ← Page 2: Active alerts
│   │   │   ├── HistoricalData.jsx         ← Page 3: History + export
│   │   │   └── MLPerformance.jsx          ← Page 4: Model metrics
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Footer.jsx
│   │   │   ├── charts/
│   │   │   │   ├── GasLevelGauge.jsx      ← Real-time gauge chart
│   │   │   │   ├── TrendLineChart.jsx     ← 24h trend line
│   │   │   │   ├── ConfusionMatrix.jsx    ← ML confusion matrix viz
│   │   │   │   └── ModelCompareBar.jsx    ← Model comparison chart
│   │   │   ├── alerts/
│   │   │   │   ├── AlertCard.jsx          ← Individual alert card
│   │   │   │   ├── AlertBadge.jsx         ← G/Y/R status badge
│   │   │   │   └── AlertHistory.jsx       ← Alert list table
│   │   │   └── common/
│   │   │       ├── StatusIndicator.jsx    ← Online/Offline indicator
│   │   │       ├── LoadingSpinner.jsx
│   │   │       └── ExportButton.jsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useFirebase.js             ← Firebase live data hook
│   │   │   ├── useGasReadings.js          ← Polling gas readings
│   │   │   └── useAlerts.js               ← Alert subscription
│   │   │
│   │   ├── services/
│   │   │   ├── api.js                     ← Axios API client
│   │   │   └── firebase.js                ← Firebase SDK config
│   │   │
│   │   ├── store/                         ← State management (Context API)
│   │   │   ├── AppContext.jsx
│   │   │   └── reducers/
│   │   │       ├── gasReducer.js
│   │   │       └── alertReducer.js
│   │   │
│   │   └── styles/
│   │       ├── global.css
│   │       ├── theme.css                  ← Color tokens, typography
│   │       └── components.css
│   │
│   ├── package.json
│   ├── .env.example
│   └── README.md
│
├── 📁 docs/                                ← Research Documentation
│   ├── research_paper/
│   │   ├── draft_v1.docx                  ← Paper draft
│   │   └── references.bib                 ← BibTeX references
│   ├── presentations/
│   │   └── final_presentation.pptx
│   ├── validation/
│   │   ├── test_cases.md                  ← Test case definitions
│   │   └── validation_results.md          ← Test results
│   └── diagrams/
│       ├── use_case_diagram.png
│       ├── sequence_diagram.png
│       └── er_diagram.png
│
├── 📁 data/                                ← Shared data assets
│   ├── who_thresholds.csv
│   └── gas_sensor_specs.csv
│
├── .gitignore
├── README.md                               ← Project root README
└── CHANGELOG.md                           ← Version history
```

---

## 2.2 Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of Concerns** | Hardware / ML / Backend / Frontend are fully isolated modules |
| **Reproducibility** | All notebooks numbered and ordered; datasets versioned |
| **Scalability** | Backend uses service layer; can add new sensors/gases without restructuring |
| **Academic Integrity** | Datasets cited, notebooks documented, results reproducible |
| **Open Source** | All tools free-tier; no proprietary SDKs required |

---

## 2.3 File Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Python modules | snake_case | `ml_service.py` |
| React components | PascalCase | `LiveMonitor.jsx` |
| Notebooks | numbered prefix | `03_feature_engineering.ipynb` |
| Schema files | snake_case + `_schema` | `gas_readings_schema.sql` |
| Config files | lowercase | `config.py`, `.env` |
| Documentation | numbered prefix | `01_system_overview.md` |
