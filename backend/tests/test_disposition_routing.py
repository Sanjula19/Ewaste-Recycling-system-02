"""
Strategic disposition: material scope and facility routing.

Two kinds of test here, deliberately kept apart:

  * Rule tests run against a SYNTHETIC register written to a temp file.
    They prove the routing rules hold in general -- an unconfirmed
    facility is never recommended, an uncoordinated one is excluded, a
    pyrolysis plant outranks an incinerator for polymers. Pinning these
    to the shipped register would make them restate today's data gaps
    instead of the rules, and they would start passing for the wrong
    reason the moment a coordinate is filled in.

  * Shipped-register tests assert what backend/data/facilities.json
    actually supports right now, so the two known gaps (INSEE has no
    coordinates; neither recycler has a source) fail loudly if someone
    believes they were fixed when they were not.
"""

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from materials_db import GLASS_REJECTION, is_glass, resolve_material  # noqa: E402
from schemas import DispositionRequest  # noqa: E402
from services import facility_service  # noqa: E402
from services.disposition_service import calculate_disposition  # noqa: E402


# --------------------------------------------------------------- fixtures

def _facility(**over):
    base = dict(
        id="x", name="X", operator="Op", town="T", district="D",
        latitude=6.9, longitude=79.9, technology="pyrolysis", accepts=["polystyrene"],
        exports_electricity=False, tariff_lkr_per_kwh=None, status="operational",
        source_url="https://example.invalid", coordinates_source="test",
        last_verified="2026-10-09",
    )
    base.update(over)
    return base


@pytest.fixture
def synthetic_register(tmp_path, monkeypatch):
    """
    A register that exercises every branch:
      pyro-near   pyrolysis, operational, coordinated   -> the recommendation
      pyro-nocoord pyrolysis, operational, NO coords    -> excluded
      wte-far     incineration, operational             -> the alternative
      wte-close   incineration, UNCONFIRMED, nearer     -> must not win it
      mech-far    mechanical, operational               -> PVC recommendation
      mech-close  mechanical, UNCONFIRMED, nearer       -> must not win it
    """
    doc = {"facilities": [
        _facility(id="pyro-near", name="Pyro Near", technology="pyrolysis",
                  latitude=7.0, longitude=79.9),
        _facility(id="pyro-nocoord", name="Pyro Nowhere", technology="pyrolysis",
                  latitude=None, longitude=None, coordinates_source="TODO"),
        _facility(id="wte-far", name="WTE Far", technology="incineration_wte",
                  latitude=8.0, longitude=79.9, exports_electricity=True,
                  tariff_lkr_per_kwh=37.1),
        _facility(id="wte-close", name="WTE Close", technology="incineration_wte",
                  latitude=6.95, longitude=79.87, status="unconfirmed",
                  exports_electricity=True, tariff_lkr_per_kwh=12.0),
        _facility(id="mech-far", name="Mech Far", technology="mechanical_recycling",
                  latitude=7.5, longitude=79.9, accepts=["pvc"]),
        _facility(id="mech-close", name="Mech Close", technology="mechanical_recycling",
                  latitude=6.94, longitude=79.87, status="unconfirmed", accepts=["pvc"]),
    ]}
    path = tmp_path / "facilities.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(facility_service, "FACILITIES_PATH", str(path))
    facility_service.clear_cache()
    yield
    facility_service.clear_cache()


@pytest.fixture(autouse=True)
def pinned_fx(monkeypatch):
    """No network in tests, and a fixed rate keeps assertions stable."""
    from services import fx_service
    monkeypatch.setattr(fx_service, "get_fx_rates", lambda: {
        "usd_lkr": 300.0, "usd_inr": 90.0,
        "as_of": "2026-01-01T00:00:00Z", "source": "fallback"})


@pytest.fixture(autouse=True)
def colombo_origin(monkeypatch):
    monkeypatch.setenv("DEFAULT_LOCAL_AUTHORITY", "Colombo")


