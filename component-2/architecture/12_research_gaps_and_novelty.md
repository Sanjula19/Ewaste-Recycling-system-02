# 12 — Research Gaps and Novel Contributions

## 12.1 Literature Review Gaps (Academic Framing)

The following gaps are identified from a review of existing literature on e-waste monitoring and gas detection systems:

---

### Gap 1: Absence of E-Waste-Specific Gas Classification Systems

**Existing Work:**
Most gas detection research focuses on general industrial environments (mines, factories, food processing) or smart home applications. Studies by [Zampolli et al.] and [Röck et al.] demonstrate gas sensor arrays for general industrial settings but do not address the specific multi-gas profile of e-waste environments.

**Gap:**
No published system specifically targets the combination of gases emitted during e-waste dismantling (CO, Mercury Vapor, Benzene, Ammonia, H₂S, LPG) with ML classification.

**How This Research Addresses It:**
This system is purpose-built for the e-waste context, with a dataset calibrated for e-waste gas profiles and a knowledge base mapping gases to source e-waste components.

---

### Gap 2: Lack of Source Attribution (Gas → Device)

**Existing Work:**
Existing IoT gas detectors (commercial products: MQ sensor kits, PID detectors) report concentration values only. They do not identify *which device* caused the gas emission.

**Gap:**
No research provides an automated attribution chain from detected gas → source e-waste device → device-specific hazard profile → appropriate action plan.

**How This Research Addresses It:**
The Gas-Device-Hazard knowledge base is a **novel contribution** that provides this attribution, enabling targeted intervention rather than generic evacuation.

---

### Gap 3: Reactive Rather Than Real-Time Intelligent Monitoring

**Existing Work:**
Most e-waste facility monitoring is either manual (periodic air sampling sent to labs) or uses simple threshold alarms (single-point analog detectors without intelligence).

**Gap:**
No end-to-end system combines real-time sensor streaming + ML classification + WHO threshold comparison + automated alert generation within a single integrated platform.

**How This Research Addresses It:**
This system provides end-to-end real-time intelligence: sensor → MQTT → ML inference → knowledge base → WHO comparison → alert → dashboard, with a measured end-to-end latency target of <2 seconds.

---

### Gap 4: No WHO/NIOSH Threshold Integration in Real-Time Systems

**Existing Work:**
Safety threshold data (WHO, NIOSH, OSHA) is available in reference documents but is not systematically integrated into automated real-time monitoring systems in the e-waste domain.

**Gap:**
No system automatically compares live gas readings against the correct WHO/NIOSH standard for that specific gas in real time, providing a percentage-over-limit calculation and risk level.

**How This Research Addresses It:**
The WHO Threshold Comparison Engine automatically maps each gas class to its correct standard, computes the exceeded-by percentage, and assigns GREEN/YELLOW/RED risk levels.

---

### Gap 5: No Historical Data Collection for E-Waste Gas Exposure Trends

**Existing Work:**
Point-in-time gas measurements exist in occupational health literature, but these are expensive lab-based analyses, not continuous monitoring with historical storage.

**Gap:**
No affordable, continuous-monitoring platform exists that stores historical gas readings from e-waste facilities for trend analysis and reporting.

**How This Research Addresses It:**
PostgreSQL storage with full time-series data enables historical trend analysis, daily summaries, and exportable reports for occupational health documentation.

---

### Gap 6: No Comparative ML Study for E-Waste Gas Classification

**Existing Work:**
ML for gas classification exists in other domains (Vergara et al., 2012; Fonollosa et al., 2015) but not specifically for e-waste gas profiles.

**Gap:**
No study compares multiple ML algorithms (RF vs SVM vs DT vs NB) specifically for e-waste gas sensor array data.

**How This Research Addresses It:**
This study conducts a systematic comparative evaluation of four ML algorithms on e-waste gas data, providing empirical evidence for algorithm selection in this domain.

---

## 12.2 Novel Contributions Summary Table

| # | Contribution | Academic Novelty |
|---|-------------|-----------------|
| NC1 | Multi-sensor gas array calibrated for e-waste gas profiles | Domain-specific hardware configuration |
| NC2 | Gas-Device-Hazard knowledge base (gas → source device → health risk) | First automated attribution chain in e-waste monitoring |
| NC3 | WHO/NIOSH real-time threshold comparison engine | Integration of regulatory standards into live monitoring |
| NC4 | Comparative ML study: RF vs SVM vs DT vs NB on e-waste gas data | First such comparison in this specific domain |
| NC5 | Self-collected dataset from simulated e-waste lab environment | Novel dataset contribution |
| NC6 | Integrated IoT + ML + Knowledge Base + Dashboard platform | End-to-end system integration novelty |

---

## 12.3 Research Questions (Formal)

Based on the identified gaps, this research addresses the following questions:

| RQ | Research Question |
|----|-----------------|
| RQ1 | Can a multi-sensor MQ sensor array accurately detect and distinguish the toxic gases commonly emitted during e-waste processing? |
| RQ2 | Which machine learning algorithm achieves the highest classification accuracy for identifying gas types from sensor array readings in the e-waste domain? |
| RQ3 | How effectively can a rule-based knowledge base attribute detected gases to their source e-waste devices and provide appropriate safety guidance? |
| RQ4 | What end-to-end system latency is achievable in a real-time IoT-ML integrated monitoring platform? |

---

## 12.4 Positioning in Related Work

```
                        FEATURE COMPARISON

                    This  | IoT Gas | Lab-based | Commercial
Feature             Work  | Kits    | Analysis  | Detectors
─────────────────────────────────────────────────────────────
Real-time detection   ✅  |   ✅    |    ❌     |    ✅
ML gas classification ✅  |   ❌    |    ❌     |    ❌
Source attribution    ✅  |   ❌    |    ❌     |    ❌
WHO threshold compare ✅  |   ❌    |    ✅     |    Partial
Historical storage    ✅  |   ❌    |    ✅     |    Limited
Web dashboard         ✅  |   ❌    |    ❌     |    Limited
E-waste specific      ✅  |   ❌    |    ✅     |    ❌
Affordable (<$35)     ✅  |   ✅    |    ❌     |    ❌
─────────────────────────────────────────────────────────────
```

> This table should be included in the Related Work section of your research paper to clearly position your contribution.
