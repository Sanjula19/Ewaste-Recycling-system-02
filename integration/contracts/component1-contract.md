# Component 1 Contract — AI Waste Assessment (Shehan)

**Status: CONFIRMED REAL** — extracted directly from
`component-1/component_1/backend/app.py`.

Base URL (local): `http://localhost:8001`

---

## GET /health

No parameters.

**Response (200):**
```json
{
  "status": "ok",
  "service": "waste-assessment-service",
  "version": "1.2",
  "general_waste": "ready",
  "ewaste": "ready"
}
```

---

## POST /waste/predict

General waste classification (ResNet50 models).

**Request:** `multipart/form-data`
| Field | Type | Required |
|---|---|---|
| `image` | file (UploadFile) | yes |

**Response (200):**
```json
{
  "waste_type": "Plastic",
  "waste_confidence": 0.9123,
  "condition": "Clean",
  "condition_confidence": 0.8877,
  "final_grade": "A",
  "preprocessing": {
    "waste_type": "center_roi",
    "condition": "full_image"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `waste_type` | string | One of: `Plastic`, `Glass`, `Metal`, `Paper`, `Cardboard` |
| `waste_confidence` | float | Softmax confidence for `waste_type`, rounded to 4dp |
| `condition` | string | One of: `Clean`, `Contaminated`, `Damaged` |
| `condition_confidence` | float | Softmax confidence for `condition`, rounded to 4dp |
| `final_grade` | string | Derived from `condition`: Clean→`A`, Contaminated→`B`, Damaged→`C`, else `Unknown` |
| `preprocessing` | object | Describes which crop was fed to each model — informational only |

**Response (400):** `{"error": "Empty image file"}`
**Response (500):** `{"error": "<exception message>"}`

**Fields that do NOT exist in this response:** `material_name`, `weight_kg`, `weight_g`, `moisture_condition`. Component 1 never returns a weight value in its API — weight is only read from the physical load cell on the Raspberry Pi (separate hardware path, not part of this HTTP response).

---

## POST /ewaste/analyze

E-waste device detection (YOLOv8n) + hazard knowledge-base lookup.

**Request:** `multipart/form-data`
| Field | Type | Required |
|---|---|---|
| `image` | file (UploadFile) | yes |

**Response (200) — detection found:**
```json
{
  "detected": true,
  "confidence_threshold": 0.5,
  "primary_detection": {
    "class_id": 2,
    "detected_type": "Circuit Board",
    "confidence": 0.8765,
    "bbox": {"x1": 10.2, "y1": 5.1, "x2": 200.4, "y2": 150.7},
    "screening_hazard_level": "HIGH",
    "possible_components": ["..."],
    "possible_hazards": ["..."],
    "recommended_ppe": ["..."],
    "handling_instructions": ["..."],
    "escalation_rule": "...",
    "certainty_note": "..."
  },
  "detections": ["... array of the same shape, sorted by confidence desc ..."],
  "model_scope": "YOLO detects the e-waste device or component class. Hazard information is retrieved from the knowledge base and is not a visual confirmation of chemical composition."
}
```

**Response (200) — no detection above threshold:**
```json
{
  "detected": false,
  "message": "No supported e-waste object detected above the confidence threshold.",
  "confidence_threshold": 0.5,
  "detections": []
}
```

**Response (400/500):** same error shape as `/waste/predict`.

**Fields that do NOT exist:** `material_name`, `waste_type`, `weight_kg`/`weight_g`, `moisture_condition`, `grade` (the e-waste path has no `final_grade` field — grading only happens on the general-waste path).

---

## Summary of usable output fields for downstream integration

| Path | Fields available for mapping downstream |
|---|---|
| `/waste/predict` | `waste_type`, `condition`, `final_grade`, confidences |
| `/ewaste/analyze` | `primary_detection.detected_type`, `screening_hazard_level`, `possible_hazards`, confidence |

No weight and no moisture data is available from Component 1 under any endpoint.
