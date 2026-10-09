"""
scripts/verify_disposition_routing.py
--------------------------------------
Exercises the facility register from every origin it knows about, and
writes the results where the paper can cite them.

    cd backend
    venv/Scripts/python.exe scripts/verify_disposition_routing.py

Outputs (new files; nothing in results_v3/ is modified):
    results_v3/routing_tests.csv     one row per origin x material
    results_v3/disposition_10kg.json a full 10 kg response per material

It also prints the Figure 5 representative hold out of
results_v3/run_meta.json, which it only reads.

FX is pinned to the offline fallback rate. This script must produce the
same numbers on a machine with no network as on one with, or it is not a
verification of anything.
"""

from __future__ import annotations

import csv
import json
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

RESULTS_DIR = os.path.join(BACKEND_DIR, "results_v3")
CSV_PATH = os.path.join(RESULTS_DIR, "routing_tests.csv")
JSON_PATH = os.path.join(RESULTS_DIR, "disposition_10kg.json")
RUN_META = os.path.join(RESULTS_DIR, "run_meta.json")
DECISIONS = os.path.join(RESULTS_DIR, "decisions_raw.csv")

MATERIALS = ["polystyrene", "polypropylene", "pvc"]
BATCH_KG = 10.0

# Central Colombo, the coordinate the old hardcoded register defaulted to.
# Passed as an explicit lat/lon override so it is tested as a coordinate,
# not as the "Colombo" local authority (which is a separate row).
CENTRAL_COLOMBO = (6.9271, 79.8612)

from services import fx_service  # noqa: E402

fx_service.get_fx_rates = lambda: {
    "usd_lkr": 300.0, "usd_inr": 90.0,
    "as_of": "2026-01-01T00:00:00Z", "source": "fallback",
}

from schemas import DispositionRequest  # noqa: E402
from services import facility_service  # noqa: E402
from services.disposition_service import calculate_disposition  # noqa: E402

FIELDS = [
    "origin", "origin_district", "origin_source", "origin_lat", "origin_lon",
    "material", "disposition_route",
    "recommended", "recommended_operator", "recommended_technology",
    "recommended_distance_km", "recommended_status",
    "alternative", "alternative_operator", "alternative_technology",
    "alternative_distance_km", "alternative_status", "alternative_unconfirmed",
    "excluded_count", "recommendation_blocked_reason",
]


def row_for(origin_label: str, material: str, req: DispositionRequest) -> dict:
    r = calculate_disposition(req)
    rec, alt = r.recommended_facility, r.alternative_facility
    return {
        "origin": origin_label,
        "origin_district": r.origin.district or "",
        "origin_source": r.origin.source,
        "origin_lat": round(r.origin.latitude, 4),
        "origin_lon": round(r.origin.longitude, 4),
        "material": material,
        "disposition_route": r.disposition_route,
        "recommended": rec.name if rec else "",
        "recommended_operator": rec.operator if rec else "",
        "recommended_technology": rec.technology if rec else "",
        "recommended_distance_km": rec.distance_km if rec else "",
        "recommended_status": rec.status if rec else "",
        "alternative": alt.name if alt else "",
        "alternative_operator": alt.operator if alt else "",
        "alternative_technology": alt.technology if alt else "",
        "alternative_distance_km": alt.distance_km if alt else "",
        "alternative_status": alt.status if alt else "",
        "alternative_unconfirmed": alt.unconfirmed if alt else "",
        "excluded_count": len(r.facilities_excluded),
        "recommendation_blocked_reason": r.recommendation_blocked_reason or "",
    }


def main() -> None:
    facility_service.clear_cache()
    authorities = facility_service.load_local_authorities()
    print(f"Register: {len(facility_service.load_facilities())} facilities, "
          f"{len(authorities)} local authorities\n")

    rows = []

    # 1. Central Colombo, by coordinate.
    for material in MATERIALS:
        rows.append(row_for(
            f"Central Colombo ({CENTRAL_COLOMBO[0]}, {CENTRAL_COLOMBO[1]})", material,
            DispositionRequest(waste_type=material, weight_kg=BATCH_KG,
                               latitude=CENTRAL_COLOMBO[0], longitude=CENTRAL_COLOMBO[1])))

    # 2. Every local authority on the register, by name.
    for la in authorities:
        for material in MATERIALS:
            rows.append(row_for(
                la.name, material,
                DispositionRequest(waste_type=material, weight_kg=BATCH_KG,
                                   local_authority=la.name)))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> results_v3/routing_tests.csv")

    # 3. A full 10 kg response per material, from the configured default.
    payloads = {}
    for material in MATERIALS:
        r = calculate_disposition(
            DispositionRequest(waste_type=material, weight_kg=BATCH_KG))
        payloads[material] = r.model_dump()

    # Glass must be refused, and the refusal is part of what this file
    # documents -- a reader should not have to take the removal on trust.
    from materials_db import resolve_material
    rejections = {}
    for name in ["Contaminated Glass", "glass", "contaminated_glass", "gold", "silver"]:
        try:
            resolve_material(name)
            rejections[name] = "NOT REJECTED -- BUG"
        except KeyError as exc:
            rejections[name] = exc.args[0]

    with open(JSON_PATH, "w", encoding="utf-8", newline="") as fh:
        json.dump({
            "generated_by": "scripts/verify_disposition_routing.py",
            "batch_kg": BATCH_KG,
            "origin": "DEFAULT_LOCAL_AUTHORITY from the environment",
            "fx": "pinned to the offline fallback (300 LKR/USD) for reproducibility",
            "rejected_materials": rejections,
            "dispositions": payloads,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {len(payloads)} dispositions -> results_v3/disposition_10kg.json")

    # 4. Figure 5's representative hold, read out of the evaluation run.
    print("\n--- Figure 5 representative hold (from results_v3/run_meta.json) ---")
    meta = json.load(open(RUN_META, encoding="utf-8"))
    fig5 = meta["fig5_example"]
    p0 = None
    with open(DECISIONS, encoding="utf-8", newline="") as fh:
        for d in csv.DictReader(fh):
            if d["metal"] == fig5["metal"] and d["date"] == fig5["date"]:
                p0 = float(d["p0"])
                break
    tau = fig5["tau_pct"] / 100.0
    print(f"  metal            : {fig5['metal']}")
    print(f"  decision date    : {fig5['date']}")
    print(f"  selected model   : {fig5['selected']}")
    print(f"  tau              : {fig5['tau_pct']:.4f} %")
    if p0 is not None:
        print(f"  P0               : {p0:.6f} USD/kg")
        print(f"  target p0(1+tau) : {p0 * (1 + tau):.6f} USD/kg")
    else:
        print("  P0               : not found in decisions_raw.csv")
    print(f"  realised gain    : {fig5['realised_gain_pct']:.4f} %")
    print(f"  days held        : {fig5['days_held']}")
    print(f"  target hit       : {fig5['target_hit']}")


if __name__ == "__main__":
    main()