def _dispose(material, weight=10.0, **kw):
    return calculate_disposition(
        DispositionRequest(waste_type=material, weight_kg=weight, **kw))


# ------------------------------------------------------- A. glass rejected

@pytest.mark.parametrize("name", [
    "glass", "Glass", "GLASS", "contaminated glass", "Contaminated Glass",
    "contaminated_glass", "  contaminated   glass  ", "mixed glass",
    "waste glass", "glass (contaminated)",
])
def test_glass_is_rejected_under_every_naming_variant(name):
    with pytest.raises(KeyError) as exc:
        resolve_material(name)
    assert exc.value.args[0] == GLASS_REJECTION


def test_glass_rejection_message_names_the_right_destination():
    assert "glass recycler" in GLASS_REJECTION
    assert "outside the scope of strategic disposition" in GLASS_REJECTION


def test_glass_rejected_by_the_disposition_endpoint_with_400():
    from fastapi import HTTPException
    from routers.disposition import get_disposition
    with pytest.raises(HTTPException) as exc:
        get_disposition(DispositionRequest(waste_type="Contaminated Glass", weight_kg=10))
    assert exc.value.status_code == 400
    # args[0], not str(exc) -- the detail must not arrive re-quoted.
    assert exc.value.detail == GLASS_REJECTION
    assert not exc.value.detail.startswith("'")


def test_glass_detector_does_not_over_match_in_scope_materials():
    for ok in ["pvc", "pvc plastic", "polystyrene", "pp", "polypropylene",
               "copper", "aluminium", "steel", "lead", "zinc", "nickel"]:
        assert not is_glass(ok)


def test_glass_is_gone_from_the_material_table():
    from materials_db import NON_RECYCLABLES
    assert not any("glass" in k for k in NON_RECYCLABLES)


def test_heat_sink_model_and_its_constants_are_gone():
    import materials_db
    for name in ("PYROLYSIS_TEMP_CELSIUS", "AMBIENT_TEMP_CELSIUS", "JOULES_TO_KWH"):
        assert not hasattr(materials_db, name), f"{name} should have been removed"
    from materials_db import MaterialProfile
    for field in ("is_heat_sink", "specific_heat_j_g_c", "density_g_cc"):
        assert field not in MaterialProfile.__dataclass_fields__


def test_no_material_can_produce_negative_energy():
    for material in ("polystyrene", "pp", "polypropylene", "pvc", "pvc plastic"):
        r = _dispose(material)
        assert r.energy_recovery_kwh >= 0
        assert r.co2_avoided_kg >= 0


# --------------------------------- B/C. pyrolysis recommended, WtE alternative

def test_polymer_recommends_pyrolysis_with_incineration_alternative(synthetic_register):
    for material in ("polystyrene", "pp"):
        r = _dispose(material)
        assert r.recommended_facility is not None, r.recommendation_blocked_reason
        assert r.recommended_facility.id == "pyro-near"
        assert r.recommended_facility.technology == "pyrolysis"
        assert r.alternative_facility is not None
        assert r.alternative_facility.technology == "incineration_wte"


def test_recommendation_carries_everything_a_dispatch_note_needs(synthetic_register):
    f = _dispose("polystyrene").recommended_facility
    for attr in ("name", "operator", "town", "technology", "status",
                 "distance_km", "source_url"):
        assert getattr(f, attr) is not None, attr
    assert f.distance_km > 0


def test_unconfirmed_is_never_recommended_even_when_nearest(synthetic_register):
    """WTE Close and Mech Close are nearer than their operational rivals."""
    poly = _dispose("polystyrene")
    assert poly.recommended_facility.status == "operational"
    assert poly.alternative_facility.id == "wte-far", \
        "the unconfirmed-but-nearer incinerator must not take the alternative slot " \
        "while an operational one exists"

    pvc = _dispose("pvc")
    assert pvc.recommended_facility is not None, pvc.recommendation_blocked_reason
    assert pvc.recommended_facility.id == "mech-far"
    assert pvc.recommended_facility.status == "operational"


