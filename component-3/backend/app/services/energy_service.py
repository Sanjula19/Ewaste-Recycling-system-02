"""
Component 3 - Energy Service
MCDM Optimizer — material-specific parameters from training CSV
"""

import pandas as pd
import os

_benchmark_cache = {}
_material_params = {}

# Mechanical materials — no heat required
MECHANICAL_MATERIALS = {
    "Newspapers", "Cardboard Boxes", "Office Paper",
    "Glass Bottles", "Glass Jars",
    "Old Clothes", "Fabric Scraps",
    "Wooden Pallets", "Furniture Scraps",
}

# Thermal materials — temperature required
THERMAL_PARAMS = {
    "PET Water Bottles" : {"avg_temp": 265.0, "avg_time": 35.0},
    "Food Containers"   : {"avg_temp": 250.0, "avg_time": 32.0},
    "Plastic Bags"      : {"avg_temp": 230.0, "avg_time": 28.0},
    "Old Tires"         : {"avg_temp": 350.0, "avg_time": 55.0},
    "Rubber Footwear"   : {"avg_temp": 310.0, "avg_time": 45.0},
}

# Mechanical materials — processing time only (no temp)
MECHANICAL_PARAMS = {
    "Newspapers"       : {"avg_time": 15.0},
    "Cardboard Boxes"  : {"avg_time": 18.0},
    "Office Paper"     : {"avg_time": 12.0},
    "Glass Bottles"    : {"avg_time": 8.0},
    "Glass Jars"       : {"avg_time": 8.0},
    "Old Clothes"      : {"avg_time": 20.0},
    "Fabric Scraps"    : {"avg_time": 16.0},
    "Wooden Pallets"   : {"avg_time": 25.0},
    "Furniture Scraps" : {"avg_time": 28.0},
}


def _load_benchmark():
    global _benchmark_cache
    if _benchmark_cache:
        return _benchmark_cache

    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "recycling_benchmark.csv")

    df = pd.read_csv(path)
    print("CSV Columns:", list(df.columns))

    for mat in df["Material Name"].unique():
        rows = df[df["Material Name"] == mat]
        _benchmark_cache[mat] = {
            "avg_energy": round(rows["Energy Consumption (kWh)"].mean(), 1),
            "avg_eff"   : round(rows["Recycled Material (%)"].mean(), 1),
        }
    return _benchmark_cache


def calculate_optimal_parameters(material_name, weight_kg,
                                  moisture_condition,
                                  processing_priority="balanced"):
    benchmark     = _load_benchmark()
    weight_factor = weight_kg / 5.0
    drying_adj    = 10.0 if moisture_condition == "Wet" else 0.0

    if processing_priority == "energy":
        time_mult, energy_mult = 1.15, 0.90
    elif processing_priority == "speed":
        time_mult, energy_mult = 0.90, 1.10
    else:
        time_mult, energy_mult = 1.0, 1.0

    # Energy + efficiency from benchmark CSV
    base_energy = benchmark.get(material_name, {}).get("avg_energy", 5.0)
    base_eff    = benchmark.get(material_name, {}).get("avg_eff", 82.0)

    # ── Mechanical — NO temperature ──────────────────────
    if material_name in MECHANICAL_MATERIALS:
        base_time = MECHANICAL_PARAMS.get(material_name, {}).get("avg_time", 20.0)
        return {
            "optimal_temp_c"          : 0.0,
            "processing_time_min"     : round((base_time + drying_adj) * time_mult, 1),
            "energy_kwh"              : round(base_energy * weight_factor * energy_mult, 2),
            "recycling_efficiency_pct": round(base_eff, 1),
        }

    # ── Thermal — WITH temperature ───────────────────────
    thermal = THERMAL_PARAMS.get(material_name, {"avg_temp": 250.0, "avg_time": 35.0})
    return {
        "optimal_temp_c"          : round(thermal["avg_temp"], 1),
        "processing_time_min"     : round((thermal["avg_time"] + drying_adj) * time_mult, 1),
        "energy_kwh"              : round(base_energy * weight_factor * energy_mult, 2),
        "recycling_efficiency_pct": round(base_eff, 1),
    }