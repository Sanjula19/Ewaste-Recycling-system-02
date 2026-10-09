"""
materials_db.py
----------------
Reference data for the disposition engine.

SCOPE: six recyclable metals, three non-recyclable residuals:

    Metals:          Aluminium, Nickel, Steel, Lead, Zinc, Copper
    Residual waste:  PVC Plastic, Polystyrene, Polypropylene

Out of scope, and rejected rather than guessed at:
    Gold, silver            -- metals this component does not value
    Glass, contaminated     -- see GLASS_REJECTION below
    glass, and variants

GLASS WAS REMOVED FROM STRATEGIC DISPOSITION
Contaminated glass used to ride the pyrolysis route as an inert "heat
sink": it does not combust, so instead of crediting it energy the model
charged the energy needed to heat that mass to process temperature
(Q = m x Cp x dT) and reported a NEGATIVE energy recovery. That was an
honest way to model co-processing glass, but co-processing glass is not
what this system should be recommending in the first place -- glass
belongs with a glass recycler, not in a pyrolysis or waste-to-energy
feed. So the material, the heat-sink calculation and its constants
(process temperature, ambient temperature, J->kWh) are all gone, and the
material is now refused on the same path as gold and silver.

The specific-heat and density figures that fed that calculation are still
in models/reference/thermodynamic_properties_db.json (a 50+ material
archive kept for future scope), but nothing reads them any more.

SOURCE OF TRUTH FOR THE NUMBERS BELOW: the strategic_disposition.py /
thermodynamic_properties_db.json pipeline that parsed the MatWeb CSVs plus
EPA WARM data, not a literature-midpoint guess. Specifically:

    PVC          -> LHV 20.0 MJ/kg, Bio-oil 45% / Syngas 30% / Char 25%
    Polystyrene  -> LHV 40.0 MJ/kg, Bio-oil 45% / Syngas 30% / Char 25%
                    (every polystyrene sub-grade in that DB -- EPS, flame
                    retardant, molded, impact-modified -- converged on
                    40.0 MJ/kg, so one number covers all of them)
    Polypropylene-> LHV 42.0 MJ/kg, same 45/30/25 split

PVC's LHV is retained for reference only. PVC is routed to MECHANICAL
recycling, which releases no energy, so nothing on its route reads it.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import re

Route = Literal["pyrolysis", "mechanical_recycling", "recyclable_metal"]

# Which treatment process a residual goes through.
#
#   pyrolysis  -- thermal. Heat the material without oxygen and recover
#                 bio-oil / syngas / char. Polystyrene and polypropylene.
#                 A waste-to-energy incinerator is the alternative
#                 destination for the same two materials.
#   mechanical -- physical. Shred, wash and granulate back into feedstock.
#                 No combustion, so no energy recovery figure exists for
#                 it at all: reporting 0 kWh here is the honest answer,
#                 not a gap in the model. PVC goes this way.
RecyclingMethod = Literal["pyrolysis", "mechanical"]

# ---------------------------------------------------------------------------
# Recyclable metals -> handled by /forecast, not /disposition.
# ---------------------------------------------------------------------------
RECYCLABLE_METALS = {
    "aluminium", "aluminum", "nickel", "steel", "steel scrap", "steel_scrap",
    "lead", "zinc", "copper",
}

OUT_OF_SCOPE_METALS = {"gold", "silver"}

# Refused with its own message, because "unrecognised material" would be
# misleading -- glass is recognised perfectly well, it simply does not
# belong in this component any more.
GLASS_REJECTION = (
    "Contaminated glass is outside the scope of strategic disposition and "
    "should be sent to a glass recycler."
)


def _normalise(waste_type: str) -> str:
    """Lowercase, and collapse punctuation/underscores to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", waste_type.strip().lower()).strip()


def is_glass(waste_type: str) -> bool:
    """
    True for glass under any naming variant -- "glass", "Contaminated
    Glass", "contaminated_glass", "mixed glass", "glass (contaminated)".

    Matched on the word rather than an enumerated list, because the list
    is the part that rots: a caller inventing "waste glass" next month
    should still be refused, not silently fall through to "unrecognised".
    No in-scope material contains the word, so this cannot over-match.
    """
    return "glass" in _normalise(waste_type).split()


# ---------------------------------------------------------------------------
# Material thermal profile
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MaterialProfile:
    lhv_mj_kg: float
    oil_frac: float
    gas_frac: float
    char_frac: float
    recycling_method: RecyclingMethod = "pyrolysis"
    source_db_key: str = ""          # matching key in thermodynamic_properties_db.json


