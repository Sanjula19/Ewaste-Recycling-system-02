"""
Component 3 - GET /materials route
Returns all supported materials list
"""

from fastapi import APIRouter

router = APIRouter()

MATERIALS = [
    { "name": "Newspapers",        "waste_type": "Paper",   "category": "Paper",   "toxicity": "Low"    },
    { "name": "Cardboard Boxes",   "waste_type": "Paper",   "category": "Paper",   "toxicity": "Low"    },
    { "name": "Office Paper",      "waste_type": "Paper",   "category": "Paper",   "toxicity": "Low"    },
    { "name": "PET Water Bottles", "waste_type": "Plastic", "category": "Plastic", "toxicity": "Low"    },
    { "name": "Food Containers",   "waste_type": "Plastic", "category": "Plastic", "toxicity": "Low"    },
    { "name": "Plastic Bags",      "waste_type": "Plastic", "category": "Plastic", "toxicity": "Low"    },
    { "name": "Glass Bottles",     "waste_type": "Glass",   "category": "Glass",   "toxicity": "Low"    },
    { "name": "Glass Jars",        "waste_type": "Glass",   "category": "Glass",   "toxicity": "Low"    },
]


@router.get("/materials")
def get_materials():
    """Return all supported materials list."""
    return {
        "total"    : len(MATERIALS),
        "materials": MATERIALS
    }