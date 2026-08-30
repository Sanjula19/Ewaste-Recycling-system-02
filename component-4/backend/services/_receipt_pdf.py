"""
services/_receipt_pdf.py
--------------------------
Rendering half of the End-of-Cycle Tonnage Manifest & Disposal Invoice.

Kept beside manifest_service rather than inside it because the ledger
(what happened) and the receipt (how it is presented) change for
different reasons -- re-styling the invoice should never risk touching
the audit record it is built from.

The receipt is grouped by LedgerEntry.stream, the structured field, not
by parsing the free-text route label. Re-wording a route can therefore
never silently mis-file a batch in an auditable document.
"""

from __future__ import annotations
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

_HEAD_BG = colors.HexColor("#0F3D3E")
_ALT_BG = colors.HexColor("#F3F5F1")
_MUTED = "#7C8A80"


def _plural(n: int) -> str:
    return f"{n} batch" if n == 1 else f"{n} batches"


def _stream_table(elements, styles, title: str, rows: list, widths: list, note: str = "") -> None:
    """One titled section. Prints an explicit 'nothing here' line when a
    stream is empty, so a reader can tell an empty stream from a missing
    section."""
    elements.append(Paragraph(title, styles["Heading3"]))
    if note:
        elements.append(Paragraph(
            f"<font size=7.5 color='#56645C'>{note}</font>", styles["Normal"]))

    if len(rows) <= 1:
        elements.append(Paragraph(
            f"<font size=8 color='{_MUTED}'>Nothing in this stream this cycle.</font>",
            styles["Normal"]))
        elements.append(Spacer(1, 4 * mm))
        return

    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, _ALT_BG]),
        # The final row is always the subtotal.
        ("BACKGROUND", (0, -1), (-1, -1), _ALT_BG),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, _HEAD_BG),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))


