"""
collect_data.py  —  ESP32 Lab Data Collector
=============================================
E-Waste Toxic Gas Detection System
Author: Sanjula Madushanka

HOW TO USE:
  1. Flash data_collection.ino to your ESP32
  2. Close Arduino IDE Serial Monitor (frees the COM port)
  3. Run this script:
       python scripts/collect_data.py
  4. Follow the on-screen prompts
  5. The script auto-saves every reading to lab_readings.csv

REQUIREMENTS:
  pip install pyserial
"""

import serial
import serial.tools.list_ports
import csv
import time
import sys
from pathlib import Path
from datetime import datetime

# ── Settings ───────────────────────────────────────────────────────────────
BAUD_RATE    = 115200
OUTPUT_CSV   = Path(__file__).parent.parent / 'datasets' / 'collected' / 'lab_readings.csv'
VALID_CLASSES = ['CLEAN', 'CO', 'LPG', 'BENZENE', 'AMMONIA', 'MERCURY', 'H2S']
FEATURE_COLS  = ['timestamp', 'mq2_ppm', 'mq7_ppm', 'mq135_ppm',
                 'mq303_ppm', 'mq136_ppm', 'temperature_c', 'humidity_pct',
                 'gas_class', 'notes']

# ── Colour helpers (Windows compatible) ────────────────────────────────────
def clr(text, code):
    return f"\033[{code}m{text}\033[0m"

GREEN  = lambda t: clr(t, '92')
YELLOW = lambda t: clr(t, '93')
RED    = lambda t: clr(t, '91')
CYAN   = lambda t: clr(t, '96')
BOLD   = lambda t: clr(t, '1')


# ── Find available COM ports ───────────────────────────────────────────────
def find_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None, []
    esp_ports = [p for p in ports if 'CP210' in p.description or
                 'CH340' in p.description or 'USB' in p.description or
                 'UART' in p.description]
    return (esp_ports[0].device if esp_ports else ports[0].device), ports


# ── Print header ───────────────────────────────────────────────────────────
def print_header():
    print("\n" + "=" * 60)
    print("  ESP32 LAB DATA COLLECTOR")
    print("  E-Waste Toxic Gas Detection System")
    print("=" * 60)
    print()


# ── Select COM port ────────────────────────────────────────────────────────
def select_port():
    suggested, all_ports = find_esp32_port()

    if not all_ports:
        print(RED("ERROR: No COM ports found."))
        print("       Make sure ESP32 is plugged in via USB.")
        sys.exit(1)

    print("Available COM ports:")
    for i, p in enumerate(all_ports):
        marker = " <-- likely ESP32" if p.device == suggested else ""
        print(f"  [{i+1}] {p.device}  -  {p.description}{marker}")

    print()
    choice = input(f"Enter port number [default = {suggested}] or type port (e.g. COM3): ").strip()

    if choice == "":
        return suggested
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(all_ports):
            return all_ports[idx].device
    elif choice.upper().startswith("COM") or choice.startswith("/dev/"):
        return choice.upper()

    return suggested


# ── Select gas class ───────────────────────────────────────────────────────
def select_gas_class():
    print()
    print(BOLD("Select gas class for this session:"))
    print()
    for i, cls in enumerate(VALID_CLASSES):
        desc = {
            'CLEAN':   'Clean open air — no gas source',
            'CO':      'Carbon monoxide — old PCB burning',
            'LPG':     'LPG — lighter gas / capacitor',
            'BENZENE': 'Benzene/VOC — plastic burning',
            'AMMONIA': 'Ammonia — NiCd/NiMH battery',
            'MERCURY': 'Mercury vapor — CRT monitor',
            'H2S':     'Hydrogen sulphide — Li-ion battery',
        }[cls]
        print(f"  [{i+1}] {cls:<10} — {desc}")

    print()
    while True:
        choice = input("Enter number (1-7): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(VALID_CLASSES):
            return VALID_CLASSES[int(choice) - 1]
        print(RED("Invalid choice. Enter a number between 1 and 7."))


# ── Get notes ─────────────────────────────────────────────────────────────
def get_notes(gas_class):
    hints = {
        'CLEAN':   'e.g. "clean air baseline in lab"',
        'CO':      'e.g. "PCB circuit board burning test"',
        'LPG':     'e.g. "lighter gas brief spray"',
        'BENZENE': 'e.g. "plastic wire insulation burning"',
        'AMMONIA': 'e.g. "old NiCd battery opened"',
        'MERCURY': 'e.g. "CRT monitor placed 5cm from sensor"',
        'H2S':     'e.g. "Li-ion battery punctured"',
    }
    note = input(f"Notes ({hints.get(gas_class, 'optional')}): ").strip()
    return note if note else f"{gas_class} session"


# ── Ensure CSV exists with header ─────────────────────────────────────────
def ensure_csv_header():
    if not OUTPUT_CSV.exists():
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_CSV, 'w', newline='') as f:
            csv.writer(f).writerow(FEATURE_COLS)
        print(GREEN(f"[OK] Created new CSV: {OUTPUT_CSV}"))
    else:
        # Count existing rows
        with open(OUTPUT_CSV, 'r') as f:
            rows = sum(1 for _ in f) - 1
        print(GREEN(f"[OK] Appending to existing CSV ({rows} rows already)"))


