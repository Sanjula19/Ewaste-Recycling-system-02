"""
services/manifest_service.py
-------------------------------
Tracks every forecast/disposition decision made since the last reset, and
renders the "End-of-Cycle Tonnage Manifest & Disposal Invoice" PDF your
proposal describes for Stage C (bin-full lockout -> auto-generated
manifest -> 100% landfill-diversion audit trail).

Storage: a simple in-memory list, good enough for a demo/panel deployment
and for a single-process dev server. It is NOT persistent across restarts
or safe across multiple worker processes -- see README for the two
realistic upgrade paths (SQLite file, or a Postgres table) before this
goes in front of an actual municipal council on a real server.
"""

from __future__ import annotations
import io
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


@dataclass
class LedgerEntry:
    kind: Literal["forecast", "disposition"]
    manifest_id: str
    material: str
    weight_kg: float
    route_or_recommendation: str
    energy_kwh: float
    value_lkr: float
    co2_avoided_kg: float
    timestamp: str
    # Which of the four outcomes this batch actually took. The receipt
    # groups by this; deriving it from the free-text route string would
    # mean parsing prose, which breaks the moment the wording changes.
    stream: Literal["metal_sale", "metal_hold", "pyrolysis", "mechanical"] = "pyrolysis"
    unit_price_lkr: float = 0.0        # metals only -- price per kg at time of sale
    destination: str = ""              # facility this batch was dispatched to


@dataclass
class Cycle:
    cycle_id: int
    status: Literal["open", "closed"]
    started_at: str
    closed_at: str | None = None
    entries: list[LedgerEntry] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_cycles: list[Cycle] = [Cycle(cycle_id=1, status="open", started_at=_now_iso())]


def _current_cycle() -> Cycle:
    return _cycles[-1]


def _find_cycle(cycle_id: int | None) -> Cycle:
    if cycle_id is None:
        return _current_cycle()
    for c in _cycles:
        if c.cycle_id == cycle_id:
            return c
    raise KeyError(f"No such manifest cycle: {cycle_id}")


def log_forecast(resp) -> None:
    sold = resp.recommendation == "SELL NOW"
    _current_cycle().entries.append(
        LedgerEntry(
            kind="forecast",
            manifest_id=f"FC-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}",
            material=resp.metal,
            weight_kg=resp.weight_kg,
            route_or_recommendation=f"{resp.recommendation} ({resp.operator_action})",
            energy_kwh=0.0,
            # Only a SELL is realised money. A HOLD batch is compacted and
            # still sitting in the yard -- counting its notional value as
            # revenue would overstate what the cycle actually earned.
            value_lkr=(resp.profit_if_sell_lkr or 0.0) if sold else 0.0,
            co2_avoided_kg=0.0,
            timestamp=_now_iso(),
            stream="metal_sale" if sold else "metal_hold",
            unit_price_lkr=resp.unit_price_lkr,
            destination="Market liquidation bin" if sold else "Compaction bay (feedstock blocks)",
        )
    )


def log_disposition(resp) -> None:
    method = getattr(resp, "disposition_method", "pyrolysis")
    _current_cycle().entries.append(
        LedgerEntry(
            kind="disposition",
            manifest_id=resp.manifest_id,
            material=resp.waste_type,
            weight_kg=resp.weight_kg,
            route_or_recommendation=resp.disposition_route,
            energy_kwh=resp.energy_recovery_kwh,
            value_lkr=0.0,      # waste streams carry no monetary figure
            co2_avoided_kg=resp.co2_avoided_kg,
            timestamp=resp.timestamp,
            stream="mechanical" if method == "mechanical" else "pyrolysis",
            destination=(
                resp.nearest_treatment_facility.name
                if resp.nearest_treatment_facility else ""
            ),
        )
    )


