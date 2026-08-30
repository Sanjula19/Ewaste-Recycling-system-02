"""
services/disposition_service.py
----------------------------------
Builds a DispositionResponse for one batch of residual (non-recyclable)
waste.

This now implements the SAME physics as your EnergyRecoveryCalculator in
strategic_disposition.py, not a simplified stand-in:

  - Combustible materials (PVC, Polystyrene): E_rec = M x LHV x eta,
    exactly your formula, converted MJ -> kWh via your MJ_TO_KWH constant.
  - Inert heat-sink materials (Contaminated Glass): glass does not
    combust, so instead of crediting it energy, the model charges the
    energy it takes to HEAT that mass to pyrolysis temperature:
        Q = m x Cp x dT   (Cp = specific heat, dT = 500C - 25C)
    converted J -> kWh via your JOULES_TO_KWH constant. This is reported
    as wasted_energy_kwh, and energy_recovery_kwh is NEGATIVE for a
    glass-only batch -- an honest signal that co-processing contaminated
    glass costs process energy rather than yielding it, exactly what your
    notebook's sensitivity analysis (break-even plastic %) was built to
    show. thermal_classification tells the caller which case it is so a
    negative number on the dashboard is self-explanatory rather than
    looking like a bug.

For a request that mixes plastic and glass in real deployment (single
batch, mixed composition) you'd sum both terms the way
calculate_energy_recovery() does over a list of payloads -- this
single-material-per-request API only ever hits one branch per call, since
DispositionRequest.waste_type is one material at a time.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone

from materials_db import (
    resolve_material,
    PYROLYSIS_EFFICIENCY,
    PYROLYSIS_TEMP_CELSIUS,
    AMBIENT_TEMP_CELSIUS,
    JOULES_TO_KWH,
    MJ_TO_KWH,
    GRID_EMISSION_FACTOR_KG_PER_KWH,
    WTE_FEED_IN_TARIFF_LKR_PER_KWH,
    PYROLYSIS_OIL_DENSITY_KG_PER_L,
)
from services import fx_service, facility_service
from schemas import (
    DispositionRequest,
    DispositionResponse,
    EnergyBreakdown,
    FacilityMatch,
    FXInfo,
)

# Same stream-weighting simplification as before, used only to split a
# single kWh total across bio-oil/syngas/char for reporting -- see
# module docstring in the previous revision for the reasoning. Not used
# for heat-sink materials (no combustion, no split needed).
_STREAM_WEIGHTS = {"oil": 1.0, "gas": 0.55, "char": 0.65}


def _new_manifest_id() -> str:
    return f"MAN-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def calculate_disposition(req: DispositionRequest) -> DispositionResponse:
    route, profile = resolve_material(req.waste_type)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest_id = _new_manifest_id()

    if route == "recyclable_metal":
        return DispositionResponse(
            waste_type=req.waste_type,
            weight_kg=req.weight_kg,
            is_recyclable=True,
            disposition_route="Recyclable metal -- use /api/forecast for Sell/Hold valuation",
            thermal_classification=None,
            energy_recovery_kwh=0.0,
            energy_breakdown=EnergyBreakdown(
                bio_oil_liters=0.0, syngas_kwh=0.0, char_kg=0.0, total_kwh=0.0, yield_efficiency_pct=0.0
            ),
            gross_energy_kwh=None,
            wasted_energy_kwh=None,
            lhv_mj_kg=0.0,
            process_efficiency=0.0,
            landfill_diverted=True,
            co2_avoided_kg=0.0,
            manifest_id=manifest_id,
            timestamp=now_iso,
            facility_name=req.facility_name or "Urban Recycling Facility",
            nearest_treatment_facility=None,
            estimated_revenue_usd=None,
            estimated_revenue_lkr=None,
            fx=None,
        )

    fx = fx_service.get_fx_rates()

    # --- Mechanical recycling (PVC): no thermal processing at all ------
    # Shredding, washing and granulating back into feedstock releases no
    # energy, so there is nothing to recover, nothing to burn, and no
    # grid electricity displaced. Every energy and CO2 figure is
    # genuinely zero here rather than unmeasured.
    if profile.recycling_method == "mechanical":
        recycler, recycler_distance = facility_service.nearest_facility(
            req.latitude, req.longitude, kind="mechanical"
        )
        return DispositionResponse(
            waste_type=req.waste_type,
            weight_kg=req.weight_kg,
            is_recyclable=False,
            disposition_route="Mechanical Recycling",
            disposition_method="mechanical",
            dispatch_note=(
                f"Dispatch {req.weight_kg:g} kg of {req.waste_type} to "
                f"{recycler.name} ({recycler_distance} km) for shredding, washing "
                f"and granulation into recycled feedstock. Do NOT route this batch "
                f"to a pyrolysis or waste-to-energy plant."
            ),
            thermal_classification=None,
            energy_recovery_kwh=0.0,
            energy_breakdown=EnergyBreakdown(
                bio_oil_liters=0.0, syngas_kwh=0.0, char_kg=0.0,
                total_kwh=0.0, yield_efficiency_pct=0.0,
            ),
            gross_energy_kwh=None,
            wasted_energy_kwh=None,
            lhv_mj_kg=0.0,
            process_efficiency=0.0,
            landfill_diverted=True,
            co2_avoided_kg=0.0,
            manifest_id=manifest_id,
            timestamp=now_iso,
            facility_name=req.facility_name or "Urban Recycling Facility",
            nearest_treatment_facility=FacilityMatch(
                name=recycler.name,
                facility_type=recycler.facility_type,
                latitude=recycler.latitude,
                longitude=recycler.longitude,
                distance_km=recycler_distance,
                feed_in_tariff_lkr_per_kwh=None,
            ),
            estimated_revenue_usd=None,
            estimated_revenue_lkr=None,
            fx=FXInfo(**fx),
        )

    facility, distance_km = facility_service.nearest_facility(
        req.latitude, req.longitude, kind="thermal"
    )

    if profile.is_heat_sink:
        # --- Inert heat sink (Contaminated Glass): Q = m x Cp x dT ---
        mass_g = req.weight_kg * 1000.0
        delta_t = PYROLYSIS_TEMP_CELSIUS - AMBIENT_TEMP_CELSIUS
        wasted_energy_joules = mass_g * profile.specific_heat_j_g_c * delta_t
        wasted_energy_kwh = wasted_energy_joules * JOULES_TO_KWH

        gross_energy_kwh = 0.0
        net_energy_kwh = gross_energy_kwh - wasted_energy_kwh  # negative

        breakdown = EnergyBreakdown(
            bio_oil_liters=0.0,
            syngas_kwh=0.0,
            char_kg=round(req.weight_kg * profile.char_frac, 2),  # 100% inert residue
            total_kwh=round(net_energy_kwh, 2),
            yield_efficiency_pct=0.0,
        )
        thermal_classification = "inert_heat_sink"
        disposition_route = "Thermal Energy Recovery (net energy consumer -- inert heat sink)"
        # NEGATIVE, not zero. Heating an inert mass to 500C draws grid
        # power, and that power carries the grid's own carbon intensity.
        # Reporting 0.0 here would silently hide a real emission and let
        # a glass-heavy cycle look carbon-neutral when it is not.
        co2_avoided_kg = -(wasted_energy_kwh * GRID_EMISSION_FACTOR_KG_PER_KWH)

    else:
        # --- Combustible (PVC, Polystyrene): E_rec = M x LHV x eta ---
        gross_energy_mj = req.weight_kg * profile.lhv_mj_kg * PYROLYSIS_EFFICIENCY
        gross_energy_kwh = gross_energy_mj * MJ_TO_KWH
        wasted_energy_kwh = 0.0
        net_energy_kwh = gross_energy_kwh

        oil_mass_kg = req.weight_kg * profile.oil_frac
        gas_mass_kg = req.weight_kg * profile.gas_frac
        char_mass_kg = req.weight_kg * profile.char_frac

        weighted = (
            oil_mass_kg * _STREAM_WEIGHTS["oil"]
            + gas_mass_kg * _STREAM_WEIGHTS["gas"]
            + char_mass_kg * _STREAM_WEIGHTS["char"]
        ) or 1.0
        gas_share = (gas_mass_kg * _STREAM_WEIGHTS["gas"]) / weighted
        syngas_kwh = net_energy_kwh * gas_share
        bio_oil_liters = oil_mass_kg / PYROLYSIS_OIL_DENSITY_KG_PER_L

        breakdown = EnergyBreakdown(
            bio_oil_liters=round(bio_oil_liters, 2),
            syngas_kwh=round(syngas_kwh, 2),
            char_kg=round(char_mass_kg, 2),
            total_kwh=round(net_energy_kwh, 2),
            yield_efficiency_pct=round(PYROLYSIS_EFFICIENCY * 100, 1),
        )
        thermal_classification = "combustible"
        disposition_route = "Pyrolysis Processing"
        co2_avoided_kg = net_energy_kwh * GRID_EMISSION_FACTOR_KG_PER_KWH

    return DispositionResponse(
        waste_type=req.waste_type,
        weight_kg=req.weight_kg,
        is_recyclable=False,
        disposition_route=disposition_route,
        disposition_method="thermal_recovery" if profile.is_heat_sink else "pyrolysis",
        dispatch_note=None,
        thermal_classification=thermal_classification,
        # NOT pre-rounded. These values are summed across a whole cycle in
        # the manifest, and rounding each batch to 2 dp first compounds:
        # 100 identical 7 kg PP batches drift 0.33 kWh from the true total.
        # Rounding belongs at the point of display, once.
        energy_recovery_kwh=net_energy_kwh,
        energy_breakdown=breakdown,          # display-only, rounded is fine
        gross_energy_kwh=gross_energy_kwh,
        wasted_energy_kwh=wasted_energy_kwh,
        lhv_mj_kg=profile.lhv_mj_kg,
        process_efficiency=PYROLYSIS_EFFICIENCY,
        landfill_diverted=True,
        co2_avoided_kg=co2_avoided_kg,
        manifest_id=manifest_id,
        timestamp=now_iso,
        facility_name=req.facility_name or "Urban Recycling Facility",
        nearest_treatment_facility=FacilityMatch(
            name=facility.name,
            facility_type=facility.facility_type,
            latitude=facility.latitude,
            longitude=facility.longitude,
            distance_km=distance_km,
            feed_in_tariff_lkr_per_kwh=facility.feed_in_tariff_lkr_per_kwh,
        ),
        # Waste streams no longer carry a monetary figure. Revenue is
        # reported for metal sales only, so "total value" on the manifest
        # means one unambiguous thing. Waste is accounted for in tonnage,
        # energy and CO2 instead.
        estimated_revenue_usd=None,
        estimated_revenue_lkr=None,
        fx=FXInfo(**fx),
    )
