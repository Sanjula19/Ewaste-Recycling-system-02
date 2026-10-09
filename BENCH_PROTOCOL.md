# Bench Protocol — Component 4 Terminal

**Purpose:** produce the four measurements the paper is missing — terminal
trials, round-trip success rate, actuation accuracy and end-to-end latency —
in one session.

**Read before starting:** `Mayashi-IOT-handoff/PROJECT_PROGRESS.md` §1 and
`SENSOR_PIN_SUMMARY.md`.

---

## What is being measured, and why in this order

| Block | Scans | Produces |
|---|---|---|
| A. Real scans | 50 | round-trip rate, latency, Cu/Al classification accuracy, LED correctness, release rate |
| B. Backend restart | within A | the cold first-request-per-metal figure, separated from the warm ones |
| C. Forced HOLD | 10 | crusher actuation, which a real forecast may never ask for |
| D. Lockout | 5 | lockout trigger rate and refusal-while-locked rate |

Block C is separate because its decisions are **imposed**, not model output.
`tools/summarise_terminal_trials.py` reports it separately and refuses to
pool it with block A — a combined round-trip rate would describe neither.

---

## 0. Before you touch the rig (~20 min)

**Firmware settings.** In `Mayashi-IOT-handoff/main/main.ino`:

```c
#define TRIAL_LOG       1
#define STEP_DELAY_MS   0     // NOT 1200 — see below
```

`STEP_DELAY_MS 1200` adds roughly **10 s of pure padding per scan** (the
cycle passes through `logStep()` five times and `delay(STEP_DELAY_MS)`
several more). At 1200 the reported scan-to-actuation time measures the
padding, not the terminal. `t0` is taken before the first `logStep()` so a
mistake here is survivable, but the intermediate spans are not — leave it
at 0.

**Checklist:**

- [ ] `STEP_DELAY_MS` is 0 and `TRIAL_LOG` is 1
- [ ] Compile: `arduino-cli compile --fqbn esp32:esp32:esp32 Mayashi-IOT-handoff/main`
- [ ] `WIFI_SSID` / `WIFI_PASS` / `BACKEND_IP` correct at the top of `main.ino`.
      **`BACKEND_IP` changes every time the laptop rejoins the hotspot** —
      run `ipconfig` and check it now. It is the single most common cause of
      a session of `TIMEOUT` rows.
- [ ] Servos on their **dedicated 5 V 3 A supply**, grounds tied to the ESP32.
      Not the ESP32's 5V pin, not the L298N (its 78M05 gives 500 mA; the SG90
      stalls at ~700 mA and the MG996R at ~2.5 A).
- [ ] **Plate clear at boot** — `baselineClear` is measured during startup
      and everything downstream is relative to it.
- [ ] Watch the LED self-test: any lamp that stays dark is a wiring fault.
      GPIO 19 and 23 are dead; do not use them.
- [ ] 25 copper and 25 aluminium items, pre-sorted into two trays
- [ ] `pip install -r tools/requirements.txt` (pyserial)
- [ ] `TRIAL_FORCE_DECISION` **unset** in `backend/.env`
- [ ] Backend running and reachable: `curl http://<BACKEND_IP>:8000/api/health`
- [ ] Print `tools/bench_scan_order.csv` and `tools/observations_template.csv`

**Close the Arduino IDE Serial Monitor.** It holds the port open and
`log_trials.py` will not be able to read it.

---

## A. 50 real scans

The order is **pre-written** in `tools/bench_scan_order.csv` — a seeded
shuffle of 25 copper and 25 aluminium (seed 20261009, reproducible). Follow
it exactly. Do not improvise the order: alternating Cu/Al by hand produces a
pattern, and a classifier that happens to track the alternation would score
well for the wrong reason. The longest run of the same material is 5; that
is expected, not an error in the sheet.

