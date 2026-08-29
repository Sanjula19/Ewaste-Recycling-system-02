"""
Component 3 - Feature Engineering
material_name string -> ML features
"""

MATERIAL_PROPERTIES = {
    "Aluminum"            : {"melting_point": 660,  "density": 2.70, "heat_capacity": 900},
    "Steel"               : {"melting_point": 1370, "density": 7.85, "heat_capacity": 490},
    "Scrap Steel"         : {"melting_point": 1370, "density": 7.80, "heat_capacity": 490},
    "Sheet Metal"         : {"melting_point": 500,  "density": 7.50, "heat_capacity": 500},
    "Lead-Based Alloy"    : {"melting_point": 327,  "density": 11.3, "heat_capacity": 128},
    "Polypropylene"       : {"melting_point": 160,  "density": 0.91, "heat_capacity": 1900},
    "Plastic Resin"       : {"melting_point": 180,  "density": 1.10, "heat_capacity": 1800},
    "Reprocessed Plastics": {"melting_point": 170,  "density": 1.05, "heat_capacity": 1850},
    "Packaging"           : {"melting_point": 150,  "density": 0.95, "heat_capacity": 1700},
    "Circuit Board"       : {"melting_point": 300,  "density": 2.10, "heat_capacity": 800},
    "Machine Component"   : {"melting_point": 400,  "density": 5.50, "heat_capacity": 600},
    "Cotton"              : {"melting_point": 150,  "density": 0.15, "heat_capacity": 1300},
    "Textiles"            : {"melting_point": 150,  "density": 0.20, "heat_capacity": 1300},
    "Solvent"             : {"melting_point": 200,  "density": 0.87, "heat_capacity": 1700},
    "Industrial Oil"      : {"melting_point": 250,  "density": 0.90, "heat_capacity": 1900},
    "Coolant"             : {"melting_point": 200,  "density": 1.07, "heat_capacity": 3300},
    "Catalyst"            : {"melting_point": 300,  "density": 3.50, "heat_capacity": 750},
}


def get_material_features(material_name: str) -> dict:
    """Get physical properties for a material."""
    return MATERIAL_PROPERTIES.get(material_name, {
        "melting_point": 200,
        "density"      : 2.5,
        "heat_capacity": 900,
    })
