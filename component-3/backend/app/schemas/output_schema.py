"""
Component 3 - Output Schema (Pydantic)
"""

from pydantic import BaseModel
from typing import Optional


class OptimizeResponse(BaseModel):
    # Input echo
    material_name      : str
    waste_type         : Optional[str] = None
    weight_kg          : float
    moisture_condition : str

    # Model 1 - Decision Tree output
    recommended_method : str

    # Model 2 - MCDM output
    optimal_temp_c            : float
    processing_time_min       : float
    energy_kwh                : float
    recycling_efficiency_pct  : float

    # Model 3 - Rule-Based output
    safety_status        : str
    pre_drying_required  : bool
    toxicity_level       : str

    # Pre-drying specific
    pre_drying_temp_c    : Optional[float] = None
    pre_drying_time_min  : Optional[float] = None
    pre_drying_action    : Optional[str]   = None

    # Chemical agent info
    chemical_agent        : Optional[str] = None
    chemical_concentration: Optional[str] = None
    chemical_purpose      : Optional[str] = None
    handling_note         : Optional[str] = None

    # Cooling
    cooling_time_min : Optional[float] = None
    cooling_method   : Optional[str]   = None
    target_temp_c    : Optional[float] = None

    # Metadata
    batch_id  : Optional[str] = None
    timestamp : Optional[str] = None
    doc_id    : Optional[str] = None

    # IoT moisture provenance ("sensor" or "manual")
    moisture_source : Optional[str]   = None
    sensor_raw_value: Optional[int]   = None
    sensor_timestamp: Optional[str]   = None