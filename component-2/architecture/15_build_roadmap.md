# 15 — Build Roadmap

## 15.1 Project Timeline Overview

```
WEEK 1       WEEK 2       WEEK 3       WEEK 4       WEEK 5
Foundation   ML Pipeline  Hardware +   Frontend +   Polish +
& Theory     (Offline)    Backend      Integration  Validation
    ●────────────●────────────●────────────●────────────●
   Start                                            Complete
```

---

## 15.2 Week-by-Week Build Plan

### WEEK 1 — Foundation & Theory

| Day | Tasks | Output |
|-----|-------|--------|
| 1 | Download all 4 datasets (D1–D4) | Datasets in `ml/datasets/raw/` |
| 1 | Setup Python environment + Jupyter | Working Jupyter environment |
| 2 | Write Theoretical Framework section | Research paper Section 2 draft |
| 3 | Write Research Methodology section | Research paper Section 3 draft |
| 4 | Create project folder structure | All folders from `02_folder_structure.md` |
| 4 | Setup GitHub repository | Public repo with README |
| 5 | Explore datasets (01_data_exploration.ipynb) | EDA notebook complete |
| 5 | Review architecture documents | Understanding of full system |

**Week 1 Deliverables:**
- [ ] All datasets downloaded and organized
- [ ] Python environment setup
- [ ] GitHub repo created with folder structure
- [ ] Theory + Methodology sections drafted
- [ ] Data exploration notebook complete

---

### WEEK 2 — ML Pipeline (Offline)

| Day | Tasks | Output |
|-----|-------|--------|
| 6 | Preprocess UCI dataset (02_preprocessing.ipynb) | Cleaned, normalized dataset |
| 7 | Feature engineering (03_feature_engineering.ipynb) | Final feature set |
| 8 | Train Random Forest (04_model_training.ipynb) | `random_forest_v1.pkl` |
| 8 | Train SVM, Decision Tree, Naive Bayes | All 4 `.pkl` files |
| 9 | Evaluate all models (05_model_evaluation.ipynb) | Comparison table + charts |
| 9 | Hyperparameter tuning RF (06_hyperparameter_tuning.ipynb) | Optimized RF |
| 10 | Export models (07_model_export.ipynb) | Final model files ready |
| 10 | Create model comparison visualizations | Charts for research paper |

**Week 2 Deliverables:**
- [ ] All 4 models trained and evaluated
- [ ] Model comparison table filled
- [ ] Confusion matrices generated
- [ ] Best model (RF) exported to `.pkl`
- [ ] Results section started

---

### WEEK 3 — Hardware + Backend

| Day | Tasks | Output |
|-----|-------|--------|
| 11 | Buy hardware (if not already done) | ESP32 + all sensors |
| 11 | Wire sensors to ESP32 (use pinout from Doc 04) | Working breadboard |
| 12 | Flash calibration sketches; test each sensor | Sensor reads stable values |
| 12 | Setup HiveMQ Cloud account; get credentials | MQTT broker ready |
| 13 | Build firmware (`hardware/firmware/main/`) | ESP32 publishes JSON |
| 13 | Verify MQTT messages in HiveMQ console | Messages arriving |
| 14 | Build FastAPI backend skeleton | `backend/` structure complete |
| 14 | Implement MQTT subscriber service | Backend receives sensor data |
| 15 | Implement ML inference service (load .pkl) | `/predict/classify` working |
| 15 | Implement knowledge base service | Device/hazard lookup working |
| 15 | Implement WHO threshold service | Risk level assignment working |
| 15 | Test end-to-end: ESP32 → MQTT → API → ML | Data flows correctly |

**Week 3 Deliverables:**
- [ ] ESP32 wired and publishing data
- [ ] Backend receives and processes MQTT messages
- [ ] ML inference returns correct gas class
- [ ] Knowledge base lookup works
- [ ] WHO thresholds correctly compared

---

### WEEK 4 — Frontend + Integration + Validation

| Day | Tasks | Output |
|-----|-------|--------|
| 16 | Setup React project + routing | 4-page shell |
| 16 | Setup Firebase project; write backend service | Live data flowing |
| 17 | Build Page 1: Live Monitor with charts | Working live dashboard |
| 17 | Connect Firebase SDK to React | Real-time updates working |
| 18 | Build Page 2: Hazard Alert with action cards | Alert display working |
| 18 | Build Page 3: Historical Data + export | CSV download working |
| 19 | Build Page 4: ML Performance charts | Model comparison displayed |
| 19 | Deploy backend to Render.com | Live API URL |
| 19 | Deploy frontend to Vercel | Live dashboard URL |
| 20 | Collect self-collected dataset (D5) | 200+ lab samples |
| 20 | Run validation test cases (from Doc 14) | Validation results |
| 20 | Fill in validation results table | Validation section complete |

