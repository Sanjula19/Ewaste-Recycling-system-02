"""
tools/summarise_terminal_trials.py
----------------------------------
Turns a bench session into the numbers the paper needs, and a LaTeX table.

    python tools/summarise_terminal_trials.py \
        --session real=tools/trials/real/terminal_trials.csv \
        --session forced_hold=tools/trials/forced_hold/terminal_trials.csv \
        --lockout tools/trials/lockout/lockout_raw.csv \
        --out-tex tools/trials/table7_terminal.tex

Each --session is reported SEPARATELY and never pooled. A forced session
has its decision imposed by TRIAL_FORCE_DECISION so the crusher can be
exercised on demand; its actuation timings are real, but its decisions are
not model output. Averaging the two would produce a round-trip rate that
describes neither.

WHAT IS REPORTED, AND THE ONE THING TO WATCH
  * round trips completed x/N, with a 95% Wilson interval
  * failures broken down by error_code
  * scan-to-actuation time: mean, SD, median, p95, and the split into
    sensing / network+backend / actuation
  * the FIRST request per metal reported separately -- it pays for the
    model load (~13 s cold) and would otherwise drag the mean and own
    the p95 on its own
  * correct LED for the returned decision
  * items released / items actuated, with a Wilson interval
  * copper vs aluminium pre-classification accuracy, with a 2x2 matrix
  * lockout triggered x/5 and scans refused x/attempted

Wilson rather than the textbook normal interval because N here is 50 and
the proportions are near 1. At p-hat = 1.0 the normal interval has zero
width, which would report perfect certainty from 50 scans; Wilson does
not, and does not run past 0 or 1 either.

No dependency beyond the standard library, so it runs in the same
interpreter as the rest of the repo with nothing installed.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import sys
from collections import Counter, defaultdict

Z95 = 1.959963984540054

# A round trip counts as completed when the backend answered 200 AND the
# firmware parsed it AND the actuation ran. error_code is the firmware's
# own verdict on that, so OK is the definition rather than a derived one.
OK = "OK"

# The LED the firmware should light for each decision, per report 6.1:
# green = SELL / dispatched, yellow = HOLD / crushing, red = bin full.
EXPECTED_LED = {"SELL NOW": "green", "HOLD": "yellow", "PYROLYSIS": "green"}


def wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials, as percents."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z95 ** 2 / n
    centre = (p + Z95 ** 2 / (2 * n)) / d
    halfwidth = (Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n))) / d
    return (100 * max(0.0, centre - halfwidth), 100 * min(1.0, centre + halfwidth))


def pct(k: int, n: int) -> float:
    return 100.0 * k / n if n else float("nan")


def fmt_rate(k: int, n: int) -> str:
    if n == 0:
        return "n/a (0 trials)"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {pct(k, n):.1f}%  95% CI [{lo:.1f}, {hi:.1f}]"


def describe(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    s = sorted(values)
    return {
        "n": len(s),
        "mean": statistics.fmean(s),
        "sd": statistics.stdev(s) if len(s) > 1 else 0.0,
        "median": statistics.median(s),
        "p95": percentile(s, 95),
        "min": s[0],
        "max": s[-1],
    }


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear interpolation between order statistics, as numpy does."""
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p / 100.0
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_values[int(k)]
    return sorted_values[lo] * (hi - k) + sorted_values[hi] * (k - lo)


def fmt_stats(label: str, d: dict, unit: str = "ms") -> str:
    if d["n"] == 0:
        return f"  {label:<28s} no data"
    return (f"  {label:<28s} mean {d['mean']:8.1f}  SD {d['sd']:7.1f}  "
            f"median {d['median']:8.1f}  p95 {d['p95']:8.1f}  "
            f"[{d['min']:.0f}-{d['max']:.0f}] {unit}  (n={d['n']})")


