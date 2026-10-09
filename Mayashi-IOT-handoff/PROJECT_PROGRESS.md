# Component 4 — Progress Log

**Project:** R26-IT-015 — AI-Powered Automated Waste Segregation & E-Waste Recycling System
**My component:** Predictive Economic Valuation & Strategic Disposition Terminal
**Controller:** ESP32 DevKit V1 (ESP32-D0WD-V3, MAC `04:b2:47:9c:f4:dc`)
**Last updated:** 2026-10-09 — reconciled against what is actually in the repo

---

## 1. Current status

Everything below is read off the firmware and the wiring notes in this
folder, not from memory. `SENSOR_PIN_SUMMARY.md` is the authoritative pin
map; where this file disagreed with it, this file was wrong and has been
corrected.

| Item | State |
|---|---|
| Arduino IDE 2.3.10 | Installed |
| ESP32 core 3.3.11 (Espressif) | Installed — **on D: drive**, see §4 |
| CP2102 USB driver | Working, board on **COM8** |
| Blink test | **Passing** |
| IR obstacle sensor | **Wired and working** — GPIO 27, active LOW, 150 ms debounce. Now the arrival trigger (`USE_IR 1`) |
| TCS34725 colour sensor | **Wired and working** — **GPIO 16/17 (RX2/TX2)**, not D21/D22 as this file previously claimed |
| SG90 routing gate servo | **Wired** — GPIO 26, `USE_GATE_SERVO 1`. 90° resting position confirmed by `ServoAngleTest.ino`; `GATE_RELEASE` (60°) is still a placeholder to tune against the real chute |
| MG996R crusher servo | **Wired** — GPIO 14, `USE_CRUSHER 1`. Runs on HOLD material, stroke fixed at 120° press / 20° release |
| HC-SR04 (bin level) | **Wired** — TRIG 5, ECHO 22 through a 1k/2k divider, `USE_ULTRASONIC 1`. 7.5 cm lockout, re-measured every 4 s on its own timer |
| Status LEDs | **Wired** — green 21 (SELL/dispatched), yellow 18 (HOLD/crushing), red 4 (bin full), with a boot self-test |
| Buzzer | **Not wired** — `USE_BUZZER 0`. GPIO 13 reserved for it |
| Wi-Fi → FastAPI backend | **Implemented** in `main/main.ino` — IR trigger → settle → colour read → POST → LED → gate. SSID/IP are hardcoded at the top of that file and change on every hotspot reconnect |
| HX711 + load cell | **Not in this component** — only Component 3 has one; weight arrives via the backend (see §7). `PLACEHOLDER_WEIGHT_KG = 2.5` stands in until that handoff exists |
| Single bin only | The gate does the **same release motion for every item** regardless of material or decision. Diverting to separate bins is a later step — do not describe the gate as a diverter |

**Not yet measured, and the reason for the bench session:** no trial of the
assembled terminal has ever been logged. There is no item count, no
round-trip success rate and no actuation-accuracy figure anywhere in this
repo. The hardware above is ready, so this is a measurement session rather
than more development. Per item, log: timestamp, IR fired, raw R/G/B/Clear,
classification, backend HTTP status, decision returned, LED lit, gate
actuated, item cleared the chute, bin distance.

**GPIO 19 and 23 are dead.** Both stopped driving on 27 Aug after being run
without current-limiting resistors. They are deliberately unused — do not
plan the rig around them.

---

## 2. Pin map

The board's silkscreen uses `Dxx` labels. **`Dxx` = `GPIOxx`** — same number,
no conversion — **except `RX2`/`TX2`, which are GPIO 16 and 17.** That
exception is where the colour sensor actually lives, and getting it wrong is
what made the old version of this table disagree with the firmware.

This table now matches `SENSOR_PIN_SUMMARY.md` and the constants at the top
of `main/main.ino`. Earlier revisions of this file listed the colour sensor
on D21/D22, the ultrasonic on D18, the LEDs on 19/23 and the servos on
D25/D26 — all superseded.

| Part | GPIO | Board pin | Status |
|---|---|---|---|
| TCS34725 SDA | 16 | `RX2` | **wired, working** |
| TCS34725 SCL | 17 | `TX2` | **wired, working** |
| IR sensor OUT | 27 | `D27` | **wired, working** — arrival trigger |
| HC-SR04 TRIG | 5 | `D5` | **wired** |
| HC-SR04 ECHO | 22 | `D22` | **wired** — through a 1k/2k divider, never direct |
| Green LED (SELL) | 21 | `D21` | **wired** |
| Yellow LED (HOLD/crushing) | 18 | `D18` | **wired** |
| Red LED (bin full) | 4 | `D4` | **wired** |
| SG90 routing gate servo | 26 | `D26` | **wired** — see `ServoAngleTest.ino` |
| MG996R crusher servo | 14 | `D14` | **wired** — moved off 26 when the gate took it |
| Onboard blue LED | 2 | — | soldered to the board; boot/debug indicator |
| Buzzer | 13 | `D13` | reserved, **not wired** |
| ~~HX711 (load cell)~~ | — | — | not used, see §7 |
| **GPIO 19** | 19 | `D19` | **DEAD** — stopped driving 27 Aug (no current-limiting resistor) |
| **GPIO 23** | 23 | `D23` | **DEAD** — same cause |

