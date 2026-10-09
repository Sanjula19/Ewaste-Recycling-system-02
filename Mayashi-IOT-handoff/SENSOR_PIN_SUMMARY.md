# Sensor and Pin Summary

This summary reflects the current ESP32 wiring used in the project firmware and setup notes.

## ESP32 Board
- Board: ESP32 DevKit V1
- USB-facing pin naming: `Dxx` matches `GPIOxx` except `RX2/TX2`, which are `GPIO16` and `GPIO17`

## Current confirmed sensor mapping

### 1) TCS34725 colour sensor
| Sensor pin | ESP32 pin | Notes |
|---|---:|---|
| VIN | 3V3 | Shared 3.3V rail |
| GND | GND | Shared ground |
| SDA | GPIO 16 (RX2) | Current project firmware uses this |
| SCL | GPIO 17 (TX2) | Current project firmware uses this |

Notes:
- The firmware uses `PIN_SDA = 16` and `PIN_SCL = 17`.
- The setup guide originally mentioned D21/D22, but the working hardware mapping in the code is RX2/TX2.

### 2) IR obstacle sensor (FC-51 style)
| Sensor pin | ESP32 pin | Notes |
|---|---:|---|
| VCC | 3V3 | Power |
| GND | GND | Ground |
| OUT | GPIO 27 | Active LOW |

Notes:
- This is the arrival trigger in the main firmware (`USE_IR 1`), mounted
  ahead of the colour sensor on the conveyor belt. On detection the
  colour sensor reads the item as it passes, the reading is POSTed to the
  backend, and the gate (servo, GPIO 26) does one release motion to drop
  the item into the single bin. Every material goes to the same bin for
  now -- routing to separate bins by material is a later step.
- It reads HIGH when clear and LOW when an object blocks the beam.

### 3) HC-SR04 ultrasonic sensor (bin level)
| Sensor pin | ESP32 pin | Notes |
|---|---:|---|
| VCC | 3V3 or VIN depending on wiring | Main firmware expects 3.3V compatible use |
| GND | GND | Ground |
| TRIG | GPIO 5 | Output |
| ECHO | GPIO 22 | Through divider as noted in the project |

Notes:
- The project uses a 1k/2k divider on the echo line before it reaches the ESP32.
- This sensor is used for bin fullness monitoring.

### 4) SG90 gate servo
| Servo pin | ESP32 pin | Notes |
|---|---:|---|
| Signal | GPIO 26 | Gate servo (per `ServoAngleTest.ino`) |
| VCC | 5V via dedicated buck supply | Do not power from ESP32 5V |
| GND | GND | Shared ground |

Notes:
- Uses the `ESP32Servo` library.
- Single bin for now: the gate does the same release motion for every
  item regardless of material -- `GATE_HOME` (90°, per `ServoAngleTest.ino`)
  is the resting position, `GATE_RELEASE` (60°, a placeholder) swings it
  to drop the item, then it returns to `GATE_HOME`. Diverting to separate
  bins by material/decision is a later step.
- GPIO 26 was previously reserved for the MG996R crusher; that moved to
  GPIO 14 to free this pin for the gate.

### 5) Crusher servo
| Servo pin | ESP32 pin | Notes |
|---|---:|---|
| Signal | GPIO 14 | Crusher servo -- wired |
| VCC | 5V via dedicated buck supply | Do not power from ESP32 5V |
| GND | GND | Shared ground |

Notes:
- `USE_CRUSHER 1` in `main.ino`. Runs on HOLD material only, after the
  item has already been released into the single bin -- independent of
  which bin it ends up in.
- Stroke is fixed in `runCrusher()`: press to 120°, release to 20°.

### 6) Status LEDs
| LED | ESP32 pin | Purpose |
|---|---:|---|
| Green | GPIO 21 | SELL / dispatched |
| Yellow | GPIO 18 | HOLD / crushing |
| Red | GPIO 4 | BIN FULL / lockout |
| Onboard blue LED | GPIO 2 | Boot / debug indicator |

### 7) Other pins noted in docs
| Function | ESP32 pin | Notes |
|---|---:|---|
| D19 | GPIO 19 | Intentionally unused |
| D23 | GPIO 23 | Intentionally unused |
| D35 | GPIO 35 | Input only; not used |
| D34 | GPIO 34 | Input only; not used |
| VP/VN | Input only | Not used |

## Quick reference table

| Device | GPIO |
|---|---:|
| TCS34725 SDA | 16 |
| TCS34725 SCL | 17 |
| IR OUT | 27 |
| Green LED | 21 |
| Yellow LED | 18 |
| Red LED | 4 |
| Ultrasonic TRIG | 5 |
| Ultrasonic ECHO | 22 |
| Diverter gate servo | 26 |
| Crusher servo | 14 |
| Onboard LED | 2 |

## Important hardware warning
- Do not power servos from the ESP32 5V rail.
- Use a dedicated 5V supply for the servos and tie the grounds together.
- Keep the colour sensor and IR sensor on the correct rails to avoid poor readings or brownout resets.