def render(cycle, s: dict, facility_name: str, generated_at: str) -> bytes:
    """`cycle` is a manifest_service.Cycle, `s` the matching summary()."""
    styles = getSampleStyleSheet()
    cell = styles["Normal"].clone("cell")
    cell.fontSize = 7.5
    cell.leading = 9

    def c(text) -> Paragraph:
        return Paragraph(str(text), cell)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title="End-of-Cycle Tonnage Manifest",
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    el: list = []

    # --- Header ---------------------------------------------------------
    el.append(Paragraph("End-of-Cycle Tonnage Manifest &amp; Disposal Invoice", styles["Title"]))
    status_label = "CLOSED" if cycle.status == "closed" else "OPEN (current)"
    el.append(Paragraph(f"<b>Facility:</b> {facility_name}", styles["Normal"]))
    el.append(Paragraph(f"<b>Cycle:</b> #{cycle.cycle_id} - {status_label}", styles["Normal"]))
    el.append(Paragraph(f"<b>Opened:</b> {cycle.started_at}", styles["Normal"]))
    if cycle.closed_at:
        el.append(Paragraph(f"<b>Closed:</b> {cycle.closed_at}", styles["Normal"]))
    el.append(Paragraph(f"<b>Generated:</b> {generated_at}", styles["Normal"]))
    el.append(Spacer(1, 6 * mm))

    # --- Cycle summary --------------------------------------------------
    sw = s["stream_weights_kg"]
    summary_rows = [
        ["Batches processed", str(s["batch_count"])],
        ["Total tonnage handled", f"{s['total_weight_kg']:,.2f} kg"],
        ["    metal sold", f"{sw['metal_sale']:,.2f} kg"],
        ["    metal held back", f"{sw['metal_hold']:,.2f} kg"],
        ["    sent to pyrolysis", f"{sw['pyrolysis']:,.2f} kg"],
        ["    mechanically recycled", f"{sw['mechanical']:,.2f} kg"],
        ["Energy recovered", f"{s['total_energy_recovered_kwh']:,.2f} kWh"],
        ["Energy consumed (inert heat sinks)", f"{s['total_energy_consumed_kwh']:,.2f} kWh"],
        ["Net energy", f"{s['net_energy_kwh']:,.2f} kWh"],
        ["CO2 avoided", f"{s['total_co2_avoided_kg']:,.2f} kg"],
        ["CO2 emitted", f"{s['total_co2_emitted_kg']:,.2f} kg"],
        ["Net CO2 avoided", f"{s['net_co2_avoided_kg']:,.2f} kg"],
        ["Revenue from metal sales", f"Rs. {s['total_value_lkr']:,.2f}"],
        ["Landfill diversion rate", f"{s['landfill_diversion_rate_pct']:.0f}%"],
    ]
    stats = Table(summary_rows, colWidths=[95 * mm, 55 * mm])
    stats.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _ALT_BG]),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    el.append(Paragraph("Cycle Summary", styles["Heading2"]))
    el.append(stats)
    el.append(Spacer(1, 6 * mm))

    entries = cycle.entries

    def of(stream: str) -> list:
        return [e for e in entries if e.stream == stream]

    # --- 1. Metals sold -------------------------------------------------
    sold = of("metal_sale")
    rows = [["Ref", "Metal", "Qty (kg)", "Unit price (Rs/kg)", "Value (Rs)"]]
    for e in sold:
        rows.append([c(e.manifest_id), c(e.material), c(f"{e.weight_kg:g}"),
                     c(f"{e.unit_price_lkr:,.2f}"), c(f"{e.value_lkr:,.2f}")])
    if sold:
        rows.append([c("<b>SUBTOTAL</b>"), c(f"<b>{_plural(len(sold))}</b>"),
                     c(f"<b>{sum(e.weight_kg for e in sold):,.2f}</b>"), c(""),
                     c(f"<b>{sum(e.value_lkr for e in sold):,.2f}</b>")])
    _stream_table(el, styles, "1. Metals Sold", rows,
                  [32 * mm, 30 * mm, 22 * mm, 32 * mm, 32 * mm],
                  "Routed to the market liquidation bin at the forecast SELL NOW price.")

    # --- 2. Metals held -------------------------------------------------
    held = of("metal_hold")
    rows = [["Ref", "Metal", "Qty (kg)", "Disposition"]]
    for e in held:
        rows.append([c(e.manifest_id), c(e.material), c(f"{e.weight_kg:g}"), c(e.destination)])
    if held:
        rows.append([c("<b>SUBTOTAL</b>"), c(f"<b>{_plural(len(held))}</b>"),
                     c(f"<b>{sum(e.weight_kg for e in held):,.2f}</b>"), c("")])
    _stream_table(el, styles, "2. Metals Held Back", rows,
                  [32 * mm, 30 * mm, 22 * mm, 64 * mm],
                  "Crushed and compacted into feedstock blocks awaiting a better price. "
                  "No revenue is recognised until these are actually sold.")

    # --- 3. Pyrolysis ---------------------------------------------------
    pyro = of("pyrolysis")
    rows = [["Ref", "Material", "Qty (kg)", "Energy (kWh)", "CO2 (kg)", "Destination plant"]]
    for e in pyro:
        rows.append([c(e.manifest_id), c(e.material), c(f"{e.weight_kg:g}"),
                     c(f"{e.energy_kwh:,.2f}"), c(f"{e.co2_avoided_kg:,.2f}"), c(e.destination)])
    if pyro:
        rows.append([c("<b>SUBTOTAL</b>"), c(f"<b>{_plural(len(pyro))}</b>"),
                     c(f"<b>{sum(e.weight_kg for e in pyro):,.2f}</b>"),
                     c(f"<b>{sum(e.energy_kwh for e in pyro):,.2f}</b>"),
                     c(f"<b>{sum(e.co2_avoided_kg for e in pyro):,.2f}</b>"), c("")])
    _stream_table(el, styles, "3. Waste Sent to Pyrolysis / Thermal Recovery", rows,
                  [30 * mm, 28 * mm, 18 * mm, 22 * mm, 20 * mm, 56 * mm],
                  "Negative energy and CO2 figures indicate an inert heat sink: the process "
                  "consumes grid power rather than yielding it.")

    # --- 4. Mechanical recycling ---------------------------------------
    mech = of("mechanical")
    rows = [["Ref", "Material", "Qty (kg)", "Destination recycler"]]
    for e in mech:
        rows.append([c(e.manifest_id), c(e.material), c(f"{e.weight_kg:g}"), c(e.destination)])
    if mech:
        rows.append([c("<b>SUBTOTAL</b>"), c(f"<b>{_plural(len(mech))}</b>"),
                     c(f"<b>{sum(e.weight_kg for e in mech):,.2f}</b>"), c("")])
    _stream_table(el, styles, "4. Waste Sent to Mechanical Recycling", rows,
                  [32 * mm, 30 * mm, 22 * mm, 64 * mm],
                  "Shredded, washed and granulated back into feedstock. No thermal "
                  "processing, so no energy or CO2 figures apply to this stream.")

    # --- Declaration ----------------------------------------------------
    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(
        f"<b>Declaration.</b> All {s['batch_count']} batches recorded in cycle "
        f"#{cycle.cycle_id} ({s['total_weight_kg']:,.2f} kg total) were routed to "
        f"resale, recycling or energy recovery. None was consigned to landfill, giving "
        f"a landfill diversion rate of {s['landfill_diversion_rate_pct']:.0f}% for this cycle.",
        styles["Normal"]))
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph(
        f"<font size=7 color='{_MUTED}'>Academic prototype -- Component 4, R26-IT-015. "
        "Prices are model forecasts against the last recorded market data; energy figures "
        "derive from published LHV and specific-heat values. All figures are estimates for "
        "demonstration and planning purposes.</font>", styles["Normal"]))

    doc.build(el)
    return buf.getvalue()
