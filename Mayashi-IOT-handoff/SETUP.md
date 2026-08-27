# Setup Guide — Component 4 (new machine)

**For:** anyone joining this project on a different laptop
**Project:** R26-IT-015 — AI-Powered Automated Waste Segregation & E-Waste Recycling System
**This component:** Predictive Economic Valuation & Strategic Disposition Terminal
**Board:** ESP32 DevKit V1 (ESP32-D0WD-V3, 30-pin)

> If you are an AI assistant reading this: this file is the environment setup.
> `PROJECT_PROGRESS.md` in the same folder is the running log of design decisions
> and what already works. Read both. Do not re-derive decisions already recorded there.

---

## 1. Check what's already installed

Run these first — some may already be present.

```powershell
# Arduino IDE — check it exists
Get-ChildItem "C:\Program Files\Arduino IDE","$env:LOCALAPPDATA\Programs\Arduino IDE" -ErrorAction SilentlyContinue | Select-Object Name

# ESP32 core — should list a version like 3.3.11
Get-ChildItem "$env:LOCALAPPDATA\Arduino15\packages\esp32\hardware\esp32" -ErrorAction SilentlyContinue

# Is the board detected? Look for "Silicon Labs CP210x" or "CH340"
Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match '\(COM\d+\)' } | Select-Object Name

# Python (needed only for the backend, not for flashing)
python --version
python -c "import fastapi; print('fastapi', fastapi.__version__)"

# Free disk space — the ESP32 core needs ~6 GB, see the warning in section 3
Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} |
    Select-Object DeviceID, @{n='FreeGB';e={[math]::Round($_.FreeSpace/1GB,1)}}
```

---

## 2. Install list

| What | Where from | Notes |
|---|---|---|
| **Arduino IDE 2.x** | arduino.cc | 2.3.10 is what we used |
| **ESP32 core by Espressif** | Boards Manager | **NOT** "Arduino ESP32 Boards" — see §4 |
| **CP210x USB driver** | Silicon Labs | Only if no COM port appears |
| **Adafruit TCS34725** | Library Manager | Click **INSTALL ALL** for dependencies |
| **ESP32Servo** | Library Manager | By Kevin Harrington / John K. Bennett |
| Python 3.x + FastAPI | python.org / pip | Backend only, not needed to flash |

**Board settings after install:** Tools → Board → **ESP32 Dev Module**, Port → whichever COM port is the CP210x.

---

## 3. ⚠️ Disk space — read before installing the ESP32 core

**The ESP32 core needs about 6 GB.** It installs toolchains for every ESP32 variant
(C3, C6, H2, P4, S2, S3), not just ours, and there is no way to install only one.

On the original laptop this filled the C: drive to 0.65 GB free and nearly
destabilised Windows. If C: has less than ~10 GB free, redirect Arduino's data
directory to another drive **before** installing.

Edit (or create) `C:\Users\<you>\.arduinoIDE\arduino-cli.yaml`:

```yaml
board_manager:
    additional_urls: []
directories:
    data: 'D:\Arduino15'
    downloads: 'D:\Arduino15\staging'
```

Restart the IDE, then install the core. Everything lands on D: instead.

**Keep the `staging` folder.** It caches ~1.77 GB of installer archives. If the core
ever needs reinstalling, those make it cost zero internet data — which matters a lot
on a phone hotspot.

---

## 4. Things that already went wrong — don't repeat them

**Do not click INSTALL twice in Boards Manager.** The second click triggers a full
*replace*: it uninstalls all 17 tools, then fails with `platform not installed`,
leaving empty folders that make the IDE claim it's installed when nothing is there.
Cost about 40 minutes. Click once, then leave it alone — the progress bar freezing
for minutes is normal extraction, not a hang.

**Install `esp32 by Espressif Systems`, not `Arduino ESP32 Boards` by Arduino.**
The latter only supports the Arduino Nano ESP32, a different board entirely.

**The board is called `ESP32 Dev Module`,** not "ESP32 Dev Board". Searching the
wrong name returns no results.

**Phantom COM ports.** Bluetooth creates several `Standard Serial over Bluetooth link`
ports. The real board shows as `Silicon Labs CP210x USB to UART Bridge`.