def num(row: dict, key: str) -> float | None:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return None


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def analyse(label: str, rows: list[dict]) -> dict:
    n = len(rows)
    ok_rows = [r for r in rows if r.get("error_code") == OK]
    failures = Counter(r.get("error_code", "?") for r in rows if r.get("error_code") != OK)

    # First request per metal. The backend loads a TensorFlow model on the
    # first call per metal (~13 s cold), so these are reported on their own
    # rather than being allowed to set the p95 for all 50 scans.
    first_seen: dict[str, dict] = {}
    warm: list[dict] = []
    for r in sorted(rows, key=lambda r: int(r["seq"]) if r.get("seq", "").isdigit() else 0):
        material = (r.get("decision") or "") and (r.get("local_class") or "")
        key = r.get("local_class") or "?"
        if key not in first_seen:
            first_seen[key] = r
        else:
            warm.append(r)

    def spans(subset: list[dict], field: str) -> list[float]:
        out = []
        for r in subset:
            v = num(r, field)
            if v is not None:
                out.append(v)
        return out

    # Timings only from completed round trips: a timeout's "total" is the
    # timeout, not a scan-to-actuation time, and mixing them in would make
    # the system look slower than it is while hiding the failure itself.
    ok_warm = [r for r in warm if r.get("error_code") == OK]
    ok_first = [r for r in first_seen.values() if r.get("error_code") == OK]

    # LED correctness, over completed round trips with a known decision.
    led_checked = led_correct = 0
    led_wrong: list[str] = []
    for r in ok_rows:
        decision = (r.get("decision") or "").strip()
        expected = EXPECTED_LED.get(decision)
        if expected is None:
            continue
        led_checked += 1
        if (r.get("led") or "").strip() == expected:
            led_correct += 1
        else:
            led_wrong.append(f"seq {r.get('seq')}: {decision} -> {r.get('led')} "
                             f"(expected {expected})")

    # Actuation. `gate` is the firmware's own "the motion completed";
    # item_released is a human confirming the item actually left. They are
    # different claims and both are reported.
    gate_cmd = sum(1 for r in rows if (r.get("gate") or "") == "1")
    released = sum(1 for r in rows if (r.get("item_released") or "") == "yes")
    released_obs = sum(1 for r in rows if (r.get("item_released") or "") in ("yes", "no"))
    crush_cmd = sum(1 for r in rows if (r.get("crusher") or "") == "1")
    crush_seen = sum(1 for r in rows
                     if (r.get("crusher") or "") == "1" and (r.get("crusher_seen") or "") == "yes")
    crush_obs = sum(1 for r in rows
                    if (r.get("crusher") or "") == "1"
                    and (r.get("crusher_seen") or "") in ("yes", "no"))

    # Confusion matrix for the LOCAL copper/not-copper verdict against what
    # was actually placed. Only observed rows can be scored.
    matrix = defaultdict(int)
    scored = 0
    for r in rows:
        truth = (r.get("true_material") or "").strip()
        pred = (r.get("local_class") or "").strip()
        if truth not in ("copper", "aluminium") or pred not in ("copper", "not_copper"):
            continue
        pred_material = "copper" if pred == "copper" else "aluminium"
        matrix[(truth, pred_material)] += 1
        scored += 1
    correct = matrix[("copper", "copper")] + matrix[("aluminium", "aluminium")]

    return {
        "label": label,
        "n": n,
        "ok": len(ok_rows),
        "failures": failures,
        "total": describe(spans(ok_warm, "total_ms")),
        "sense": describe(spans(ok_warm, "sense_ms")),
        "net": describe(spans(ok_warm, "net_ms")),
        "act": describe(spans(ok_warm, "act_ms")),
        "first": {k: r for k, r in first_seen.items()},
        "first_total": describe(spans(ok_first, "total_ms")),
        "led_checked": led_checked,
        "led_correct": led_correct,
        "led_wrong": led_wrong,
        "gate_cmd": gate_cmd,
        "released": released,
        "released_obs": released_obs,
        "crush_cmd": crush_cmd,
        "crush_seen": crush_seen,
        "crush_obs": crush_obs,
        "matrix": matrix,
        "scored": scored,
        "class_correct": correct,
        "unobserved": sum(1 for r in rows if (r.get("observed") or "") == "no"),
    }


