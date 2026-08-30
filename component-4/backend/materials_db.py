"""
materials_db.py
----------------
Reference data for the disposition engine.

FINAL SCOPE: six recyclable metals, three non-recyclable residuals:

    Metals:          Aluminium, Nickel, Steel, Lead, Zinc, Copper
    Residual waste:  PVC Plastic, Polystyrene, Contaminated Glass

Gold and silver are out of scope on the metals side.

SOURCE OF TRUTH FOR THE NUMBERS BELOW: your own strategic_disposition.py /
thermodynamic_properties_db.json pipeline (the one that parsed the MatWeb
CSVs + EPA WARM data and generated a real thermodynamic database), not a
literature-midpoint guess. Specifically, pulled from your generated DB:

    PVC          -> LHV 20.0 MJ/kg, Bio-oil 45% / Syngas 30% / Char 25%
    Polystyrene  -> LHV 40.0 MJ/kg, Bio-oil 45% / Syngas 30% / Char 25%
                    (every polystyrene sub-grade in your DB -- EPS, flame
                    retardant, molded, impact-modified -- converged on the
                    same 40.0 MJ/kg, so one number covers all of them)
    Contaminated
    Glass        -> LHV 0.0 MJ/kg (inorganic, does not combust), modeled
                    as a pure thermal heat sink using Density 2.52 g/cc
                    and Specific Heat 0.84 J/g-C, matching your DB's
                    "EPA_WARM_MSW_Mixed_Glass" entry -- the closest match
                    to "contaminated municipal glass" in your dataset.

This is a materially different (and more correct) model for glass than an
earlier draft of this file used: glass isn't burned for a small energy
credit, it's treated as a mass that must be heated to pyrolysis
temperature alongside the combustible batch, which *costs* energy rather
than yielding it. See disposition_service.py for the Q = m x Cp x dT
calculation this feeds into, taken directly from your
EnergyRecoveryCalculator class.

A copy of the full generated thermodynamic_properties_db.json (50+
materials, not just the 3 in scope here) ships in
models/reference/thermodynamic_properties_db.json for your report /
future scope expansion -- this file only wires up the 3 currently in use.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Route = Literal["pyrolysis", "thermal_recovery", "mechanical_recycling", "recyclable_metal"]

# Which of the two treatment processes a residual goes through.
#
#   pyrolysis  -- thermal. Heat the material in the absence of oxygen and
#                 recover bio-oil / syngas / char. Applies to polystyrene
#                 and polypropylene; contaminated glass rides this route
#                 too but as an inert heat sink (it consumes energy
#                 rather than yielding it -- see is_heat_sink).
#
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


# ---------------------------------------------------------------------------
# Material thermal profile
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MaterialProfile:
    is_heat_sink: bool          # True = inert, doesn't combust (e.g. glass)
    lhv_mj_kg: float            # 0.0 for heat-sink materials
    oil_frac: float
    gas_frac: float
    char_frac: float
    recycling_method: RecyclingMethod = "pyrolysis"  # see RecyclingMethod above
    density_g_cc: float = 0.0        # only meaningful for heat-sink materials
    specific_heat_j_g_c: float = 0.0  # only meaningful for heat-sink materials
    source_db_key: str = ""          # matching key in thermodynamic_properties_db.json


NON_RECYCLABLES: dict[str, MaterialProfile] = {
    # PVC is routed to MECHANICAL recycling, not pyrolysis. The LHV and
    # yield fractions below are retained from the source datasheet for
    # reference only -- nothing on the mechanical route reads them, since
    # shredding and granulating releases no energy to account for.
    "pvc plastic": MaterialProfile(
        is_heat_sink=False, lhv_mj_kg=20.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        recycling_method="mechanical",
        source_db_key="Vycom VINTEC I (R) PVC Polyvinyl Chloride (PVC)",
    ),
    "pvc": MaterialProfile(
        is_heat_sink=False, lhv_mj_kg=20.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        recycling_method="mechanical",
        source_db_key="Vycom VINTEC I (R) PVC Polyvinyl Chloride (PVC)",
    ),
    "polystyrene": MaterialProfile(
        is_heat_sink=False, lhv_mj_kg=40.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        source_db_key="Overview of materials for Expanded Polystyrene (EPS)",
    ),
    "pp": MaterialProfile(
        is_heat_sink=False, lhv_mj_kg=42.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        source_db_key="Polypropylene (PP) Scrap",
    ),
    "polypropylene": MaterialProfile(
        is_heat_sink=False, lhv_mj_kg=42.0, oil_frac=0.45, gas_frac=0.30, char_frac=0.25,
        source_db_key="Polypropylene (PP) Scrap",
    ),
    "contaminated glass": MaterialProfile(
        is_heat_sink=True, lhv_mj_kg=0.0, oil_frac=0.0, gas_frac=0.0, char_frac=1.0,
        density_g_cc=2.52, specific_heat_j_g_c=0.84,
        source_db_key="EPA_WARM_MSW_Mixed_Glass",
    ),
    "glass": MaterialProfile(
        is_heat_sink=True, lhv_mj_kg=0.0, oil_frac=0.0, gas_frac=0.0, char_frac=1.0,
        density_g_cc=2.52, specific_heat_j_g_c=0.84,
        source_db_key="EPA_WARM_MSW_Mixed_Glass",
    ),
}


def resolve_material(waste_type: str) -> tuple[Route, "MaterialProfile | None"]:
    """
    Returns (route, profile). profile is None for recyclable metals.
    Raises KeyError for out-of-scope metals (gold, silver) or anything
    else this component doesn't recognise.
    """
    key = waste_type.strip().lower()
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
        if profile.recycling_method == "mechanical":
            route = "mechanical_recycling"
        elif profile.is_heat_sink:
            route = "thermal_recovery"
        else:
            route = "pyrolysis"
        return route, profile
    raise KeyError(
        f"Unrecognised waste_type '{waste_type}'. Known non-recyclables: "
        f"{sorted(NON_RECYCLABLES)}. Known recyclable metals: aluminium, nickel, "
        f"steel, lead, zinc, copper."
    )


# ---------------------------------------------------------------------------
# Process constants -- taken directly from your EnergyRecoveryCalculator /
# strategic_disposition.py, not re-derived.
# ---------------------------------------------------------------------------
PYROLYSIS_EFFICIENCY = 0.67          # eta in E_rec = M x LHV x eta
PYROLYSIS_TEMP_CELSIUS = 500.0       # process temperature the heat-sink calc heats material to
AMBIENT_TEMP_CELSIUS = 25.0          # assumed intake temperature
# Exact, not the truncated decimals these are usually quoted as. The
# conversion is definitional -- 1 kWh IS 3.6 MJ -- so writing 0.277778
# throws away precision for no reason. The rounded forms (2.77778e-7 and
# 0.277778) are what your strategic_disposition.py notebook printed and
# remain correct to 6 s.f.; these just avoid compounding that truncation
# across a whole cycle's worth of batches.
JOULES_TO_KWH = 1.0 / 3.6e6          # 1 J  = 2.777778e-7 kWh
MJ_TO_KWH = 1.0 / 3.6                # 1 MJ = 0.2777778 kWh

# kg CO2 avoided per kWh of grid electricity displaced.
# Sri Lanka Sustainable Energy Authority, "Sri Lanka Energy Balance 2022":
# Combined Margin grid emission factor = 0.6482 kgCO2/kWh (Simple Operating
# Margin 0.7123, Build Margin 0.5841). Combined Margin is the figure
# typically used in CDM-style project accounting, so it's the default here.
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.6482

# Feed-in tariff paid for waste-to-energy electricity under the Karadiyana
# (Colombo South) W2E project's power purchase agreement -- used to put an
# indicative LKR value on the recovered energy. Source: Fairway Waste
# Management project page / Wikipedia (Colombo South Waste Processing
# Facility), tariff = 37.10 LKR/kWh.
WTE_FEED_IN_TARIFF_LKR_PER_KWH = 37.10

PYROLYSIS_OIL_DENSITY_KG_PER_L = 0.90  # typical plastic-pyrolysis oil density