**Do not use `VP`, `VN`, `D34`, `D35` for outputs** — they are input-only. They compile fine and silently do nothing.

**ADC2 pins stop working when Wi-Fi is active.** This component uses Wi-Fi, so any *analog* sensor must go on ADC1: GPIO 32, 33, 34, 35, 36, 39.

---

## 3. Sketches in this folder

Every sketch in this folder, verified against its actual contents:

| Sketch | Lines | Purpose | Result |
|---|---|---|---|
| **`main/main.ino`** | 768 | **The terminal firmware.** Everything below in one program: IR trigger → settle → colour read → POST → LED → gate, plus an independent bin monitor with lockout. Features switched on/off in the `FEATURES` block | Written; **never bench-tested** |
| `BlinkTest/BlinkTest.ino` | 21 | Onboard blue LED on GPIO 2 + serial | Passing |
| `IRSensorTest/IRSensorTest.ino` | 24 | HW-201/FC-51 IR obstacle module on D27 | Passing |
| `ColourSensorTest/ColourSensorTest.ino` | 146 | TCS34725 raw R/G/B/Clear **plus the r/c and b/c ratios** the thresholds are expressed in, every 500 ms, with an I2C scan on failure | **Rewritten 2026-10-09 — see the warning below** |
| `UltrasonicTest/UltrasonicTest.ino` | 135 | HC-SR04 distance + BIN FULL flag at the lockout threshold | Passing |
| `LedTest/LedTest.ino` | 84 | Three status LEDs in sequence | Passing |
| `LedDebug/LedDebug.ino` | 49 | Blinks all three status pins forever | Diagnostic |
| `LedAllOn/LedAllOn.ino` | 42 | All LEDs on, held steady | Diagnostic |
| `RoutingGateTest/RoutingGateTest.ino` | 50 | SG90 gate, 3 bin angles, serial-driven | Written, not yet run |
| `RoutingGateTest/ServoAngleTest.ino` | 34 | Holds the gate at one fixed angle on D26 — how 90° was confirmed as the resting position | Passing |
| `ItemScan/ItemScan.ino` | 335 | Earlier single-file scan cycle + backend round trip. Superseded by `main/main.ino` | Superseded |
| `ItemScan_IRversion_backup.ino.txt` | — | Backup of an earlier IR-triggered ItemScan | Reference only |

Serial Monitor baud for all of them: **115200**.

### ⚠ `ColourSensorTest.ino` did not contain a colour sensor test

Until 2026-10-09 this filename never held one in git history:

- Before that date it held a byte-for-byte copy of the full 768-line
  `main/main.ino` terminal firmware. **Opening it to "check the colour
  sensor" would have flashed the whole terminal.**
- Before *that*, the committed version was the 130-line HC-SR04 ultrasonic
  test — a duplicate of `UltrasonicTest.ino`.

It has been rewritten to be what its name says, using the same pins
(GPIO 16/17), gain (16x) and integration time (154 ms) as `main/main.ino`,
so a reading taken with it is directly comparable to one the terminal
takes. `main/main.ino` was not modified. The two superseded versions remain
recoverable from git history if ever needed.

Every other sketch in the table above was checked and does match its
filename.

---

## 4. Environment setup — important

**Arduino's data directory was moved to `D:\Arduino15`.**

