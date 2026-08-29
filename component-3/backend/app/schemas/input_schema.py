from pydantic import BaseModel, Field
from typing import Optional


class OptimizeRequest(BaseModel):
    material_name      : str            = Field(...,           example="PET Water Bottles")
    weight_kg          : float          = Field(...,           example=5.0)
    moisture_condition : str            = Field(...,           example="Wet")
    waste_type         : Optional[str]  = Field(default=None)
    moisture_pct       : float          = Field(default=50.0)
    processing_priority: str            = Field(default="balanced")
    operator_id        : Optional[str]  = Field(default=None)
    batch_id           : Optional[str]  = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "material_name"     : "PET Water Bottles",
                "weight_kg"         : 5.0,
                "moisture_condition": "Wet"
            }
        }
    }