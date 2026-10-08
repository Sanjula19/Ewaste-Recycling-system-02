"""
scripts/latency_bench.py
------------------------
Measures request latency for POST /api/forecast/ and
POST /api/iot/ingest?compact=true against a running backend, so the effect
of the Change 3 efficiency work is a measurement rather than a claim.

    venv/Scripts/python.exe scripts/latency_bench.py --label before --n 50
    venv/Scripts/python.exe scripts/latency_bench.py --label after  --n 50

Each label's rows are appended to results_v2/latency_before_after.csv.

The first call per metal is reported separately as `cold`: it pays for the
TensorFlow/Keras model load and the first 90-step recursive forecast, and
averaging it in with the warm calls would hide both the cost it represents
and the improvement in it.
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time

import requests

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

METALS = ["aluminium", "copper", "lead", "nickel", "steel", "zinc"]
CSV_PATH = os.path.join(BACKEND_DIR, "results_v2", "latency_before_after.csv")
FIELDS = ["label", "endpoint", "n_warm", "cold_ms", "mean_ms", "median_ms", "max_ms", "min_ms", "p95_ms"]


def _wait_for_health(base: str, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if requests.get(f"{base}/api/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise SystemExit(f"backend at {base} never became healthy")


def _timed(fn) -> float:
    t0 = time.perf_counter()
    r = fn()
    dt = (time.perf_counter() - t0) * 1000.0
    if r.status_code != 200:
        raise SystemExit(f"HTTP {r.status_code}: {r.text[:300]}")
    return dt


def bench_forecast(base: str, n: int) -> dict:
    """n requests spread round-robin over the six metals."""
    cold = max(_timed(lambda m=m: requests.post(
        f"{base}/api/forecast/", json={"metal": m, "weight_kg": 100}, timeout=600))
        for m in METALS)
    warm = [_timed(lambda m=METALS[i % len(METALS)]: requests.post(
        f"{base}/api/forecast/", json={"metal": m, "weight_kg": 100}, timeout=600))
        for i in range(n)]
    return _summarise("POST /api/forecast/", cold, warm)


def bench_iot(base: str, n: int) -> dict:
    body = lambda m: {"device_id": "bench", "bin_id": "bin-01", "weight_kg": 12.5, "known_material": m}
    cold = max(_timed(lambda m=m: requests.post(
        f"{base}/api/iot/ingest?compact=true", json=body(m), timeout=600)) for m in METALS)
    warm = [_timed(lambda m=METALS[i % len(METALS)]: requests.post(
        f"{base}/api/iot/ingest?compact=true", json=body(m), timeout=600))
        for i in range(n)]
    return _summarise("POST /api/iot/ingest?compact=true", cold, warm)


def _summarise(endpoint: str, cold: float, warm: list[float]) -> dict:
    s = sorted(warm)
    return {
        "endpoint": endpoint,
        "n_warm": len(warm),
        "cold_ms": round(cold, 1),
        "mean_ms": round(statistics.fmean(warm), 1),
        "median_ms": round(statistics.median(warm), 1),
        "max_ms": round(max(warm), 1),
        "min_ms": round(min(warm), 1),
        "p95_ms": round(s[min(len(s) - 1, int(0.95 * len(s)))], 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="e.g. before / after")
    ap.add_argument("--base", default="http://127.0.0.1:8099")
    ap.add_argument("--n", type=int, default=50)
    args = ap.parse_args()

    _wait_for_health(args.base)
    rows = [bench_forecast(args.base, args.n), bench_iot(args.base, args.n)]
    for r in rows:
        r["label"] = args.label

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    is_new = not os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in FIELDS})

    for r in rows:
        print(f"[{args.label}] {r['endpoint']:38s} cold {r['cold_ms']:>9.1f}  "
              f"mean {r['mean_ms']:>8.1f}  median {r['median_ms']:>8.1f}  max {r['max_ms']:>8.1f} ms")
    print(f"\nAppended to {CSV_PATH}")


if __name__ == "__main__":
    main()