**Serial Monitor shows nothing after upload.** The ESP32 resets the moment upload
finishes, so `setup()` output is gone before you can switch tabs. Either open Serial
Monitor *before* uploading, or press **EN** (left button by the USB socket) to re-run
`setup()`. This is not a fault, and it wasted a lot of time before we worked it out.

**Charge-only USB cables.** If Windows shows no new device at all — not even an
unknown one — the cable has no data wires. Very common with cables bundled with
power banks.

**Unplug USB before rewiring.** Brushing 3V3 against GND while live triggers the
brownout detector (`BOD: Brownout detector was triggered`) and resets the board.
Repeated shorts eventually kill the regulator.

---

## 5. Wiring

`Dxx` on the silkscreen = `GPIOxx`. Same number, no conversion.

### IR obstacle sensor (FC-51 style)

| Module | ESP32 |
|---|---|
| VCC | **3V3** |
| GND | **GND** (left side) |
| OUT | **D27** |

Active **LOW** — OUT is HIGH when clear, LOW on detection.

### TCS34725 colour sensor

| Module | ESP32 |
|---|---|
| VIN | **3V3** |
| GND | **GND** (right side) |
| SDA | **D21** |
| SCL | **D22** |

Leave `3Vo`, `LED`, `INT` unconnected.

**`SDA` and `SCL` are not adjacent** — `RX0` and `TX0` sit between them. Wiring onto
those kills serial output entirely while uploads still work, which is a confusing
failure to diagnose.

### Pin reference, USB facing you

```
   LEFT SIDE                      RIGHT SIDE
   EN                             D23
   VP   (input only)              D22  ◀── TCS34725 SCL
   VN   (input only)              TX0     ⚠️ skip
   D34  (input only)              RX0     ⚠️ skip
   D35  (input only)              D21  ◀── TCS34725 SDA
   D32                            D19
   D33                            D18
   D25   (SG90 later)             D5
   D26   (MG996R later)           TX2
   D27  ◀── IR OUT                RX2
   D14   free                     D4
   D12                            D2   (onboard blue LED)
   GND  ◀── IR GND                D15
   D13   (buzzer later)           GND  ◀── TCS34725 GND
   VIN                            3V3  ◀── power for BOTH sensors
   └───────────────── USB ─────────────────┘
```

**`VP`, `VN`, `D34`, `D35` are input-only.** They compile fine as outputs and
silently do nothing.

**There is only one `3V3` pin.** Both sensors share it — run it to a breadboard rail
rather than forcing two jumpers into one hole.

---

## 6. Sketches, in the order to run them

| Sketch | Tests | Expected |
|---|---|---|
| `BlinkTest/` | Board + toolchain + serial | Blue LED blinks, prints `LED ON`/`LED OFF` |
| `IRSensorTest/` | IR alone | `OBJECT DETECTED` / `clear` |
| `ColourSensorTest/` | Colour alone, continuous | Rows of R/G/B/Clear/Lux; scans I2C on failure |
| `ItemScan/` | **Both together** — IR triggers one colour read | Startup check, then one row per item |
| `RoutingGateTest/` | SG90 gate, 3 angles | Type 1/2/3 in Serial Monitor |

Serial Monitor baud for all: **115200**.

`ItemScan` runs in IR-only mode if the colour sensor isn't connected, so each sensor
can be tested independently.

---

## 7. Power (for the servo stage — not yet built)

**Do not power servos from the ESP32 or from the L298N's 5V pin.** The L298N's 78M05
regulator supplies only 500 mA; an SG90 stalls at ~700 mA and an MG996R at ~2.5 A.

```
12V 3A adapter ──┬── L298N 12V ──────────▶ belt DC motor
                 │
                 └── 12V→5V buck (3A) ─┬─▶ SG90 servo
                                       └─▶ MG996R servo

USB from laptop ─────────────────────────▶ ESP32 (keep it here while developing)

           all grounds tied together
```

Servos need the **ESP32Servo** library — the standard `Servo` library is AVR-only and
will not compile.

---

## 8. Where things stand

Working: board, serial, IR sensor on D27, TCS34725 on D21/D22, combined `ItemScan`.

Not started: servos, HC-SR04, LEDs, buzzer, Wi-Fi, FastAPI backend.

Current task: collecting R/G/B/Clear readings for each demo material to find out
whether the classes separate well enough to classify. See §6 and §8 of
`PROJECT_PROGRESS.md` for the reasoning and next steps.
