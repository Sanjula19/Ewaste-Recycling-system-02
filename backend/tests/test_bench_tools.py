"""
The bench-session toolchain, end to end, on synthetic firmware output.

These tools run once, on a bench, with hardware attached and a person
holding a stopwatch. That is the worst possible place to discover that the
parser drops a row or the summary divides by zero -- so the whole chain
(parse -> merge -> summarise) is exercised here against lines shaped
exactly like the ones main.ino emits, with no serial port involved.

The field counts asserted below are the firmware's wire format. If
main.ino's TRIAL line changes, these fail, which is the point.
"""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import log_trials  # noqa: E402
import merge_observations  # noqa: E402
import summarise_terminal_trials as summarise  # noqa: E402

PY = sys.executable


# --------------------------------------------------------------- fixtures

def _trial_line(seq, sense, net, act, total, r, g, b, c, cls,
                http=200, decision="HOLD", led="yellow", gate=1, crusher=1,
                bin_cm=21.4, err="OK"):
    return (f"TRIAL,{seq},{sense},{net},{act},{total},{r},{g},{b},{c},{cls},"
            f"{http},{decision},{led},{gate},{crusher},{bin_cm},{err}")


@pytest.fixture
def session(tmp_path):
    """
    A synthetic 10-scan session: 8 clean, 1 timeout, 1 bad JSON. Scan 1 is
    the cold first request for copper and scan 2 for aluminium, both much
    slower, so the cold-split logic has something to find.
    """
    lines = [
        "=== Component 4 terminal ===",                      # prose, ignored
        "NET,CONNECTED,172.20.10.4",
        "NET,BACKEND,http://172.20.10.4:8000",
        "BIN,24.1",
        _trial_line(1, 1005, 13120, 2310, 16435, 9211, 4742, 4016, 16194, "copper"),
        _trial_line(2, 1002, 12880, 1402, 15284, 9876, 8201, 7944, 17310, "not_copper",
                    decision="SELL NOW", led="green", crusher=0),
        _trial_line(3, 1004, 205, 2305, 3514, 9150, 4700, 4000, 16100, "copper"),
        _trial_line(4, 1001, 198, 1399, 2598, 9900, 8250, 7980, 17400, "not_copper",
                    decision="SELL NOW", led="green", crusher=0),
        _trial_line(5, 1003, 212, 2318, 3533, 9180, 4720, 4010, 16150, "copper"),
        "   some prose in the middle of the session",
        _trial_line(6, 1002, 221, 1410, 2633, 9890, 8210, 7950, 17330, "not_copper",
                    decision="SELL NOW", led="green", crusher=0),
        _trial_line(7, 1004, 209, 2301, 3514, 9160, 4710, 4005, 16120, "copper"),
        # A timeout: no decision, no actuation.
        _trial_line(8, 1003, 30011, 0, 31014, 9870, 8190, 7930, 17290, "not_copper",
                    http=-11, decision="-", led="none", gate=0, crusher=0, err="TIMEOUT"),
        # Bad JSON from the backend.
        _trial_line(9, 1002, 240, 0, 1242, 9140, 4690, 3990, 16080, "copper",
                    http=200, decision="-", led="none", gate=0, crusher=0, err="PARSE_ERR"),
        _trial_line(10, 1001, 215, 1405, 2621, 9880, 8200, 7940, 17300, "not_copper",
                    decision="SELL NOW", led="green", crusher=0),
        "NET,DISCONNECTED,",
        "NET,RECONNECTED,172.20.10.4",
        "BIN,7.1",
        "LOCKOUT,11,7.1,1",
        "LOCKOUT,12,6.8,1",
    ]

    # Drive the real parser, exactly as log_trials.main() does.
    rows = {"TRIAL": [], "LOCKOUT": [], "NET": [], "BIN": []}
    malformed = 0
    for line in lines:
        tag, parts = log_trials.parse_line(line)
        if not tag:
            continue
        if parts is None:
            malformed += 1
            continue
        rows[tag].append(["2026-10-09T09:00:00.000Z", "real"] + parts)
    assert malformed == 0, "well-formed fixture lines must all parse"

    d = tmp_path / "real"
    d.mkdir()

    def write(name, fields, data):
        p = d / name
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(fields)
            w.writerows(data)
        return p

    trials = write("trials_raw.csv", log_trials.TRIAL_FIELDS, rows["TRIAL"])
    lock = write("lockout_raw.csv", log_trials.LOCKOUT_FIELDS, rows["LOCKOUT"])
    write("net_events.csv", log_trials.NET_FIELDS, rows["NET"])

    # The manual sheet: truth for 9 of 10 scans, one deliberately left
    # unobserved, and one misclassification (scan 7 was aluminium).
    obs = d / "observations.csv"
    with open(obs, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(merge_observations.OBS_FIELDS)
        w.writerow([1, "copper", "yellow", "yes", "yes", ""])
        w.writerow([2, "aluminium", "green", "yes", "no", ""])
        w.writerow([3, "copper", "yellow", "yes", "yes", ""])
        w.writerow([4, "aluminium", "green", "yes", "no", ""])
        w.writerow([5, "copper", "yellow", "no", "yes", "jammed on the chute lip"])
        w.writerow([6, "aluminium", "green", "yes", "no", ""])
        w.writerow([7, "aluminium", "yellow", "yes", "yes", "called copper by mistake"])
        w.writerow([8, "aluminium", "", "no", "no", "timeout"])
        w.writerow([9, "copper", "", "no", "no", "bad json"])
        # scan 10 deliberately left unobserved
    return {"dir": d, "trials": trials, "lockout": lock, "observations": obs}


# ------------------------------------------------------------------- parser

def test_parser_accepts_every_firmware_line_shape():
    assert log_trials.parse_line(_trial_line(1, 1, 2, 3, 6, 1, 2, 3, 4, "copper"))[0] == "TRIAL"
    assert log_trials.parse_line("LOCKOUT,5,7.1,1")[0] == "LOCKOUT"
    assert log_trials.parse_line("NET,RECONNECTED,10.0.0.2")[0] == "NET"
    assert log_trials.parse_line("BIN,24.1")[0] == "BIN"


def test_parser_ignores_prose_without_counting_it_malformed():
    for prose in ["=== Component 4 terminal ===", "   gate -> 60 deg", "", "   ",
                  ">> ITEM DETECTED  #4", "TRIALS are not a tag"]:
        tag, parts = log_trials.parse_line(prose)
        assert tag == "", prose
        assert parts is None


def test_parser_flags_a_truncated_line_rather_than_dropping_it():
    """
    A USB glitch mid-line must be visible, not silently absent -- an
    undercounted denominator would overstate the round-trip rate.
    """
    tag, parts = log_trials.parse_line("TRIAL,1,1005,212")
    assert tag == "TRIAL"
    assert parts is None


def test_trial_field_count_matches_the_firmware_contract():
    """19 CSV columns = 2 added by the host + 17 from the firmware."""
    assert log_trials.N_TRIAL == 17
    assert len(log_trials.TRIAL_FIELDS) == 19


# -------------------------------------------------------------------- wilson

def test_wilson_does_not_claim_certainty_at_a_perfect_score():
    lo, hi = summarise.wilson(50, 50)
    assert hi == pytest.approx(100.0)
    assert lo < 100.0, "a normal interval would give zero width here"
    assert lo > 90.0


def test_wilson_stays_inside_zero_to_one_hundred():
    for k, n in [(0, 5), (1, 3), (5, 5), (0, 1), (13, 13)]:
        lo, hi = summarise.wilson(k, n)
        assert 0.0 <= lo <= hi <= 100.0, (k, n)


def test_wilson_of_nothing_is_not_a_crash():
    lo, hi = summarise.wilson(0, 0)
    assert lo != lo and hi != hi          # NaN, not an exception


def test_percentile_matches_linear_interpolation():
    s = [1.0, 2.0, 3.0, 4.0]
    assert summarise.percentile(s, 0) == 1.0
    assert summarise.percentile(s, 100) == 4.0
    assert summarise.percentile(s, 50) == pytest.approx(2.5)
    assert summarise.percentile([7.0], 95) == 7.0


# --------------------------------------------------------------------- merge

def test_merge_keeps_every_measured_scan(session, tmp_path):
    out = tmp_path / "terminal_trials.csv"
    rc = subprocess.run(
        [PY, str(TOOLS / "merge_observations.py"),
         "--trials", str(session["trials"]),
         "--observations", str(session["observations"]),
         "--out", str(out)],
        capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 10, "an unobserved scan must not be dropped"
    assert [r["observed"] for r in rows].count("no") == 1
    assert rows[0]["true_material"] == "copper"
    assert rows[9]["true_material"] == ""


def test_merge_reports_an_observation_for_a_scan_that_never_happened(session, tmp_path):
    """The sheet and the log disagreeing is an error, not a warning."""
    with session["observations"].open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerow([99, "copper", "yellow", "yes", "yes", ""])
    out = tmp_path / "t.csv"
    rc = subprocess.run(
        [PY, str(TOOLS / "merge_observations.py"),
         "--trials", str(session["trials"]),
         "--observations", str(session["observations"]),
         "--out", str(out)],
        capture_output=True, text=True)
    assert rc.returncode == 2
    assert "never measured" in rc.stdout


def test_merge_normalises_yes_no_spellings(session, tmp_path):
    obs = tmp_path / "o.csv"
    with obs.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(merge_observations.OBS_FIELDS)
        w.writerow([1, "Cu", "yellow", "Y", "TRUE", ""])
        w.writerow([2, "Aluminum", "green", "1", "no", ""])
    out = tmp_path / "t.csv"
    rc = subprocess.run(
        [PY, str(TOOLS / "merge_observations.py"),
         "--trials", str(session["trials"]),
         "--observations", str(obs), "--out", str(out)],
        capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["item_released"] == "yes"
    assert rows[0]["crusher_seen"] == "yes"
    assert rows[0]["true_material"] == "copper"
    assert rows[1]["item_released"] == "yes"
    assert rows[1]["true_material"] == "aluminium"


def test_merge_refuses_a_sheet_missing_a_column(session, tmp_path):
    obs = tmp_path / "bad.csv"
    obs.write_text("seq,true_material\n1,copper\n", encoding="utf-8")
    rc = subprocess.run(
        [PY, str(TOOLS / "merge_observations.py"),
         "--trials", str(session["trials"]),
         "--observations", str(obs), "--out", str(tmp_path / "t.csv")],
        capture_output=True, text=True)
    assert rc.returncode == 1
    assert "missing column" in rc.stderr


# ----------------------------------------------------------------- summarise

@pytest.fixture
def merged(session, tmp_path):
    out = tmp_path / "terminal_trials.csv"
    subprocess.run(
        [PY, str(TOOLS / "merge_observations.py"),
         "--trials", str(session["trials"]),
         "--observations", str(session["observations"]),
         "--out", str(out)],
        capture_output=True, text=True, check=True)
    return out


def test_summary_counts_round_trips_and_failures(merged):
    rows = list(csv.DictReader(merged.open(encoding="utf-8")))
    a = summarise.analyse("real", rows)
    assert a["n"] == 10
    assert a["ok"] == 8
    assert dict(a["failures"]) == {"TIMEOUT": 1, "PARSE_ERR": 1}


def test_summary_excludes_the_cold_first_request_from_the_warm_stats(merged):
    """
    Scans 1 and 2 are the cold first request for each class, at ~13 s of
    network time. If they leaked into the warm set they would own the p95.
    """
    rows = list(csv.DictReader(merged.open(encoding="utf-8")))
    a = summarise.analyse("real", rows)
    assert set(a["first"]) == {"copper", "not_copper"}
    assert a["net"]["max"] < 1000, "a 13 s cold request leaked into the warm stats"
    assert a["first_total"]["n"] == 2
    assert a["first_total"]["mean"] > 10000


def test_summary_timings_use_only_completed_round_trips(merged):
    """A 30 s timeout is not a scan-to-actuation time."""
    rows = list(csv.DictReader(merged.open(encoding="utf-8")))
    a = summarise.analyse("real", rows)
    assert a["total"]["n"] == 6          # 8 OK minus the 2 cold ones
    assert a["total"]["max"] < 5000


def test_summary_scores_led_against_the_returned_decision(merged):
    rows = list(csv.DictReader(merged.open(encoding="utf-8")))
    a = summarise.analyse("real", rows)
    # 8 completed round trips, all with a matching LED.
    assert a["led_checked"] == 8
    assert a["led_correct"] == 8
    assert a["led_wrong"] == []


def test_summary_separates_commanded_actuation_from_observed_release(merged):
    """
    Scan 5 jammed: the firmware completed the gate motion but the item did
    not leave. Those are different claims and must not collapse into one.
    """
    rows = list(csv.DictReader(merged.open(encoding="utf-8")))
    a = summarise.analyse("real", rows)
    assert a["gate_cmd"] == 8
    assert a["released_obs"] == 9        # 9 observed rows
    assert a["released"] == 6            # scan 5 jammed, 8 and 9 failed
    assert a["released"] < a["gate_cmd"]


def test_summary_builds_the_confusion_matrix(merged):
    """Scan 7 was aluminium called copper -- one false positive."""
    rows = list(csv.DictReader(merged.open(encoding="utf-8")))
    a = summarise.analyse("real", rows)
    m = a["matrix"]
    assert a["scored"] == 9
    assert m[("copper", "copper")] == 4
    assert m[("aluminium", "aluminium")] == 4
    assert m[("aluminium", "copper")] == 1
    assert m[("copper", "aluminium")] == 0
    assert a["class_correct"] == 8


def test_summary_runs_end_to_end_and_writes_latex(merged, session, tmp_path):
    tex = tmp_path / "table7.tex"
    rc = subprocess.run(
        [PY, str(TOOLS / "summarise_terminal_trials.py"),
         "--session", f"real={merged}",
         "--lockout", str(session["lockout"]),
         "--out-tex", str(tex)],
        capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    out = rc.stdout
    for expected in ["SESSION: real", "Round trips", "95% CI", "LOCKOUT TRIALS",
                     "scans refused", "predicted", "First request per metal"]:
        assert expected in out, expected
    body = tex.read_text(encoding="utf-8")
    assert "\\begin{table}" in body and "\\end{table}" in body
    assert body.count("\\\\") >= 5


def test_summary_keeps_real_and_forced_sessions_apart(merged, tmp_path):
    forced = tmp_path / "forced.csv"
    forced.write_text(merged.read_text(encoding="utf-8"), encoding="utf-8")
    rc = subprocess.run(
        [PY, str(TOOLS / "summarise_terminal_trials.py"),
         "--session", f"real={merged}",
         "--session", f"forced_hold={forced}",
         "--out-tex", str(tmp_path / "t.tex")],
        capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "SESSION: real" in rc.stdout
    assert "SESSION: forced_hold" in rc.stdout
    assert "NOT pooled" in rc.stdout


def test_summary_survives_a_session_with_no_completed_round_trips(tmp_path):
    """Every scan failed. Must report 0/N, not divide by zero."""
    p = tmp_path / "t.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        hdr = log_trials.TRIAL_FIELDS + merge_observations.OBS_FIELDS[1:] + ["observed"]
        w.writerow(hdr)
        for seq in (1, 2):
            w.writerow(["ts", "real", seq, 1000, 30000, 0, 31000, 1, 2, 3, 4,
                        "copper", -11, "-", "none", 0, 0, 20.0, "TIMEOUT",
                        "copper", "", "no", "no", "", "yes"])
    rc = subprocess.run(
        [PY, str(TOOLS / "summarise_terminal_trials.py"), "--session", f"real={p}"],
        capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "0/2" in rc.stdout
    assert "TIMEOUT" in rc.stdout
