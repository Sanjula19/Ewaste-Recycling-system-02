# 04 — Hardware Architecture

## 4.1 Component List

| Component | Model | Quantity | Purpose |
|-----------|-------|----------|---------|
| Microcontroller | ESP32 DevKit V1 | 1 | Main controller: ADC, WiFi, MQTT |
| Gas Sensor | MQ-2 | 1 | LPG, Propane, Methane, Smoke |
| Gas Sensor | MQ-7 | 1 | Carbon Monoxide (CO) |
| Gas Sensor | MQ-135 | 1 | Benzene, Ammonia, CO₂, Alcohol |
| Gas Sensor | MQ-303A | 1 | Mercury Vapor, Alcohol |
| Gas Sensor | MQ-136 | 1 | Hydrogen Sulphide (H₂S) |
| Env. Sensor | DHT22 | 1 | Temperature + Humidity (calibration) |
| Display | LCD 16×2 I2C | 1 | Local reading display |
| Indicator | LED (Red) | 1 | DANGER alert |
| Indicator | LED (Yellow) | 1 | CAUTION alert |
| Indicator | LED (Green) | 1 | SAFE status |
| Alert | Active Buzzer | 1 | Audible danger alarm |
| Resistors | 220Ω | 3 | LED current limiting |
| Power | USB 5V/2A Adapter | 1 | System power |
| Misc | Breadboard + Jumper wires | — | Prototyping |
| Misc | 10kΩ resistor | 1 | DHT22 pull-up |

---

## 4.2 ESP32 Pin Assignment Table

| GPIO Pin | Type | Connected To | Notes |
|----------|------|-------------|-------|
| GPIO 34 | Analog Input | MQ-2 AOUT | ADC1_CH6, input only |
| GPIO 35 | Analog Input | MQ-7 AOUT | ADC1_CH7, input only |
| GPIO 32 | Analog Input | MQ-135 AOUT | ADC1_CH4 |
| GPIO 33 | Analog Input | MQ-303 AOUT | ADC1_CH5 |
| GPIO 25 | Analog Input | MQ-136 AOUT | ADC1_CH8 (DAC1, avoid DAC mode) |
| GPIO 4 | Digital I/O | DHT22 Data | Pull-up 10kΩ to 3.3V |
| GPIO 21 | I2C SDA | LCD I2C SDA | Hardware I2C bus |
| GPIO 22 | I2C SCL | LCD I2C SCL | Hardware I2C bus |
| GPIO 26 | Digital Output | Red LED | Via 220Ω resistor to GND |
| GPIO 27 | Digital Output | Yellow LED | Via 220Ω resistor to GND |
| GPIO 14 | Digital Output | Green LED | Via 220Ω resistor to GND |
| GPIO 13 | Digital Output | Active Buzzer | Direct connection |
| 3.3V | Power | DHT22 VCC | — |
| 5V (VIN) | Power | MQ sensors VCC | All MQ sensors need 5V |
| 5V (VIN) | Power | LCD VCC | I2C backpack runs on 5V |
| GND | Ground | All components | Common ground |

> ⚠️ **Important:** ESP32 ADC pins only accept **0–3.3V**. MQ sensors output up to 5V. Use a **voltage divider** (10kΩ + 20kΩ) on each sensor AOUT line to step down to 0–3.3V.

---

## 4.3 Circuit Voltage Divider (for each MQ sensor)

```
MQ Sensor AOUT (0–5V)
         │
        [10kΩ]
         │
         ├──────────── To ESP32 GPIO (0–3.3V safe)
         │
        [20kΩ]
         │
        GND
```

Voltage at ESP32 pin = 5V × (20kΩ / (10kΩ + 20kΩ)) = **3.33V max** ✅

---

## 4.4 MQ Sensor Warm-Up and Calibration

### 4.4.1 Warm-Up Requirements
| Sensor | Warm-Up Time | Operating Voltage | Heater Current |
|--------|-------------|------------------|---------------|
| MQ-2 | 30 seconds | 5V | ~160mA |
| MQ-7 | 60 seconds | 5V / 1.4V (cycle) | ~150mA (5V phase) |
| MQ-135 | 20 seconds | 5V | ~35mA |
| MQ-303A | 30 seconds | 3.3V | ~25mA |
| MQ-136 | 30 seconds | 5V | ~60mA |