def report(a: dict) -> None:
    bar = "=" * 72
    print(bar)
    print(f"SESSION: {a['label']}    {a['n']} scan(s) attempted")
    print(bar)

    print("\n-- Round trips ------------------------------------------------")
    print(f"  completed                    {fmt_rate(a['ok'], a['n'])}")
    if a["failures"]:
        print("  failures by error_code:")
        for code, k in a["failures"].most_common():
            print(f"    {code:<14s} {k:3d}  ({pct(k, a['n']):.1f}% of attempts)")
    else:
        print("  failures                     none")
    if a["unobserved"]:
        print(f"  NOTE: {a['unobserved']} scan(s) have no observation row; the "
              f"actuation and\n        classification rates below exclude them.")

    print("\n-- Scan-to-actuation time (completed round trips, warm) -------")
    print(fmt_stats("total (t3-t0)", a["total"]))
    print(fmt_stats("  sensing (t1-t0)", a["sense"]))
    print(fmt_stats("  network+backend (t2-t1)", a["net"]))
    print(fmt_stats("  actuation (t3-t2)", a["act"]))

    print("\n-- First request per metal (cold, reported separately) --------")
    if not a["first"]:
        print("  no data")
    for key, r in sorted(a["first"].items()):
        tot = num(r, "total_ms")
        net = num(r, "net_ms")
        print(f"  {key:<12s} seq {r.get('seq'):>3s}  total "
              f"{(f'{tot:.0f} ms' if tot is not None else '?'):>9s}  of which "
              f"network+backend {(f'{net:.0f} ms' if net is not None else '?'):>9s}"
              f"   [{r.get('error_code')}]")
    if a["first_total"]["n"]:
        print(fmt_stats("  cold total", a["first_total"]))

    print("\n-- LED correctness --------------------------------------------")
    print(f"  correct for the decision     {fmt_rate(a['led_correct'], a['led_checked'])}")
    for w in a["led_wrong"]:
        print(f"    MISMATCH {w}")

    print("\n-- Actuation --------------------------------------------------")
    print(f"  gate motion commanded        {a['gate_cmd']}/{a['n']}")
    print(f"  items released (observed)    {fmt_rate(a['released'], a['released_obs'])}")
    print(f"  crusher stroke commanded     {a['crush_cmd']}")
    print(f"  crusher seen (observed)      {fmt_rate(a['crush_seen'], a['crush_obs'])}")

    print("\n-- Pre-classification: copper vs aluminium --------------------")
    if a["scored"] == 0:
        print("  no observed rows with a true_material to score against")
    else:
        m = a["matrix"]
        print(f"  accuracy                     {fmt_rate(a['class_correct'], a['scored'])}")
        print("                        predicted")
        print("                     copper  aluminium")
        print(f"    actual copper     {m[('copper','copper')]:6d}  {m[('copper','aluminium')]:9d}")
        print(f"    actual aluminium  {m[('aluminium','copper')]:6d}  {m[('aluminium','aluminium')]:9d}")
        tp = m[("copper", "copper")]
        fp = m[("aluminium", "copper")]
        fn = m[("copper", "aluminium")]
        if tp + fp:
            print(f"    copper precision  {fmt_rate(tp, tp + fp)}")
        if tp + fn:
            print(f"    copper recall     {fmt_rate(tp, tp + fn)}")
    print()


def report_lockout(path: str, expected_trials: int) -> None:
    rows = load(path)
    bar = "=" * 72
    print(bar)
    print(f"LOCKOUT TRIALS    {os.path.basename(path)}")
    print(bar)
    if not rows:
        print("  no rows\n")
        return
    attempted = len(rows)
    refused = sum(1 for r in rows if (r.get("refused") or "") == "1")
    triggered = len({r.get("seq") for r in rows})
    print(f"  lockout triggered            {triggered}/{expected_trials} planned trial(s)")
    print(f"  scans refused while locked   {fmt_rate(refused, attempted)}")
    distances = [v for v in (num(r, "bin_cm") for r in rows) if v is not None and v > 0]
    if distances:
        print(f"  bin distance at refusal      {min(distances):.1f}-{max(distances):.1f} cm "
              f"(threshold 7.5 cm)")
        over = [d for d in distances if d >= 7.5]
        if over:
            print(f"  WARNING: {len(over)} refusal(s) at or above the 7.5 cm threshold "
                  f"-- the lockout latched and had not been cleared.")
    print()