# ── Count existing rows per class ─────────────────────────────────────────
def count_per_class():
    if not OUTPUT_CSV.exists():
        return {}
    counts = {}
    with open(OUTPUT_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = row.get('gas_class', 'UNKNOWN')
            counts[cls] = counts.get(cls, 0) + 1
    return counts


# ── Main collection loop ───────────────────────────────────────────────────
def collect(port, gas_class, notes, target_rows=50):
    print()
    print("=" * 60)
    print(f"  Session: {BOLD(gas_class)}")
    print(f"  Port:    {port}")
    print(f"  Target:  {target_rows} rows")
    print(f"  Notes:   {notes}")
    print("=" * 60)
    print()
    print("Connecting to ESP32...")

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=5)
        time.sleep(2)
        print(GREEN("Connected!"))
    except Exception as e:
        print(RED(f"ERROR: Cannot open {port} - {e}"))
        print("  - Make sure Arduino IDE Serial Monitor is CLOSED")
        print("  - Make sure ESP32 is plugged in")
        return 0

    rows_saved = 0
    print()
    print(f"Waiting for sensor warm-up (30 sec)... Press Ctrl+C to skip")
    print()

    with open(OUTPUT_CSV, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)

        try:
            while True:
                if not ser.is_open:
                    break

                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                except Exception:
                    continue

                if not line:
                    continue

                # Warm-up progress messages
                if line.startswith('#WARMUP:'):
                    msg = line.replace('#WARMUP:', '')
                    try:
                        sec = int(msg)
                        print(f"\r  Warming up: {sec:2d}s remaining... ", end='', flush=True)
                    except Exception:
                        print(f"\r  {msg}", end='', flush=True)
                    continue

                if line.startswith('#READY:'):
                    print(f"\n{GREEN('[READY] Sensors warm. Collecting data...')}")
                    print()
                    print(f"  {'Row':>4}  {'MQ-2':>8} {'MQ-7':>8} {'MQ-135':>8} {'MQ-303':>9} {'MQ-136':>8} {'Temp':>6} {'Hum':>6}")
                    print("  " + "-" * 65)
                    continue

                if line.startswith('#') or line.startswith('mq2'):
                    # Skip comment lines and header
                    continue

                # Parse CSV data row
                parts = line.split(',')
                if len(parts) != 7:
                    continue

                try:
                    values = [float(p.strip()) for p in parts]
                except ValueError:
                    continue

                # Validate values (basic sanity check)
                mq2, mq7, mq135, mq303, mq136, temp, hum = values
                if mq2 < 0 or mq7 < 0 or temp < -10 or temp > 60:
                    print(YELLOW(f"  [SKIP] Suspicious reading: {line}"))
                    continue

                # Save row
                timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                writer.writerow([
                    timestamp, mq2, mq7, mq135, mq303, mq136,
                    temp, hum, gas_class, notes
                ])
                csvfile.flush()
                rows_saved += 1

                # Display reading
                print(f"  {rows_saved:>4}  {mq2:>8.3f} {mq7:>8.3f} {mq135:>8.3f} "
                      f"{mq303:>9.5f} {mq136:>8.3f} {temp:>6.1f} {hum:>6.1f}  "
                      f"{GREEN(gas_class)}")

                # Check if target reached
                if rows_saved >= target_rows:
                    print()
                    print(GREEN(f"[DONE] Target reached: {rows_saved} rows saved for {gas_class}"))
                    break

        except KeyboardInterrupt:
            print()
            print(YELLOW(f"[STOPPED] Saved {rows_saved} rows so far."))

    ser.close()
    return rows_saved


# ── Show progress dashboard ────────────────────────────────────────────────
def show_progress():
    counts = count_per_class()
    total  = sum(counts.values())

    print()
    print(BOLD("=== COLLECTION PROGRESS ==="))
    print()
    print(f"  {'Class':<12} {'Collected':>10}  {'Status'}")
    print("  " + "-" * 45)
    for cls in VALID_CLASSES:
        n   = counts.get(cls, 0)
        bar = "#" * min(n // 2, 25)
        ok  = GREEN("[DONE]") if n >= 30 else (YELLOW("[LOW]") if n > 0 else RED("[NONE]"))
        print(f"  {cls:<12} {n:>10}  {bar}  {ok}")

    print()
    print(f"  Total rows collected: {total}")
    if total >= 210:
        print(GREEN("  [OK] Minimum dataset met (210+ rows). Ready to train!"))
    else:
        needed = 210 - total
        print(YELLOW(f"  [!]  Need {needed} more rows to reach minimum (210 total)"))
    print()


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    # Enable ANSI colours on Windows
    import os
    os.system('')

    print_header()
    show_progress()

    # Ask how many rows to collect
    print("How many rows per session?")
    print("  [1] 30 rows  (~1 minute)")
    print("  [2] 50 rows  (~2 minutes)  <-- recommended")
    print("  [3] 100 rows (~3 minutes)")
    print("  [4] Custom")
    print()
    choice = input("Enter choice [2]: ").strip() or "2"
    rows_map = {"1": 30, "2": 50, "3": 100}
    if choice in rows_map:
        target = rows_map[choice]
    elif choice == "4":
        target = int(input("Enter number of rows: ").strip())
    else:
        target = 50

    while True:
        print()
        port      = select_port()
        gas_class = select_gas_class()
        notes     = get_notes(gas_class)

        ensure_csv_header()

        saved = collect(port, gas_class, notes, target_rows=target)

        print()
        show_progress()

        print()
        another = input("Collect another session? (y/n) [y]: ").strip().lower()
        if another == 'n':
            break

    print()
    print("=" * 60)
    print(BOLD("  COLLECTION COMPLETE"))
    print("=" * 60)
    final = count_per_class()
    total = sum(final.values())
    print(f"  Total rows in CSV: {total}")
    print(f"  File: {OUTPUT_CSV}")
    print()
    print("  Next steps:")
    print("    1. Run: python scripts/merge_datasets.py")
    print("    2. Run: python scripts/run_pipeline.py")
    print()


if __name__ == '__main__':
    main()
