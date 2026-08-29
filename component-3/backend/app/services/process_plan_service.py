"""
Component 3 - Process Plan Service
Combine 3 models results - final process recipe JSON
CATEGORY_MAP loaded from training CSV — not hardcoded
"""

import json
import os
import pandas as pd
from datetime import datetime

_chemical_cache  = None
_category_map    = None
_toxicity_map    = None


def _load_chemical_map():
    global _chemical_cache
    if _chemical_cache:
        return _chemical_cache
    path = os.path.join(os.path.dirname(__file__), "..", "data", "chemical_agent_map.json")
    with open(path) as f:
        data = json.load(f)
    _chemical_cache = data["chemical_agents"]
    return _chemical_cache


def _load_category_map():
    """Load waste_type mapping directly from training CSV — no hardcoding"""
    global _category_map
    if _category_map:
        return _category_map
    # Try training CSV path
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "data", "component3_training_v2.csv"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml_training", "material_model", "dataset", "component3_training_v2.csv"),
    ]
    for path in paths:
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Build map: material_name → waste_type (unique per material)
            _category_map = dict(zip(df['material_name'], df['waste_type']))
            print(f"  CATEGORY_MAP loaded from CSV: {len(_category_map)} materials")
            return _category_map

    # Fallback if CSV not found
    print("  WARNING: training CSV not found — using fallback map")
    _category_map = {
        "Newspapers":"Organic","Cardboard Boxes":"Organic","Office Paper":"Organic",
        "PET Water Bottles":"Plastic","Food Containers":"Plastic","Plastic Bags":"Plastic",
        "Glass Bottles":"Glass","Glass Jars":"Glass",
        "Old Clothes":"Organic","Fabric Scraps":"Organic",
        "Old Tires":"Rubber","Rubber Footwear":"Rubber",
        "Wooden Pallets":"Organic","Furniture Scraps":"Organic",
    }
    return _category_map


def _load_toxicity_map():
    """Load toxicity mapping from training CSV"""
    global _toxicity_map
    if _toxicity_map:
        return _toxicity_map
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "data", "component3_training_v2.csv"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml_training", "material_model", "dataset", "component3_training_v2.csv"),
    ]
    for path in paths:
        if os.path.exists(path):
            df = pd.read_csv(path)
            _toxicity_map = dict(zip(df['material_name'], df['toxicity_level']))
            return _toxicity_map

    # Fallback
    _toxicity_map = {"Old Tires": "Medium"}
    return _toxicity_map


def build_process_recipe(
    material_name, waste_type, weight_kg, moisture_condition,
    recommended_method,
    optimal_temp_c, processing_time_min, energy_kwh, recycling_efficiency_pct,
    safety_status, pre_drying_required, toxicity_level,
    batch_id=None,
):
    chemical_map  = _load_chemical_map()
    category_map  = _load_category_map()

    chemical_info = chemical_map.get(material_name, {
        "chemical_agent"        : "None",
        "chemical_concentration": "None",
        "chemical_purpose"      : "No chemical required",
        "handling_note"         : "Standard safety",
    })

    # Auto fix waste_type — from CSV, not hardcoded
    if not waste_type:
        waste_type = category_map.get(material_name, "Organic")

    # Pre-drying — material specific (from MCDM output)
    if pre_drying_required:
        pre_drying_temp_c   = round(optimal_temp_c * 0.4, 1) if optimal_temp_c else 80.0
        pre_drying_time_min = round(processing_time_min * 0.3, 1)
        pre_drying_action   = "Apply controlled heat to remove moisture content"
    else:
        pre_drying_temp_c   = None
        pre_drying_time_min = None
        pre_drying_action   = None

    # Cooling
    cooling_time_min = round(processing_time_min * 0.25, 1)
    cooling_method   = "Controlled Cooling"
    target_temp_c    = 30.0

    # Timestamp
    timestamp = datetime.utcnow().isoformat()

    return {
        # ── Input echo ───────────────────────────────────
        "material_name"           : material_name,
        "waste_type"              : waste_type,
        "weight_kg"               : weight_kg,
        "moisture_condition"      : moisture_condition,

        # ── Model 1 — Decision Tree ──────────────────────
        "recommended_method"      : recommended_method,

        # ── Model 2 — MCDM ──────────────────────────────
        "optimal_temp_c"          : optimal_temp_c,
        "processing_time_min"     : processing_time_min,
        "energy_kwh"              : energy_kwh,
        "recycling_efficiency_pct": recycling_efficiency_pct,

        # ── Model 3 — Rule-Based ─────────────────────────
        "safety_status"           : safety_status,
        "pre_drying_required"     : pre_drying_required,
        "toxicity_level"          : toxicity_level,

        # ── Pre-drying details ───────────────────────────
        "pre_drying_temp_c"       : pre_drying_temp_c,
        "pre_drying_time_min"     : pre_drying_time_min,
        "pre_drying_action"       : pre_drying_action,

        # ── Chemical agent ───────────────────────────────
        "chemical_agent"          : chemical_info.get("chemical_agent"),
        "chemical_concentration"  : chemical_info.get("chemical_concentration"),
        "chemical_purpose"        : chemical_info.get("chemical_purpose"),
        "handling_note"           : chemical_info.get("handling_note"),

        # ── Cooling ──────────────────────────────────────
        "cooling_time_min"        : cooling_time_min,
        "cooling_method"          : cooling_method,
        "target_temp_c"           : target_temp_c,

        # ── Metadata ─────────────────────────────────────
        "batch_id"                : batch_id,
        "timestamp"               : timestamp,
    }