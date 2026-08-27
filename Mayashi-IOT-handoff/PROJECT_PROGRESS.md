# Component 4 — Progress Log

**Project:** R26-IT-015 — AI-Powered Automated Waste Segregation & E-Waste Recycling System
**My component:** Predictive Economic Valuation & Strategic Disposition Terminal
**Controller:** ESP32 DevKit V1 (ESP32-D0WD-V3, MAC `04:b2:47:9c:f4:dc`)
**Last updated:** 2026-08-26

---

## 1. Current status

| Item | State |
|---|---|
| Arduino IDE 2.3.10 | Installed |
| ESP32 core 3.3.11 (Espressif) | Installed — **on D: drive**, see §4 |
| CP2102 USB driver | Working, board on **COM8** |
| Blink test | **Passing** |
| IR obstacle sensor | **Passing** |
| TCS34725 colour sensor | **Passing** — on D21/D22, readings stable to <1% |
| SG90 routing servo | Not started — needs external 5 V supply |
| MG996R crusher servo | Not started — needs external 5 V supply |
| HX711 + load cell | **Not in this component** — only Component 3 has one; weight arrives via the backend (see §7) |
| HC-SR04 (bin level) | Not started |
| Status LEDs + buzzer | Not started |
| Wi-Fi → FastAPI backend | Not started |

---

## 2. Pin map

The board's silkscreen uses `Dxx` labels. **`Dxx` = `GPIOxx`** — same number, no conversion.

| Part | Report GPIO | Board pin | Status |
|---|---|---|---|
| TCS34725 SDA | 21 | `D21` | pending |
| TCS34725 SCL | 22 | `D22` | pending |
| ~~HX711 (load cell)~~ | ~~14~~ | `D14` — **now free** | not used, see §7 |
| HC-SR04 (bin level) | 18 | `D18` | pending |
| Green LED (SELL) | 19 | `D19` | pending |
| Yellow LED (HOLD/crushing) | 23 | `D23` | pending |
| Red LED (bin full) | 4 | `D4` | pending |
| Buzzer | 13 | `D13` | pending |
| SG90 routing servo | — | `D25` | chosen, not wired |
| MG996R crusher servo | — | `D26` | chosen, not wired |
| IR sensor OUT | — | `D27` | **wired, working** |

**Do not use `VP`, `VN`, `D34`, `D35` for outputs** — they are input-only. They compile fine and silently do nothing.

---

## 3. Sketches in this folder

| Sketch | Purpose | Result |
|---|---|---|
| `BlinkTest/BlinkTest.ino` | Onboard blue LED on GPIO 2 + serial | Passing |
| `IRSensorTest/IRSensorTest.ino` | IR obstacle module on D27 | Passing |
| `ColourSensorTest/ColourSensorTest.ino` | TCS34725 raw R/G/B/Clear + lux, with I2C scan on failure | Passing |
| `RoutingGateTest/RoutingGateTest.ino` | SG90 gate, 3 bin angles, serial-driven | Written, not yet run |

Serial Monitor baud for all of them: **115200**.

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

1. Install `Adafruit TCS34725` library (Install All for dependencies), wire to D21/D22, run `ColourSensorTest`
2. Record typical R/G/B/Clear values for each demo material — these become the backend's classification thresholds
3. Source a 5 V 3 A supply, then wire and test both servos with `ESP32Servo`
4. HC-SR04 bin-level + the 5 cm lockout threshold
5. LEDs and buzzer
6. Wi-Fi + FastAPI `/ingest` round trip

**Not in my component:** the camera (ESP32-CAM + Raspberry Pi) belongs to Component 3. Confirm with that teammate whether we share one physical rig or build two before cutting any acrylic.