**Week 4 Deliverables:**
- [ ] Complete 4-page dashboard
- [ ] System deployed to cloud
- [ ] Self-collected dataset complete
- [ ] All test cases executed and documented
- [ ] Validation results recorded

---

### WEEK 5 — Polish, Write-Up, Submission

| Day | Tasks | Output |
|-----|-------|--------|
| 21 | Write Results section (ML metrics, system performance) | Paper Section 4 |
| 21 | Write Discussion section (gap analysis, limitations) | Paper Section 5 |
| 22 | Write Conclusion + Future Work | Paper Section 6 |
| 22 | Complete References/Bibliography (BibTeX) | Full reference list |
| 23 | Create diagrams: Use case, Sequence, ER | `docs/diagrams/` |
| 23 | Prepare final presentation slides | `docs/presentations/` |
| 24 | Record demo video (hardware → dashboard) | Demo video file |
| 24 | Final paper review + formatting | Formatted paper |
| 25 | Final submission | Submitted ✅ |

---

## 15.3 Build Order Dependency Graph

```
[Datasets Downloaded]
        │
        ▼
[ML Notebooks] ──────► [.pkl Models saved]
                                │
                                ▼
[ESP32 Wired] ──► [Firmware Built] ──► [MQTT Messages]
                                              │
                                              ▼
                              [FastAPI Backend] ◄── [.pkl Models]
                                │         │
                         [Firebase]   [PostgreSQL]
                                │
                                ▼
                          [React Dashboard]
                                │
                                ▼
                    [System Validation Testing]
                                │
                                ▼
                    [Research Paper Write-Up]
```

---

## 15.4 What NOT to Build (Keep Scope Tight)

For your final-year project, **avoid scope creep**. These are explicitly OUT of scope:

| Feature | Why Skip |
|---------|----------|
| Mobile app | Adds weeks; web dashboard is sufficient |
| Multi-node sensor network | Complex; single node is enough for research |
| Gas concentration regression | Classification is enough; regression needs calibrated gas sources |
| User authentication | Not needed for single-lab demo system |
| Email/SMS notifications | MQTT hardware alert is sufficient |
| Neo4j knowledge graph | JSON files are simpler and sufficient |

---

## 15.5 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Hardware delayed shipping | Medium | High | Order early Week 1; simulate with pre-recorded data |
| Sensors give noisy readings | High | Medium | Add moving average filter in firmware |
| ML accuracy < 90% | Medium | High | Use SMOTE; tune hyperparameters; collect more data |
| Render.com API sleeps | High | Low | UptimeRobot ping every 14min |
| HiveMQ free tier limit | Low | Medium | Reduce publish frequency to every 10 sec |
| Dataset unavailable | Low | High | Keep backup mirrors; use only D2+D5 if D1 fails |

---

## 15.6 Definition of Done (Final Checklist)

### Hardware Layer
- [ ] All 5 sensors wired and reading stable values
- [ ] DHT22 reading temperature and humidity
- [ ] LCD displaying gas type and risk level
- [ ] LEDs and buzzer responding to risk level
- [ ] MQTT messages publishing every 5 seconds

### ML Layer
- [ ] All 4 models trained and evaluated
- [ ] Model comparison table complete with accuracy, F1, precision, recall
- [ ] Confusion matrices generated
- [ ] Feature importance chart created
- [ ] Best model saved as `.pkl` and loaded by backend

### Backend Layer
- [ ] All API endpoints documented and tested
- [ ] MQTT subscriber receiving messages reliably
- [ ] ML inference returning correct results
- [ ] Knowledge base lookup returning device + health risks + actions
- [ ] WHO threshold comparison working correctly
- [ ] Alerts stored in PostgreSQL
- [ ] Live data pushed to Firebase

### Frontend Layer
- [ ] Page 1: Live gas readings updating every 5 sec
- [ ] Page 2: Active hazard alert with full detail
- [ ] Page 3: Historical data with CSV export
- [ ] Page 4: ML model comparison charts
- [ ] Dashboard deployed on Vercel

### Validation
- [ ] All test cases from Doc 14 executed
- [ ] Validation results table complete
- [ ] End-to-end latency measured and documented
- [ ] Self-collected dataset (200+ samples) complete

### Research Paper
- [ ] Abstract complete
- [ ] Introduction complete with problem statement
- [ ] Literature review complete with gap analysis
- [ ] Research methodology complete
- [ ] Results section complete with all tables and figures
- [ ] Discussion complete
- [ ] Conclusion and future work complete
- [ ] All references cited in proper format