```
 1-10: Al Cu Cu Cu Al Cu Al Al Cu Cu
11-20: Cu Al Cu Cu Al Cu Al Al Cu Cu
21-30: Cu Al Al Al Al Al Cu Cu Al Cu
31-40: Al Cu Cu Al Al Cu Al Cu Cu Al
41-50: Al Al Al Al Cu Cu Cu Al Cu Al
```

**Start logging first:**

```bash
python tools/log_trials.py --port COM8 --session-label real
```

Then run the scans. **Per scan, write one row on the observation sheet**
(`seq`, `true_material`, `led_seen`, `item_released`, `crusher_seen`,
`notes`). `seq` is the number in the `>> ITEM DETECTED #n` banner and in the
`TRIAL` line.

Four things only a person can record, which is why the sheet exists:

- **`led_seen`** — which lamp actually lit. The firmware logs what it
  *commanded*.
- **`item_released`** — whether the item actually left the chute. The
  firmware logs that the gate *motion completed*, which is a different
  claim; a jam satisfies the first and not the second.
- **`crusher_seen`** — whether the stroke visibly ran.
- **`true_material`** — what you actually placed. Scored against the
  terminal's local verdict in the confusion matrix.

Let the item **clear the IR beam** between scans — the trigger is
edge-triggered and will not fire again until the beam is clear. Wait for
`-- removed, ready for next --`.

If a scan fails, **record it and move on.** Do not retry it as the same
`seq`. A failure is a data point: the round-trip rate is the number the
session exists to produce, and silently retrying failures inflates it.

### B. Backend restart, at scan 25

With logging still running, restart the backend:

```bash
# Ctrl-C the uvicorn process, then
cd backend && venv/Scripts/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Wait for `Preloaded model artifacts in …`, then continue from scan 26.

This is deliberate. The first request per metal after a restart pays for the
TensorFlow model load — about **13 s cold against ~170 ms warm**. The
summary reports those first requests separately; pooled, two cold scans
would own the p95 of all 50 and the headline latency would be a model-load
time rather than a terminal time.

Scans 1–2 give the first cold pair; the restart gives a second, which is
what makes the figure more than an anecdote.

Stop logging with Ctrl-C when scan 50 is done. Expect:

```
  trials_raw.csv     50 row(s)
```

If it says fewer, some scans produced no `TRIAL` line — check
`serial_raw.log` before moving on.

---

## C. 10 forced-HOLD scans

A real forecast returns HOLD only when the market says so, and at the time
of writing the live models return SELL for most metals. You cannot wait for
a HOLD while standing at the rig, so the decision is forced — otherwise the
crusher goes untested.

```bash
# backend/.env
TRIAL_FORCE_DECISION=HOLD
```

Restart the backend. It will log, at WARNING:

```
TRIAL MODE: TRIAL_FORCE_DECISION=HOLD -- /api/iot/ingest will return this
decision instead of the model's ...
```

**If you do not see that line, forcing is not on.** Do not proceed on the
assumption that it is.

```bash
python tools/log_trials.py --port COM8 --session-label forced_hold
```

Run **10 scans** (any mix; copper is convenient). Each should light yellow
and run a compaction stroke. Record `crusher_seen` for every one.

Every response and every manifest entry from this block carries
`forced=true`, and `GET /api/manifest/summary` reports `forced_entries`.
That is what keeps these 10 out of the real decision record.

### Switch forcing off immediately afterwards

```bash
# backend/.env — remove the line, or set it empty
TRIAL_FORCE_DECISION=
```

Restart the backend and **confirm the warning is gone.** A later session run
with forcing still on would silently record imposed decisions as real ones —
the one failure mode this flag is designed around, and the reason an
unrecognised value raises instead of defaulting to off.

---

## D. 5 lockout trials

```bash
python tools/log_trials.py --port COM8 --session-label lockout
```

Per trial:

1. Fill or raise the waste surface to **within 7.5 cm** of the lid sensor
   (a box or a hand works; the bin monitor re-measures every 4 s).
2. Wait for `!! BIN FULL … scanning suspended` and the **red** LED.
3. **Attempt a scan** with the bin still full. It must be refused:
   `>> item detected but BIN IS FULL`, a `LOCKOUT` line, and a `TRIAL` line
   with `error_code=LOCKOUT`.
4. Clear the bin, wait for `bin cleared - scanning resumed`.
5. Repeat — 5 times total.

Both the trigger and the refusal are measured: a lockout that latches but
still accepts items would pass step 2 and fail step 3.

---

## E. Processing

```bash
# One per session
python tools/merge_observations.py \
    --trials tools/trials/real/trials_raw.csv \
    --observations tools/trials/real/observations.csv \
    --out tools/trials/real/terminal_trials.csv

