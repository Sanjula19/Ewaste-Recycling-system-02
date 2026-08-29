"""
Component 3 - Input Validators
"""

VALID_MATERIALS = [
    "Aluminum", "Steel", "Scrap Steel", "Sheet Metal", "Lead-Based Alloy",
    "Polypropylene", "Plastic Resin", "Reprocessed Plastics", "Packaging",
    "Circuit Board", "Machine Component", "Cotton", "Textiles",
    "Solvent", "Industrial Oil", "Coolant", "Catalyst"
]

VALID_WASTE_TYPES = ["Metal", "Plastic", "E-waste", "Organic", "Chemical"]
VALID_MOISTURE    = ["Wet", "Dry"]


def validate_input(material_name, waste_type, weight_kg, moisture_condition):
    """Validate input fields. Returns dict with valid status and errors."""
    errors = []

    if material_name not in VALID_MATERIALS:
        errors.append(f"Invalid material_name: {material_name}. Valid: {VALID_MATERIALS}")

    if waste_type not in VALID_WASTE_TYPES:
        errors.append(f"Invalid waste_type: {waste_type}. Valid: {VALID_WASTE_TYPES}")

    if not (0.1 <= weight_kg <= 1000):
        errors.append(f"weight_kg must be 0.1-1000. Got: {weight_kg}")

    if moisture_condition not in VALID_MOISTURE:
        errors.append(f"moisture_condition must be Wet or Dry. Got: {moisture_condition}")

    return {"valid": len(errors) == 0, "errors": errors}
