"""
Component 3 - Optimization Service
Decision Tree predict - recommended_method
"""

from app.models.material_model.load_models import predict_method


def get_recommended_method(material_name, waste_type, weight_kg,
                           moisture_condition, moisture_pct, toxicity_level):
    """
    Decision Tree model - predict recommended recycling method.
    Returns: 'Thermal' | 'Chemical' | 'Mechanical'
    """
    return predict_method(
        material_name      = material_name,
        waste_type         = waste_type,
        weight_kg          = weight_kg,
        moisture_condition = moisture_condition,
        moisture_pct       = moisture_pct,
        toxicity_level     = toxicity_level
    )