python tools/merge_observations.py \
    --trials tools/trials/forced_hold/trials_raw.csv \
    --observations tools/trials/forced_hold/observations.csv \
    --out tools/trials/forced_hold/terminal_trials.csv

python tools/summarise_terminal_trials.py \
    --session real=tools/trials/real/terminal_trials.csv \
    --session forced_hold=tools/trials/forced_hold/terminal_trials.csv \
    --lockout tools/trials/lockout/lockout_raw.csv \
    --out-tex tools/trials/table7_terminal.tex
```

Type the observation sheet into `observations.csv` (copy
`tools/observations_template.csv`) before merging. If `merge_observations.py`
reports *"observation row(s) for seq N were never measured"*, the sheet and
the log disagree about what happened — fix the `seq` column before trusting
anything downstream.

`table7_terminal.tex` goes straight into the paper. Update
`Component4-Paper-Numbers.md` items 12–15 and the end-to-end half of item 14
from the summary output.

---

## What a good session looks like

| Measure | Expect | Investigate if |
|---|---|---|
| `trials_raw.csv` rows | exactly 50 | fewer — a scan produced no TRIAL line |
| Round trips completed | ≥ 45/50 | a cluster of `TIMEOUT` — check `BACKEND_IP` and `net_events.csv` for a drop |
| Sensing (t1−t0) | ~1000 ms, very low SD | high SD — the item is landing during the settle |
| Network+backend warm | 150–300 ms | > 1 s — Wi-Fi, not the backend |
| Actuation (t3−t2) | ~1.4 s SELL, ~3.2 s HOLD | the gate is 2×700 ms, the crusher 2×900 ms |
| Cold first request | 10–15 s | this is the model load, and it is expected |
| LED correct | 50/50 | any mismatch is a firmware or wiring bug, not noise |
| Items released | high, but **not** assumed 50/50 | this is the number a jam shows up in |
| Cu/Al accuracy | ≥ 45/50 | matte or dark items read badly; note them |
| Lockout refusals | 5/5 | a single acceptance while locked is a real defect |

**Report what happened, including the failures.** Three timeouts and a jam
in 50 scans is a credible result for a prototype; 50/50 with no failure
modes recorded invites the question of what was not counted.

---

## Known constraints

- **Single bin.** The gate does the same release motion for every item,
  regardless of material or decision. It is a release mechanism, not a
  diverter — do not describe it as routing to separate bins.
- **Weight is a placeholder.** `PLACEHOLDER_WEIGHT_KG = 2.5`; only
  Component 3 has a load cell. Every batch value in this session is computed
  from 2.5 kg.
- **Buzzer is not wired** (`USE_BUZZER 0`), so `beep_ms` in the response
  does nothing.
- **`GATE_RELEASE` is 60°, a placeholder.** If items do not reliably clear
  the chute, tune it — and record that you did, since it changes the
  actuation timing.
- **Classification is copper vs not-copper only.** Three colour channels
  cannot do more; a bright neutral surface has the same `r/c` as copper,
  which is why the blue channel needs a band and not a floor.
