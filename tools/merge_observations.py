"""
tools/merge_observations.py
---------------------------
Joins what the firmware measured with what a human watched, producing the
single table the summary reads.

    python tools/merge_observations.py \
        --trials tools/trials/real/trials_raw.csv \
        --observations tools/trials/real/observations.csv \
        --out tools/trials/real/terminal_trials.csv

The firmware knows it COMMANDED the gate and lit an LED. It cannot know
whether the item actually left the chute, whether the lamp was visible, or
what the item really was. Those four columns have to come from someone
standing at the rig, which is why this is a join and not a calculation:

    observations.csv : seq, true_material, led_seen, item_released,
                       crusher_seen, notes

Copy tools/observations_template.csv to the session directory and fill it
in as the scans happen. `seq` is the number in the TRIAL line and in the
firmware's ">> ITEM DETECTED #n" banner.

JOIN BEHAVIOUR
Left join on the TRIAL rows: every measured scan appears in the output,
observed or not, with the observation columns empty where no row was
filled in. The alternative -- dropping unobserved scans -- would quietly
shrink the denominator of the round-trip rate, which is the one number
the session exists to produce. Unmatched observation rows (a seq that was
never measured) are reported as an error, because that means the sheet and
the log disagree about what happened.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

OBS_FIELDS = ["seq", "true_material", "led_seen", "item_released", "crusher_seen", "notes"]

YES = {"y", "yes", "1", "true", "t"}
NO = {"n", "no", "0", "false", "f"}


def _norm_yesno(value: str, where: str, errors: list[str]) -> str:
    """
    Normalise to yes/no/"" -- a mix of "y", "Yes" and "TRUE" down one
    column would otherwise be counted as three different answers.
    """
    v = (value or "").strip().lower()
    if v == "":
        return ""
    if v in YES:
        return "yes"
    if v in NO:
        return "no"
    errors.append(f"{where}: {value!r} is not yes/no")
    return ""


def _norm_material(value: str, where: str, errors: list[str]) -> str:
    v = (value or "").strip().lower()
    if v == "":
        return ""
    if v in ("copper", "cu"):
        return "copper"
    if v in ("aluminium", "aluminum", "al"):
        return "aluminium"
    # Anything else is kept verbatim: the bench order is copper/aluminium,
    # but a note of what was actually placed is more use than a rejection.
    errors.append(f"{where}: true_material {value!r} is neither copper nor aluminium "
                  f"(kept as-is)")
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description="Join trials_raw.csv with observations.csv")
    ap.add_argument("--trials", required=True)
    ap.add_argument("--observations", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    for path in (args.trials, args.observations):
        if not os.path.isfile(path):
            print(f"error: {path} not found", file=sys.stderr)
            if path == args.observations:
                print("       copy tools/observations_template.csv and fill it in",
                      file=sys.stderr)
            return 1

    with open(args.trials, encoding="utf-8", newline="") as fh:
        trials = list(csv.DictReader(fh))
    if not trials:
        print(f"error: {args.trials} has no rows", file=sys.stderr)
        return 1

    errors: list[str] = []
    with open(args.observations, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [f for f in OBS_FIELDS if f not in (reader.fieldnames or [])]
        if missing:
            print(f"error: {args.observations} is missing column(s): {missing}",
                  file=sys.stderr)
            print(f"       expected: {OBS_FIELDS}", file=sys.stderr)
            return 1
        obs: dict[str, dict] = {}
        for i, row in enumerate(reader, start=2):
            seq = (row.get("seq") or "").strip()
            if not seq:
                continue
            if seq in obs:
                errors.append(f"observations.csv line {i}: seq {seq} appears twice")
            where = f"observations.csv line {i}"
            obs[seq] = {
                "true_material": _norm_material(row.get("true_material", ""), where, errors),
                "led_seen": (row.get("led_seen") or "").strip().lower(),
                "item_released": _norm_yesno(row.get("item_released", ""), where, errors),
                "crusher_seen": _norm_yesno(row.get("crusher_seen", ""), where, errors),
                "notes": (row.get("notes") or "").strip(),
            }

    out_fields = list(trials[0].keys()) + [
        "true_material", "led_seen", "item_released", "crusher_seen", "notes", "observed",
    ]

    matched = 0
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields, lineterminator="\n")
        w.writeheader()
        for row in trials:
            seq = (row.get("seq") or "").strip()
            o = obs.get(seq)
            if o:
                matched += 1
            row = dict(row)
            row.update(o or {f: "" for f in OBS_FIELDS[1:]})
            row["observed"] = "yes" if o else "no"
            w.writerow(row)

    orphans = sorted(set(obs) - {(r.get("seq") or "").strip() for r in trials},
                     key=lambda s: (len(s), s))
    print(f"wrote {args.out}")
    print(f"  {len(trials)} measured scan(s), {matched} with an observation row")
    if len(trials) != matched:
        print(f"  {len(trials) - matched} scan(s) have no observation -- they are kept, "
              f"with observed=no")
    if orphans:
        print(f"  ERROR: observation row(s) for seq {orphans} were never measured.")
        print(f"         The sheet and the log disagree. Check for an off-by-one in "
              f"the seq column before using this file.")
    for e in errors:
        print(f"  warning: {e}")
    return 2 if orphans else 0


if __name__ == "__main__":
    raise SystemExit(main())