NON_RECYCLABLES: dict[str, MaterialProfile] = {
    # PVC is routed to MECHANICAL recycling, not pyrolysis. The LHV and
    # yield fractions below are retained from the source datasheet for
    # reference only -- nothing on the mechanical route reads them, since
    # shredding and granulating releases no energy to account for.
    "pvc plastic": MaterialProfile(
        lhv_mj_kg=20.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        recycling_method="mechanical",
        source_db_key="Vycom VINTEC I (R) PVC Polyvinyl Chloride (PVC)",
    ),
    "pvc": MaterialProfile(
        lhv_mj_kg=20.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        recycling_method="mechanical",
        source_db_key="Vycom VINTEC I (R) PVC Polyvinyl Chloride (PVC)",
    ),
    "polystyrene": MaterialProfile(
        lhv_mj_kg=40.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        source_db_key="Overview of materials for Expanded Polystyrene (EPS)",
    ),
    "pp": MaterialProfile(
        lhv_mj_kg=42.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        source_db_key="Polypropylene (PP) Scrap",
    ),
    "polypropylene": MaterialProfile(
        lhv_mj_kg=42.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        source_db_key="Polypropylene (PP) Scrap",
    ),
}


def resolve_material(waste_type: str) -> tuple[Route, "MaterialProfile | None"]:
    """
    Returns (route, profile). profile is None for recyclable metals.

    Raises KeyError for anything this component does not handle: glass
    (with its own message), gold and silver, or an unrecognised name.
    Callers turn that into an HTTP 400 -- see routers/disposition.py.
    """
    key = waste_type.strip().lower()

    if is_glass(waste_type):
        raise KeyError(GLASS_REJECTION)

    if key in OUT_OF_SCOPE_METALS:
        raise KeyError(
            f"'{waste_type}' is out of scope for this component (metals covered: "
            f"aluminium, nickel, steel, lead, zinc, copper). Route it through a "
            f"different module."
        )
    if key in RECYCLABLE_METALS:
        return "recyclable_metal", None
    if key in NON_RECYCLABLES:
        profile = NON_RECYCLABLES[key]
        route: Route = (
            "mechanical_recycling" if profile.recycling_method == "mechanical"
            else "pyrolysis"
        )
        return route, profile
    raise KeyError(
        f"Unrecognised waste_type '{waste_type}'. Known non-recyclables: "
        f"{sorted(NON_RECYCLABLES)}. Known recyclable metals: aluminium, nickel, "
        f"steel, lead, zinc, copper."
    )


# ---------------------------------------------------------------------------
# Process constants -- taken directly from the EnergyRecoveryCalculator /
# strategic_disposition.py pipeline, not re-derived.
# ---------------------------------------------------------------------------
PYROLYSIS_EFFICIENCY = 0.67          # eta in E_rec = M x LHV x eta

# Exact, not the truncated decimals this is usually quoted as. The
# conversion is definitional -- 1 kWh IS 3.6 MJ -- so writing 0.277778
# throws away precision for no reason. The rounded form is what
# strategic_disposition.py printed and remains correct to 6 s.f.; this
# just avoids compounding that truncation across a whole cycle.
MJ_TO_KWH = 1.0 / 3.6                # 1 MJ = 0.2777778 kWh

# kg CO2 avoided per kWh of grid electricity DISPLACED. Only meaningful
# for a plant that actually exports electricity to the grid -- see
# disposition_service, which reports it for nothing else.
#
# Sri Lanka Sustainable Energy Authority, "Sri Lanka Energy Balance 2022":
# Combined Margin grid emission factor = 0.6482 kgCO2/kWh (Simple
# Operating Margin 0.7123, Build Margin 0.5841). Combined Margin is the
# figure used in CDM-style project accounting, so it is the default here.
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.6482

PYROLYSIS_OIL_DENSITY_KG_PER_L = 0.90  # typical plastic-pyrolysis oil density

# NOTE: the waste-to-energy feed-in tariff used to live here as a single
# module constant (37.10 LKR/kWh, the Karadiyana PPA rate). It is now a
# per-facility field in backend/data/facilities.json, because it is a
# property of one plant's power purchase agreement and applying it to
# every plant overstated what the others are known to pay. A facility
# with no sourced tariff reports no electricity value at all.