def summary(cycle_id: int | None = None) -> dict:
    """
    Cycle totals. Every figure is accumulated at full precision and
    rounded once at the end -- summing already-rounded per-entry values
    compounds their error across a long cycle.

    Energy and CO2 are split into recovered/avoided versus consumed/
    emitted. Contaminated glass is a net energy CONSUMER, so netting it
    silently against the pyrolysis credits would understate both sides
    and hide the fact that a glass-heavy cycle costs grid power.
    """
    cycle = _find_cycle(cycle_id)
    entries = cycle.entries

    total_weight = sum(e.weight_kg for e in entries)

    # Split rather than net, so both directions stay visible.
    energy_recovered = sum(e.energy_kwh for e in entries if e.energy_kwh > 0)
    energy_consumed = -sum(e.energy_kwh for e in entries if e.energy_kwh < 0)
    co2_avoided = sum(e.co2_avoided_kg for e in entries if e.co2_avoided_kg > 0)
    co2_emitted = -sum(e.co2_avoided_kg for e in entries if e.co2_avoided_kg < 0)

    # Value means realised metal sales, nothing else.
    total_value_lkr = sum(e.value_lkr for e in entries if e.stream == "metal_sale")

    def stream_weight(name: str) -> float:
        return sum(e.weight_kg for e in entries if e.stream == name)

    return {
        "cycle_id": cycle.cycle_id,
        "status": cycle.status,
        "started_at": cycle.started_at,
        "closed_at": cycle.closed_at,
        "batch_count": len(entries),
        "total_weight_kg": round(total_weight, 2),
        "total_energy_recovered_kwh": round(energy_recovered, 2),
        "total_energy_consumed_kwh": round(energy_consumed, 2),
        "net_energy_kwh": round(energy_recovered - energy_consumed, 2),
        "total_value_lkr": round(total_value_lkr, 2),
        "total_co2_avoided_kg": round(co2_avoided, 2),
        "total_co2_emitted_kg": round(co2_emitted, 2),
        "net_co2_avoided_kg": round(co2_avoided - co2_emitted, 2),
        "stream_weights_kg": {
            "metal_sale": round(stream_weight("metal_sale"), 2),
            "metal_hold": round(stream_weight("metal_hold"), 2),
            "pyrolysis": round(stream_weight("pyrolysis"), 2),
            "mechanical": round(stream_weight("mechanical"), 2),
        },
        "landfill_diversion_rate_pct": 100.0 if entries else 0.0,
        "entries": [e.__dict__ for e in entries],
    }


def list_cycles() -> list[dict]:
    result = []
    for c in reversed(_cycles):
        total_weight = sum(e.weight_kg for e in c.entries)
        total_value_lkr = sum(e.value_lkr for e in c.entries)
        result.append(
            {
                "cycle_id": c.cycle_id,
                "status": c.status,
                "batch_count": len(c.entries),
                "total_weight_kg": round(total_weight, 2),
                "total_value_lkr": round(total_value_lkr, 2),
                "started_at": c.started_at,
                "closed_at": c.closed_at,
            }
        )
    return result


def reset() -> dict:
    current = _current_cycle()
    n = len(current.entries)
    current.status = "closed"
    current.closed_at = _now_iso()
    new_cycle = Cycle(cycle_id=current.cycle_id + 1, status="open", started_at=_now_iso())
    _cycles.append(new_cycle)
    return {"cleared_entries": n, "closed_cycle_id": current.cycle_id, "new_cycle_id": new_cycle.cycle_id}


def generate_pdf(facility_name: str = "Urban Recycling Facility", cycle_id: int | None = None) -> bytes:
    """
    The End-of-Cycle Tonnage Manifest & Disposal Invoice -- an itemised
    receipt of what left the facility and where it went, grouped by the
    four outcomes a batch can have: metal sold, metal held back, waste
    pyrolysed, waste mechanically recycled.

    Layout lives in services/_receipt_pdf.py; this function's job is
    only to hand it the right cycle and its totals.
    """
    from services import _receipt_pdf

    cycle = _find_cycle(cycle_id)
    return _receipt_pdf.render(
        cycle=cycle,
        s=summary(cycle_id),
        facility_name=facility_name,
        generated_at=_now_iso(),
    )


