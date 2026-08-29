"""
Component 3 - Safety Service
Rule-Based Expert System - safety_status / pre_drying_required
"""

import json
import os

_rules_cache    = None
_toxicity_cache = None


def _load_rules():
    global _rules_cache, _toxicity_cache
    if _rules_cache:
        return _rules_cache, _toxicity_cache

    path = os.path.join(os.path.dirname(__file__), "..", "data", "safety_rules.json")
    with open(path) as f:
        data = json.load(f)

    _rules_cache    = data["rules"]["moisture_toxicity_matrix"]
    _toxicity_cache = data["rules"]["material_toxicity_map"]
    return _rules_cache, _toxicity_cache


def get_toxicity_level(material_name):
    """Get toxicity level for a material."""
    _, toxicity_map = _load_rules()
    return toxicity_map.get(material_name, "Low")


def check_safety(material_name, moisture_condition, toxicity_level=None):
    """
    Rule-based safety check.
    Returns: safety_status, pre_drying_required
    """
    rules, _ = _load_rules()

    if toxicity_level is None:
        toxicity_level = get_toxicity_level(material_name)

    moisture_rules = rules.get(moisture_condition, rules["Dry"])
    safety_status  = moisture_rules.get(toxicity_level, "SECURE")
    pre_drying     = (moisture_condition == "Wet")

    return {
        "safety_status"      : safety_status,
        "pre_drying_required": pre_drying,
        "toxicity_level"     : toxicity_level,
    }