def latex(sessions: list[dict], out_path: str) -> None:
    def cell(k: int, n: int) -> str:
        if n == 0:
            return "--"
        lo, hi = wilson(k, n)
        return f"{k}/{n} ({pct(k, n):.1f}\\%) & [{lo:.1f}, {hi:.1f}]"

    lines = [
        "% Generated by tools/summarise_terminal_trials.py -- do not edit by hand.",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Terminal bench-trial results. Forced sessions have their decision "
        "imposed by \\texttt{TRIAL\\_FORCE\\_DECISION} to exercise the crusher on "
        "demand; their decisions are not model output and are reported separately.}",
        "\\label{tab:terminal-trials}",
        "\\begin{tabular}{llrr}",
        "\\hline",
        "Session & Measure & Result & 95\\% CI \\\\",
        "\\hline",
    ]
    for a in sessions:
        lab = a["label"].replace("_", "\\_")
        lines.append(f"{lab} & Round trips completed & {cell(a['ok'], a['n'])} \\\\")
        lines.append(f" & Correct LED for decision & {cell(a['led_correct'], a['led_checked'])} \\\\")
        lines.append(f" & Items released & {cell(a['released'], a['released_obs'])} \\\\")
        if a["scored"]:
            lines.append(f" & Cu/Al pre-classification & {cell(a['class_correct'], a['scored'])} \\\\")
        t = a["total"]
        if t["n"]:
            lines.append(f" & Scan-to-actuation (ms) & {t['mean']:.0f} $\\pm$ {t['sd']:.0f} "
                         f"& median {t['median']:.0f}, p95 {t['p95']:.0f} \\\\")
            lines.append(f" & \\quad sensing / net / act (ms) & "
                         f"{a['sense']['mean']:.0f} / {a['net']['mean']:.0f} / "
                         f"{a['act']['mean']:.0f} & \\\\")
        lines.append("\\hline")
    lines += ["\\end{tabular}", "\\end{table}", ""]

    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarise a terminal bench session")
    ap.add_argument("--session", action="append", default=[], metavar="LABEL=PATH",
                    help="repeatable. e.g. real=tools/trials/real/terminal_trials.csv")
    ap.add_argument("--lockout", default=None, help="lockout_raw.csv")
    ap.add_argument("--lockout-planned", type=int, default=5,
                    help="planned lockout trials, default 5 per the protocol")
    ap.add_argument("--out-tex", default=None, help="write a LaTeX table here")
    args = ap.parse_args()

    if not args.session and not args.lockout:
        ap.error("give at least one --session or a --lockout file")

    analysed = []
    for spec in args.session:
        if "=" not in spec:
            ap.error(f"--session needs LABEL=PATH, got {spec!r}")
        label, path = spec.split("=", 1)
        if not os.path.isfile(path):
            print(f"error: {path} not found", file=sys.stderr)
            return 1
        rows = load(path)
        if not rows:
            print(f"warning: {path} has no rows", file=sys.stderr)
        a = analyse(label, rows)
        analysed.append(a)
        report(a)

    if args.lockout:
        if not os.path.isfile(args.lockout):
            print(f"error: {args.lockout} not found", file=sys.stderr)
            return 1
        report_lockout(args.lockout, args.lockout_planned)

    if len(analysed) > 1:
        print("Sessions are reported separately above and are NOT pooled: a forced")
        print("session's decisions are imposed, so a combined round-trip rate would")
        print("describe neither session.\n")

    if args.out_tex and analysed:
        latex(analysed, args.out_tex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
