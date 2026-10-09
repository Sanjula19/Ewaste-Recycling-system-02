"""
tools/log_trials.py
-------------------
Captures the terminal's machine-readable trial lines off the serial port
and writes them to CSV, so a bench session produces data instead of a
scrollback buffer.

    python tools/log_trials.py --port COM8 --session-label real
    python tools/log_trials.py --port COM8 --session-label forced_hold

Requires pyserial:  pip install -r tools/requirements.txt

Reads the lines that main.ino emits when TRIAL_LOG is 1:

    TRIAL,<seq>,<sense_ms>,<net_ms>,<act_ms>,<total_ms>,<r>,<g>,<b>,<c>,
          <class>,<http_status>,<decision>,<led>,<gate>,<crusher>,
          <bin_cm>,<error_code>
    LOCKOUT,<seq>,<bin_cm>,<refused>
    NET,<event>,<detail>
    BIN,<cm>

and writes, into tools/trials/<session-label>/:

    trials_raw.csv      one row per scan
    lockout_raw.csv     one row per scan attempted while locked
    net_events.csv      Wi-Fi transitions and the backend host
    bin_readings.csv    every bin measurement
    serial_raw.log      everything received, verbatim

WHY serial_raw.log EXISTS
It is not in the brief, but it costs nothing and it is the only way back
if a line arrives malformed -- a USB glitch mid-line, or a prose log line
that happens to start with TRIAL. Without it a corrupted row is simply
lost. Rows that fail to parse are counted and reported at the end rather
than silently dropped.

EVERY WRITE IS FLUSHED
A bench session is not repeatable: if the script dies on scan 47 of 50,
the first 46 rows must still be on disk. The cost is negligible at these
rates.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timezone

def _import_serial():
    """
    Imported inside main() rather than at module scope so this file can be
    imported for its field lists -- merge_observations.py and the pipeline
    test both want TRIAL_FIELDS, and neither touches a serial port. A
    top-level import would make the constants unreachable on any machine
    without pyserial, including CI.
    """
    try:
        import serial  # pyserial
        return serial
    except ImportError:
        sys.exit(
            "pyserial is not installed.\n"
            "    pip install -r tools/requirements.txt\n"
            "(or: pip install pyserial)"
        )


TRIAL_FIELDS = [
    "host_timestamp", "session_label", "seq",
    "sense_ms", "net_ms", "act_ms", "total_ms",
    "r", "g", "b", "c",
    "local_class", "http_status", "decision", "led",
    "gate", "crusher", "bin_cm", "error_code",
]
LOCKOUT_FIELDS = ["host_timestamp", "session_label", "seq", "bin_cm", "refused"]
NET_FIELDS = ["host_timestamp", "session_label", "event", "detail"]
BIN_FIELDS = ["host_timestamp", "session_label", "bin_cm"]

# Payload field counts, excluding the leading tag.
N_TRIAL = 17
N_LOCKOUT = 3
N_NET = 2
N_BIN = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# Expected payload length per tag, excluding the leading tag itself.
EXPECTED = {"TRIAL": N_TRIAL, "LOCKOUT": N_LOCKOUT, "NET": N_NET, "BIN": N_BIN}


def parse_line(line: str) -> tuple[str | None, list[str] | None]:
    """
    Classify one serial line.

    Returns (tag, fields) for a well-formed trial line, ("", None) for a
    prose log line to ignore, and (tag, None) for a line that carries a
    known tag but the wrong field count -- which the caller counts as
    malformed rather than dropping silently.

    Split out from main() so it can be tested without a serial port; the
    bench session is not a place to discover a parser bug.
    """
    line = line.strip()
    if not line:
        return "", None
    tag, sep, rest = line.partition(",")
    if tag not in EXPECTED:
        return "", None
    if not sep:
        return tag, None
    fields = rest.split(",")
    if len(fields) != EXPECTED[tag]:
        return tag, None
    return tag, fields


class Sink:
    """One CSV file, header written once, flushed after every row."""

    def __init__(self, path: str, fields: list[str]) -> None:
        self.path = path
        self.fields = fields
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self.fh = open(path, "a", encoding="utf-8", newline="")
        self.w = csv.writer(self.fh, lineterminator="\n")
        if new:
            self.w.writerow(fields)
            self.fh.flush()
        self.count = 0

    def write(self, row: list) -> None:
        self.w.writerow(row)
        self.fh.flush()
        self.count += 1

    def close(self) -> None:
        self.fh.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[3])
    ap.add_argument("--port", required=True, help="serial port, e.g. COM8 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200, help="default 115200, as main.ino")
    ap.add_argument("--session-label", required=True,
                    help='e.g. "real", "forced_hold", "lockout". Recorded in every '
                         "row and used as the output directory name, so the summary "
                         "can keep real and forced sessions apart.")
    ap.add_argument("--outdir", default=None,
                    help="default tools/trials/<session-label>/")
    args = ap.parse_args()

    serial = _import_serial()

    outdir = args.outdir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "trials", args.session_label)
    os.makedirs(outdir, exist_ok=True)

    trials = Sink(os.path.join(outdir, "trials_raw.csv"), TRIAL_FIELDS)
    lockouts = Sink(os.path.join(outdir, "lockout_raw.csv"), LOCKOUT_FIELDS)
    nets = Sink(os.path.join(outdir, "net_events.csv"), NET_FIELDS)
    bins = Sink(os.path.join(outdir, "bin_readings.csv"), BIN_FIELDS)
    raw = open(os.path.join(outdir, "serial_raw.log"), "a", encoding="utf-8")

    malformed = 0

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as exc:
        return _fail(f"cannot open {args.port}: {exc}")

    print(f"session '{args.session_label}'  port {args.port} @ {args.baud}")
    print(f"writing to {outdir}")
    print("Ctrl-C to stop.\n")

    try:
        while True:
            try:
                line = ser.readline().decode("utf-8", errors="replace").strip()
            except serial.SerialException as exc:
                print(f"\nserial port lost: {exc}")
                break
            if not line:
                continue

            raw.write(line + "\n")
            raw.flush()

            ts = _now()
            tag, parts = parse_line(line)

            if not tag:
                # Prose log line. Already in serial_raw.log; nothing to do.
                continue
            if parts is None:
                malformed += 1
                print(f"\n  ! malformed {tag}: {line[:90]}")
                continue

            sink = {"TRIAL": trials, "LOCKOUT": lockouts,
                    "NET": nets, "BIN": bins}[tag]
            sink.write([ts, args.session_label] + parts)

            print(f"\r  trials {trials.count:3d} | lockouts {lockouts.count:3d} | "
                  f"net {nets.count:3d} | bin {bins.count:4d}", end="", flush=True)

    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        for s in (trials, lockouts, nets, bins):
            s.close()
        raw.close()

    print("\n")
    print(f"  trials_raw.csv     {trials.count} row(s)")
    print(f"  lockout_raw.csv    {lockouts.count} row(s)")
    print(f"  net_events.csv     {nets.count} row(s)")
    print(f"  bin_readings.csv   {bins.count} row(s)")
    if malformed:
        print(f"  {malformed} malformed line(s) skipped -- see serial_raw.log")
    if trials.count == 0:
        print("\n  No TRIAL lines arrived. Check that TRIAL_LOG is 1 in main.ino,")
        print("  that the board is on this port, and that nothing else (Serial")
        print("  Monitor in the Arduino IDE) is holding the port open.")
    return 0


def _fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
