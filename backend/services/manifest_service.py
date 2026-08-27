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
    _current_cycle().entries.append(
        LedgerEntry(
            kind="forecast",
            manifest_id=f"FC-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}",
            material=resp.metal,
            weight_kg=resp.weight_kg,
            route_or_recommendation=f"{resp.recommendation} ({resp.operator_action})",
            energy_kwh=0.0,
            value_lkr=resp.profit_if_sell_lkr or 0.0,
            co2_avoided_kg=0.0,
            timestamp=_now_iso(),
        )
    )


def log_disposition(resp) -> None:
    _current_cycle().entries.append(
        LedgerEntry(
            kind="disposition",
            manifest_id=resp.manifest_id,
            material=resp.waste_type,
            weight_kg=resp.weight_kg,
            route_or_recommendation=resp.disposition_route,
            energy_kwh=resp.energy_recovery_kwh,
            value_lkr=resp.estimated_revenue_lkr or 0.0,
            co2_avoided_kg=resp.co2_avoided_kg,
            timestamp=resp.timestamp,
        )
    )


def summary(cycle_id: int | None = None) -> dict:
    cycle = _find_cycle(cycle_id)
    entries = cycle.entries
    total_weight = sum(e.weight_kg for e in entries)
    total_energy = sum(e.energy_kwh for e in entries)
    total_value_lkr = sum(e.value_lkr for e in entries)
    total_co2 = sum(e.co2_avoided_kg for e in entries)
    return {
        "cycle_id": cycle.cycle_id,
        "status": cycle.status,
        "batch_count": len(entries),
        "total_weight_kg": round(total_weight, 2),
        "total_energy_recovered_kwh": round(total_energy, 2),
        "total_value_lkr": round(total_value_lkr, 2),
        "total_co2_avoided_kg": round(total_co2, 2),
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
    cycle = _find_cycle(cycle_id)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="End-of-Cycle Tonnage Manifest")
    styles = getSampleStyleSheet()
    elements = []

    cycle_label = f"Cycle #{cycle.cycle_id} — {'Closed' if cycle.status == 'closed' else 'Open (current)'}"
    elements.append(Paragraph("End-of-Cycle Tonnage Manifest &amp; Disposal Invoice", styles["Title"]))
    elements.append(Paragraph(f"Facility: {facility_name}", styles["Normal"]))
    elements.append(Paragraph(cycle_label, styles["Normal"]))
    elements.append(
        Paragraph(
            f"Generated: {_now_iso()}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 8 * mm))

    s = summary(cycle_id)
    stats_table = Table(
        [
            ["Batches processed", str(s["batch_count"])],
            ["Total tonnage (kg)", f"{s['total_weight_kg']:,}"],
            ["Total energy recovered (kWh)", f"{s['total_energy_recovered_kwh']:,}"],
            ["Total estimated value (LKR)", f"{s['total_value_lkr']:,}"],
            ["Total CO2 avoided (kg)", f"{s['total_co2_avoided_kg']:,}"],
            ["Landfill diversion rate", f"{s['landfill_diversion_rate_pct']:.0f}%"],
        ],
        colWidths=[90 * mm, 60 * mm],
    )
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(stats_table)
    elements.append(Spacer(1, 8 * mm))

    elements.append(Paragraph("Batch Detail", styles["Heading2"]))
    cell_style = styles["Normal"].clone("cell")
    cell_style.fontSize = 7.5
    cell_style.leading = 9

    def cell(text: str) -> Paragraph:
        return Paragraph(str(text), cell_style)

    rows = [["Manifest / Ref ID", "Material", "Weight (kg)", "Route / Rec.", "Energy (kWh)", "Value (LKR)"]]
    for e in cycle.entries:
        rows.append(
            [cell(e.manifest_id), cell(e.material), cell(f"{e.weight_kg:g}"),
             cell(e.route_or_recommendation), cell(f"{e.energy_kwh:g}"), cell(f"{e.value_lkr:,.2f}")]
        )
    if len(rows) == 1:
        rows.append([cell("-"), cell("-"), cell("-"), cell("No batches logged this cycle"), cell("-"), cell("-")])

    detail_table = Table(rows, colWidths=[32 * mm, 28 * mm, 18 * mm, 48 * mm, 20 * mm, 24 * mm])
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]
        )
    )
    elements.append(detail_table)

    doc.build(elements)
    return buf.getvalue()