def test_unconfirmed_may_still_appear_as_an_alternative(synthetic_register):
    """Flagged, so the option is visible without being vouched for."""
    pvc = _dispose("pvc")
    assert pvc.alternative_facility is not None
    assert pvc.alternative_facility.id == "mech-close"
    assert pvc.alternative_facility.status == "unconfirmed"
    assert pvc.alternative_facility.unconfirmed is True


def test_null_coordinate_facility_is_excluded_and_reported(synthetic_register):
    r = _dispose("polystyrene")
    excluded_ids = {x.id for x in r.facilities_excluded}
    assert "pyro-nocoord" in excluded_ids
    assert "pyro-near" not in excluded_ids
    reason = next(x.reason for x in r.facilities_excluded if x.id == "pyro-nocoord")
    assert "coordinates" in reason.lower()
    # Excluded, not merely ranked last.
    assert r.recommended_facility.id != "pyro-nocoord"
    assert (r.alternative_facility or r.recommended_facility).id != "pyro-nocoord"


def test_pvc_routes_to_mechanical_recycling_only(synthetic_register):
    r = _dispose("pvc")
    assert r.disposition_method == "mechanical"
    assert r.disposition_route == "Mechanical Recycling"
    assert r.recommended_facility.technology == "mechanical_recycling"
    # PVC is deliberately kept out of combustion: neither slot may be thermal.
    for slot in (r.recommended_facility, r.alternative_facility):
        if slot is not None:
            assert slot.technology == "mechanical_recycling"
    assert r.energy_recovery_kwh == 0.0
    assert r.pyrolysis_products is None


def test_pvc_and_pvc_plastic_resolve_the_same_way(synthetic_register):
    a, b = _dispose("pvc"), _dispose("pvc plastic")
    assert a.recommended_facility.id == b.recommended_facility.id
    assert a.disposition_method == b.disposition_method == "mechanical"


# --------------------------------------------------- C. origin / local authority

def test_origin_defaults_to_the_configured_local_authority(synthetic_register):
    r = _dispose("polystyrene")
    assert r.origin.name == "Colombo"
    assert r.origin.source == "default"


def test_named_local_authority_is_used(synthetic_register):
    r = _dispose("polystyrene", local_authority="Jaffna")
    assert r.origin.name == "Jaffna"
    assert r.origin.source == "local_authority"


def test_explicit_coordinates_override_the_local_authority(synthetic_register):
    r = _dispose("polystyrene", local_authority="Jaffna",
                 latitude=6.9271, longitude=79.8612)
    assert r.origin.source == "request_override"
    assert r.origin.latitude == pytest.approx(6.9271)


def test_unknown_local_authority_falls_back_rather_than_failing(synthetic_register):
    r = _dispose("polystyrene", local_authority="Atlantis")
    assert r.origin.source == "default"
    assert r.recommended_facility is not None


def test_distance_grows_with_a_more_distant_origin(synthetic_register):
    near = _dispose("polystyrene", local_authority="Colombo")
    far = _dispose("polystyrene", local_authority="Jaffna")
    assert far.recommended_facility.distance_km > near.recommended_facility.distance_km


# ------------------------------------------------------ D. energy / value / CO2

def test_energy_follows_m_lhv_eta(synthetic_register):
    from materials_db import MJ_TO_KWH, NON_RECYCLABLES, PYROLYSIS_EFFICIENCY
    for material in ("polystyrene", "pp"):
        lhv = NON_RECYCLABLES[material].lhv_mj_kg
        r = _dispose(material, weight=10.0)
        assert r.energy_recovery_kwh == pytest.approx(
            10.0 * lhv * PYROLYSIS_EFFICIENCY * MJ_TO_KWH)