> **MQ-7 special handling:** Requires **voltage cycling** — HIGH voltage (5V, 60sec) then LOW voltage (1.4V, 90sec) for accurate CO measurement. Implement in firmware using a state machine.

### 4.4.2 Calibration Formula
```
Vout  = ADC_reading × (3.3V / 4095)       # ADC to voltage
Rs    = ((Vc × RL) / Vout) - RL           # Sensor resistance
                                            # RL = load resistor value (varies per MQ)
ratio = Rs / R0                            # R0 = baseline in clean air
ppm   = a × ratio^b                       # a, b from datasheet curve
```

Where `R0` is measured in **clean air** during calibration setup.

---

## 4.5 Hardware Block Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
  Clean Air ───►  [MQ-2]   [MQ-7]  [MQ-135] [MQ-303] [MQ-136]  │
  + E-waste       AOUT     AOUT     AOUT      AOUT      AOUT     │
  gases            │        │        │         │         │        │
                   └────────┴────────┴─────────┴─────────┘        │
                            │ (5V→3.3V voltage dividers)          │
                            ▼                                      │
                   ┌────────────────────────────────────────┐     │
                   │         ESP32 DevKit V1                │     │
                   │                                        │     │
                   │  ADC → Read sensor voltages            │     │
                   │  Math → Convert to ppm                 │     │
                   │  GPIO4 ← DHT22 (Temp/Humidity)        │     │
                   │  I2C  → LCD 16x2 display              │     │
                   │  GPIO → LEDs (R/Y/G) + Buzzer         │     │
                   │  WiFi → MQTT publish to HiveMQ        │     │
                   │  MQTT subscribe → commands from API   │     │
                   └────────────────────────────────────────┘     │
                       │        │        │        │                │
                      LCD      LED-R   LED-Y   LED-G + Buzzer     │
                   [display] [danger] [warn]   [safe]  [alarm]    │
                                                                   │
                    ──────────────────────────────────────────────┘
```

---

## 4.6 Firmware State Machine

```
┌─────────────────────────────────────────────────────────┐
│                  FIRMWARE STATES                        │
│                                                         │
│  STARTUP ──► WARM_UP (60s) ──► CALIBRATE ──► RUNNING   │
│                                                   │     │
│         ┌─────────────────────────────────────────┘     │
│         ▼                                               │
│  RUNNING LOOP (every 5 seconds):                       │
│    1. Read all 5 sensor ADC values                     │
│    2. Read DHT22 temperature + humidity                 │
│    3. Convert ADC → voltage → Rs → ppm                 │
│    4. Update LCD display                                │
│    5. Publish JSON via MQTT                             │
│    6. Subscribe for command messages                    │
│    7. If command received → update LEDs/Buzzer         │
│    8. Wait 5 seconds → loop                            │
└─────────────────────────────────────────────────────────┘
```

---

## 4.7 Power Budget

| Component | Supply | Current Draw |
|-----------|--------|-------------|
| ESP32 (WiFi active) | 5V USB | ~240mA |
| MQ-2 | 5V | 160mA |
| MQ-7 | 5V | 150mA (high phase) |
| MQ-135 | 5V | 35mA |
| MQ-303A | 3.3V | 25mA |
| MQ-136 | 5V | 60mA |
| DHT22 | 3.3V | 1.5mA |
| LCD + backpack | 5V | 30mA |
| LEDs × 3 | 3.3V | ~30mA total |
| Buzzer | 3.3V | 30mA |
| **TOTAL** | **5V USB** | **~760mA peak** |

> ✅ A **5V / 2A USB adapter** safely powers the entire system with ~1.24A headroom.

---

## 4.8 Physical Enclosure Design

```
┌─────────────────────────────┐
│   E-WASTE GAS MONITOR BOX   │
│                             │
│  ┌───────────────────────┐  │
│  │  LCD: CO | 12ppm SAFE │  │
│  └───────────────────────┘  │
│                             │
│  [🟢]  [🟡]  [🔴]          │← Status LEDs
│                             │
│  [SENSOR MESH VENTS]        │← Allow air to reach MQ sensors
│  ■■■■■■■■■■■■■■■■■■■■■    │
│                             │
│  USB-C Power ──────────── ○ │
└─────────────────────────────┘
  Approx size: 15cm × 10cm × 6cm
```
