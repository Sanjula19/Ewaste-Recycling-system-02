"""
scripts/export_figures.py
-------------------------
Re-exports the paper figures from results_v3/ as SVG and 600 dpi PNG,
3.5 in wide, WITHOUT re-plotting anything.

    cd backend
    venv/Scripts/python.exe scripts/export_figures.py

WHY THIS CONVERTS INSTEAD OF RE-PLOTTING
The obvious route -- re-run evaluate_c4_v2.py --analysis-only with extra
savefig() calls -- would regenerate the figures, and regenerating is
exactly what "without changing the plots" rules out. It would also rewrite
every other file in results_v3/ as a side effect.

So this reads the existing PDFs as artwork and rasterises/transcodes them.
The drawing is whatever was committed; nothing here can move a tick label.

THE 3.5 IN REQUIREMENT IS ALREADY MET
All three PDFs are 252.00 pt wide = exactly 3.5 in, because
evaluate_c4_v2.py authored them at figsize=(3.5, h) with 8 pt serif type
for an IEEE single column. No scaling is applied -- a rescale is what
would shrink the 8 pt labels below legibility. 600 dpi x 3.5 in = 2100 px.

TEXT IS CONVERTED TO PATHS IN THE SVG
The PDFs embed Type 42 fonts (pdf.fonttype: 42). An SVG that merely names
"Times New Roman" renders differently wherever that font is missing --
which includes most Linux boxes and many journal pipelines. text_as_path
makes the SVG self-contained and pixel-faithful to the PDF, at the cost of
text no longer being selectable. For a figure going into a paper that is
the right trade; pass --svg-text to get selectable text instead.
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BACKEND_DIR, "results_v3")

FIGURES = ["fig4_holdout_steel", "fig5_hold_example", "fig6_sensitivity"]

TARGET_WIDTH_IN = 3.5
PT_PER_IN = 72.0
DPI = 600

# A hair of tolerance: 252.0 pt is exact here, but a figure re-authored at
# a slightly different size should warn rather than be silently rescaled.
WIDTH_TOLERANCE_PT = 0.5


def png_phys_dpi(path: str) -> tuple[float, float] | None:
    """
    Read the pHYs chunk back out of a PNG, in dots per inch.

    Worth verifying rather than trusting: a PNG carrying the right pixel
    count but no physical size lands at 96 dpi in Word and comes out
    roughly 22 in wide.
    """
    with open(path, "rb") as fh:
        if fh.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        while True:
            head = fh.read(8)
            if len(head) < 8:
                return None
            length, kind = struct.unpack(">I4s", head)
            data = fh.read(length)
            fh.read(4)  # CRC
            if kind == b"pHYs":
                x, y, unit = struct.unpack(">IIB", data)
                if unit != 1:          # 1 = metre
                    return None
                return (x * 0.0254, y * 0.0254)
            if kind == b"IEND":
                return None


def _unit_the_root(svg: str, w_pt: float, h_pt: float) -> str:
    """
    Put explicit `pt` units on the SVG root's width and height.

    MuPDF emits width="252" height="172.8" with no unit. A unitless SVG
    length is user units, which consumers treat as px -- so a 252-wide
    figure lands at 252 px = 2.625 in at 96 dpi, not the 3.5 in it was
    authored as. LaTeX's svg package, Inkscape and every browser read it
    that way.

    Only the two root attributes change. The viewBox is already in points
    and is left exactly as MuPDF wrote it, so the coordinate system and
    every path inside are untouched -- this fixes the declared physical
    size, not the drawing.
    """
    def fmt(v: float) -> str:
        return f"{v:g}"

    m = re.search(r"<svg\b[^>]*>", svg)
    if not m:
        return svg
    root = m.group(0)
    fixed = re.sub(r'\bwidth="[^"]*"', f'width="{fmt(w_pt)}pt"', root, count=1)
    fixed = re.sub(r'\bheight="[^"]*"', f'height="{fmt(h_pt)}pt"', fixed, count=1)
    return svg[:m.start()] + fixed + svg[m.end():]


def png_size(path: str) -> tuple[int, int]:
    with open(path, "rb") as fh:
        fh.read(16)
        w, h = struct.unpack(">II", fh.read(8))
    return w, h


def main() -> int:
    ap = argparse.ArgumentParser(description="Export results_v3 figures as SVG + PNG")
    ap.add_argument("--out-dir", default=RESULTS_DIR,
                    help="default: backend/results_v3/ (alongside the PDFs)")
    ap.add_argument("--dpi", type=int, default=DPI)
    ap.add_argument("--svg-text", action="store_true",
                    help="keep text as text in the SVG instead of converting it to "
                         "paths. Smaller file, selectable text, but renders wrong "
                         "wherever Times New Roman is missing.")
    args = ap.parse_args()

    try:
        import pymupdf
    except ImportError:
        print("PyMuPDF is not installed.\n    pip install pymupdf", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    problems = 0

    print(f"source: {RESULTS_DIR}")
    print(f"output: {args.out_dir}")
    print(f"target: {TARGET_WIDTH_IN} in wide, SVG + PNG at {args.dpi} dpi")
    print(f"SVG text: {'kept as text' if args.svg_text else 'converted to paths'}\n")

    for name in FIGURES:
        pdf_path = os.path.join(RESULTS_DIR, f"{name}.pdf")
        if not os.path.isfile(pdf_path):
            print(f"  {name}: MISSING {pdf_path}")
            problems += 1
            continue

        doc = pymupdf.open(pdf_path)
        if doc.page_count != 1:
            print(f"  {name}: {doc.page_count} pages, expected 1 -- skipped")
            problems += 1
            doc.close()
            continue
        page = doc.load_page(0)

        w_pt, h_pt = page.rect.width, page.rect.height
        w_in, h_in = w_pt / PT_PER_IN, h_pt / PT_PER_IN

        if abs(w_pt - TARGET_WIDTH_IN * PT_PER_IN) > WIDTH_TOLERANCE_PT:
            # Deliberately not auto-scaled: scaling is a change to how the
            # figure reads, and the caller should decide.
            print(f"  {name}: WARNING source is {w_in:.3f} in wide, not "
                  f"{TARGET_WIDTH_IN} in. Exported at its native size; "
                  f"re-author the figure rather than scaling it.")
            problems += 1

        # --- SVG ---------------------------------------------------------
        svg = page.get_svg_image(text_as_path=not args.svg_text)
        svg = _unit_the_root(svg, w_pt, h_pt)
        svg_path = os.path.join(args.out_dir, f"{name}.svg")
        with open(svg_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(svg)

        # --- PNG ---------------------------------------------------------
        pix = page.get_pixmap(dpi=args.dpi)
        pix.set_dpi(args.dpi, args.dpi)
        png_path = os.path.join(args.out_dir, f"{name}.png")
        pix.save(png_path)
        doc.close()

        # --- verify ------------------------------------------------------
        px_w, px_h = png_size(png_path)
        expect_w = round(w_in * args.dpi)
        phys = png_phys_dpi(png_path)

        ok = True
        if abs(px_w - expect_w) > 1:
            ok = False
            print(f"  {name}: PNG is {px_w} px wide, expected ~{expect_w}")
        if phys is None or abs(phys[0] - args.dpi) > 1:
            ok = False
            print(f"  {name}: PNG pHYs reads {phys}, expected ~{args.dpi} dpi")
        if "<svg" not in svg[:2000]:
            ok = False
            print(f"  {name}: SVG output does not look like SVG")
        # The declared physical width, not just the viewBox. A unitless
        # value here is the bug this script exists to avoid.
        svg_w = re.search(r'<svg\b[^>]*\bwidth="([^"]+)"', svg)
        if not svg_w or not svg_w.group(1).endswith("pt"):
            ok = False
            print(f"  {name}: SVG width is "
                  f"{svg_w.group(1) if svg_w else 'absent'}, expected a pt value")
        elif abs(float(svg_w.group(1)[:-2]) / PT_PER_IN - w_in) > 0.01:
            ok = False
            print(f"  {name}: SVG width {svg_w.group(1)} does not match {w_in:.3f} in")
        if not ok:
            problems += 1

        svg_kb = os.path.getsize(svg_path) / 1024
        png_kb = os.path.getsize(png_path) / 1024
        print(f"  {name}")
        print(f"      source  {w_in:.3f} x {h_in:.3f} in  ({w_pt:.2f} x {h_pt:.2f} pt)")
        print(f"      .svg    {svg_kb:8.1f} KB  vector, {w_in:.3f} in wide")
        print(f"      .png    {png_kb:8.1f} KB  {px_w} x {px_h} px @ "
              f"{phys[0]:.0f} dpi" if phys else "      .png    no dpi")

    print()
    if problems:
        print(f"{problems} problem(s) -- see above")
        return 1
    print("All figures exported and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