def test_pyrolysis_reports_products_and_no_estimated_value(synthetic_register):
    r = _dispose("polystyrene", weight=10.0)
    p = r.pyrolysis_products
    assert (p.oil_pct, p.gas_pct, p.char_pct) == (45.0, 30.0, 25.0)
    assert p.bio_oil_kg == pytest.approx(4.5)
    assert p.syngas_kg == pytest.approx(3.0)
    assert p.char_kg == pytest.approx(2.5)
    assert p.value == "not estimated"


def test_pyrolysis_destination_reports_no_electricity_and_no_grid_co2(synthetic_register):
    r = _dispose("polystyrene")
    assert r.recommended_facility.technology == "pyrolysis"
    assert r.electricity.reported is False
    assert r.electricity.value_lkr is None
    assert r.electricity.grid_co2_avoided_kg is None
    assert r.co2_avoided_kg == 0.0
    assert "does not export electricity" in r.electricity.not_reported_reason


def test_electricity_value_is_reported_for_an_exporter_with_a_sourced_tariff(tmp_path, monkeypatch):
    """Only an exporting plant WITH a tariff gets a value and a CO2 figure."""
    doc = {"facilities": [
        _facility(id="wte", name="WTE", technology="incineration_wte",
                  latitude=6.95, longitude=79.87, exports_electricity=True,
                  tariff_lkr_per_kwh=37.1),
    ]}
    path = tmp_path / "f.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(facility_service, "FACILITIES_PATH", str(path))
    facility_service.clear_cache()

    from materials_db import GRID_EMISSION_FACTOR_KG_PER_KWH
    r = _dispose("polystyrene", weight=10.0)
    e = r.electricity
    assert e.reported is True
    assert e.tariff_lkr_per_kwh == 37.1
    assert e.value_lkr == pytest.approx(round(r.energy_recovery_kwh * 37.1, 2))
    assert e.grid_co2_avoided_kg == pytest.approx(
        round(r.energy_recovery_kwh * GRID_EMISSION_FACTOR_KG_PER_KWH, 2))
    assert r.co2_avoided_kg == e.grid_co2_avoided_kg
    # The label must not let a council read this as income.
    assert "not paid to the council" in e.label
    facility_service.clear_cache()


def test_exporter_without_a_sourced_tariff_reports_neither_value_nor_co2(tmp_path, monkeypatch):
    doc = {"facilities": [
        _facility(id="wte", name="WTE No Tariff", technology="incineration_wte",
                  latitude=6.95, longitude=79.87, exports_electricity=True,
                  tariff_lkr_per_kwh=None),
    ]}
    path = tmp_path / "f.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(facility_service, "FACILITIES_PATH", str(path))
    facility_service.clear_cache()
    r = _dispose("polystyrene")
    assert r.electricity.reported is False
    assert r.electricity.value_lkr is None
    assert r.co2_avoided_kg == 0.0
    assert "no feed-in tariff" in r.electricity.not_reported_reason
    facility_service.clear_cache()


def test_mechanical_reports_no_energy_value_or_co2(synthetic_register):
    r = _dispose("pvc")
    assert r.energy_recovery_kwh == 0.0
    assert r.co2_avoided_kg == 0.0
    assert r.electricity.reported is False
    assert "no combustion" in r.electricity.not_reported_reason


def test_revenue_fields_stay_none_but_present_for_the_firmware_contract(synthetic_register):
    """routers/iot.py reads estimated_revenue_lkr into the compact payload."""
    for material in ("polystyrene", "pvc"):
        r = _dispose(material)
        assert "estimated_revenue_lkr" in r.model_dump()
        assert r.estimated_revenue_lkr is None
        assert r.estimated_revenue_usd is None


# ------------------------------------------- shipped register, as it stands

def test_shipped_register_parses_and_every_entry_is_complete():
    facility_service.clear_cache()
    facilities = facility_service.load_facilities()
    assert len(facilities) == 5
    for f in facilities:
        assert f.id and f.name and f.operator and f.town and f.district
        assert f.technology in ("pyrolysis", "incineration_wte", "mechanical_recycling")
        assert f.status in ("operational", "unconfirmed")
        assert f.coordinates_source
        assert f.last_verified
        # A tariff may only exist where electricity is exported.
        if f.tariff_lkr_per_kwh is not None:
            assert f.exports_electricity, f"{f.name} has a tariff but exports nothing"