C: had dropped to 0.65 GB free during the ESP32 core install, which nearly destabilised Windows. The ESP32 core needs ~6 GB (it installs toolchains for every ESP32 variant — C3, C6, H2, P4, S2, S3 — not just ours; there's no way to install only one).

Config lives at `C:\Users\MSI\.arduinoIDE\arduino-cli.yaml`:

```yaml
board_manager:
    additional_urls: []
directories:
    data: 'D:\Arduino15'
    downloads: 'D:\Arduino15\staging'
```

Backup of the original is at `arduino-cli.yaml.bak`.

**Do not delete `D:\Arduino15\staging`.** It holds 1.77 GB of cached installer archives. If the core ever needs reinstalling, those make it cost **zero internet data** — which matters because we're on a phone hotspot.

Current free space: C: ~6.6 GB, D: ~151 GB.

---

## 5. Things that went wrong (don't repeat)

**Clicking INSTALL twice in Boards Manager.** The second click made arduino-cli do a full *replace* — it uninstalled all 17 tools, then failed with `platform not installed`, leaving empty folder shells that made the IDE report "3.3.11 installed" while nothing was actually there. Cost about 40 minutes. **Click install once, then leave it alone.** The progress bar freezing for minutes is normal extraction behaviour, not a hang.

**The board is called `ESP32 Dev Module`,** not "ESP32 Dev Board". Searching the wrong name returns no results.

**Four phantom COM ports (COM3–6) are Bluetooth,** not the ESP32. The real one shows as `Silicon Labs CP210x USB to UART Bridge`. Currently **COM8**.

---

## 6. Hardware notes / decisions made

**IR sensor is active LOW** — `OUT` sits HIGH when clear, drops LOW on detection. Powered from **3V3, not 5 V** (ESP32 GPIOs are not 5 V-tolerant). Detection range is 2–30 cm rated, 2–10 cm realistic, and **much shorter on dark objects** — matte black may not register at all, which is a real risk for waste items.

**IR placement decision:** the load cell can detect item presence on its own (weight goes from 0 to non-zero), so an IR sensor above the platform would be redundant. Better use: mount it at the **output chute** to confirm the item actually left after the servo pushes. That catches jams, which the load cell can't see cleanly.

**Load cells are slow** — HX711 runs at 10 SPS and the platform rings for 0.5–2 s after an item lands. Must average ~10 samples and wait for variance to settle before accepting a weight.

**Never mount the servo, camera arm, or IR bracket on the weighing platform.** Their weight adds to the load cell and servo vibration stops readings from ever settling. Mount on a separate fixed frame; keep cables from tugging on the platform.

**Servo power: the L298N is not suitable.** Its 78M05 regulator supplies only 500 mA. SG90 stalls at ~700 mA; MG996R stalls at ~2.5 A. Need a dedicated **5 V 3 A supply** with ground tied to the ESP32. Never power servos from the ESP32's 5V/VIN pin.

**Servos need the `ESP32Servo` library, not the standard `Servo` library** (AVR-only, won't compile). Requires `ESP32PWM::allocateTimer(0)` and `setPeriodHertz(50)`.

**Routing mechanism:** prefer a **gate + slight tilt** over a pusher arm. Gravity moves the item, the servo only steers it — far less torque needed and much less likely to jam during the demo.

**ADC2 pins stop working when Wi-Fi is active.** Since this component uses Wi-Fi, any *analog* sensor must go on ADC1: GPIO 32, 33, 34, 35, 36, 39.

---

## 7. Backend

Report specifies a **shared FastAPI backend** for all four components — use FastAPI, not Flask, so the code merges with teammates'.

Already on this laptop: Python 3.13.2, FastAPI 0.115.12. Flask is *not* installed (and isn't needed).

To reach the server from the ESP32:
1. Bind to `0.0.0.0`, not `127.0.0.1`
2. Open the port in Windows Firewall
3. Both devices on the same network — laptop was `172.20.10.2` on a phone hotspot (**this IP changes on every reconnect** — re-check with `ipconfig` before a demo)

### Weight handoff — there is only ONE load cell

Only Component 3 has a load cell. This component has none, so weight must come
from the backend, not from our own hardware.

Flow: Component 3 weighs and photographs → POSTs weight to the backend → backend
opens an item record → our ESP32 POSTs raw R/G/B/Clear + bin distance → backend
matches it to the open record, does the valuation (`price = weight × forecast
rate/kg`), and returns the decision.

**This needs the two stations to agree on which item they are talking about.**
For the prototype, run a strict **one-item-at-a-time pipeline**: the backend holds
a single "current item" record and rejects a new Station 1 ingest until Station 2
has dispatched the previous one. Trying to have two items in flight without a
proper item ID will silently mismatch weights to colours.

Endpoint to build: `/ingest` taking raw R/G/B/Clear + bin distance (weight is
looked up server-side from the open item record), returning SELL/HOLD, target
facility, calculated energy recovery, and bin-lockout state.

---

## 8. Next steps

Steps 1-6 of the old list are **done** — the library is installed, the
sensor is on GPIO 16/17, thresholds were measured 26-27 Aug, both servos
are wired off a dedicated 5 V supply, the bin lockout is in at 7.5 cm (not
5 cm as originally planned), the LEDs are in, and the Wi-Fi round trip is
implemented in `main/main.ino`. What is left:

1. **Bench session — the only thing blocking the paper.** Run N ≥ 30 items
   (50+ preferred) through the belt and log per item, as listed in §1. This
   closes terminal trials, round-trip success rate, actuation accuracy and
   the end-to-end latency figure in one sitting. Set `STEP_DELAY_MS = 0`
   before timing anything: it is 1,200 ms for Serial-Monitor readability and
   would otherwise dominate the measurement.
2. **Tune `GATE_RELEASE`** (currently 60°, a placeholder) against the real
   chute, and confirm items actually clear it. The IR sensor at the output
   is already positioned to verify that.
3. **Wire the buzzer** on GPIO 13 and set `USE_BUZZER 1`, or drop it from
   the report.
4. **Diverting to separate bins by material/decision** — currently a single
   bin and one release motion for everything.
5. **Weight handoff from Component 3**, replacing `PLACEHOLDER_WEIGHT_KG`.

**Not in my component:** the camera (ESP32-CAM + Raspberry Pi) belongs to Component 3. Confirm with that teammate whether we share one physical rig or build two before cutting any acrylic.