def test_shipped_register_holds_only_the_approved_facilities():
    facility_service.clear_cache()
    assert {f.id for f in facility_service.load_facilities()} == {
        "insee-ecocycle-puttalam-pyrolysis",
        "kerawalapitiya-wte",
        "karadiyana-wte",
        "ciyasa-plastics-kaduwela",
        "negombo-recycling-club-hub",
    }


def test_shipped_insee_is_routable():
    """
    INSEE's coordinates were supplied on 2026-10-09, which is what makes
    the pyrolysis recommendation work against the real register. This
    guards them: a coordinate silently reverting to null would quietly
    turn every polymer recommendation back into an incinerator fallback,
    which is a routing change nobody would see in a diff of a results file.
    """
    facility_service.clear_cache()
    insee = next(f for f in facility_service.load_facilities()
                 if f.id == "insee-ecocycle-puttalam-pyrolysis")
    assert insee.has_coordinates, "INSEE lost its coordinates"
    assert insee.coordinates_source != "TODO"
    assert insee.status == "operational"
    assert insee.source_url and insee.source_url.startswith("https://")
    # Inside Sri Lanka, and in the right district -- catches a lat/lon
    # swap, which would otherwise land the plant in the Indian Ocean.
    assert 5.0 < insee.latitude < 10.5, insee.latitude
    assert 79.0 < insee.longitude < 82.5, insee.longitude
    assert insee.district == "Puttalam"


def test_shipped_register_recommends_pyrolysis_for_polymers():
    """The real register, not the synthetic one."""
    facility_service.clear_cache()
    for material in ("polystyrene", "polypropylene"):
        r = _dispose(material)
        assert r.recommended_facility is not None, r.recommendation_blocked_reason
        assert r.recommended_facility.id == "insee-ecocycle-puttalam-pyrolysis"
        assert r.recommended_facility.technology == "pyrolysis"
        assert r.recommendation_blocked_reason is None
        # Pyrolysis exports no electricity, so no value and no grid CO2.
        assert r.electricity.reported is False
        assert r.co2_avoided_kg == 0.0
        # Nothing is excluded any more: every shipped facility has a coordinate.
        assert r.facilities_excluded == []
        assert r.alternative_facility.id == "kerawalapitiya-wte"
        assert r.alternative_facility.technology == "incineration_wte"


def test_shipped_register_still_blocks_pvc():
    """
    Both mechanical recyclers remain unconfirmed -- neither has a source
    URL on the register -- so PVC gets a flagged alternative and no
    recommendation. Fails once a source is supplied and one is promoted to
    operational, which is the intended next change.
    """
    facility_service.clear_cache()
    pvc = _dispose("pvc")
    assert pvc.recommended_facility is None
    assert "unconfirmed" in pvc.recommendation_blocked_reason
    assert pvc.alternative_facility.unconfirmed is True


def test_no_shipped_facility_is_left_unroutable():
    facility_service.clear_cache()
    missing = [f.name for f in facility_service.load_facilities()
               if not f.has_coordinates]
    assert missing == [], f"no coordinates for: {missing}"


def test_shipped_local_authorities_all_carry_coordinates():
    facility_service.clear_cache()
    las = facility_service.load_local_authorities()
    assert len(las) == 43
    for la in las:
        assert la.latitude is not None and la.longitude is not None
        assert 5.0 < la.latitude < 10.5, la.name      # inside Sri Lanka
        assert 79.0 < la.longitude < 82.5, la.name
        assert la.coordinates_source
    assert facility_service.find_local_authority("Colombo") is not None
    assert facility_service.find_local_authority("colombo") is not None
    assert facility_service.find_local_authority("Atlantis") is None
