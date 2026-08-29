/*
 * ESP32 Data Collection Sketch
 * ==============================
 * E-Waste Toxic Gas Detection System
 * Author: Sanjula Madushanka
 *
 * PURPOSE: Reads all 5 MQ sensors + DHT22 and prints
 *          one CSV row every 2 seconds to Serial.
 *          Used ONLY for collecting training data.
 *          (Different from the final MQTT firmware)
 *
 * WIRING (same as main system):
 *   MQ-2   -> GPIO 34
 *   MQ-7   -> GPIO 35
 *   MQ-135 -> GPIO 32
 *   MQ-303 -> GPIO 33
 *   MQ-136 -> GPIO 25
 *   DHT22  -> GPIO 4
 *
 * HOW TO USE:
 *   1. Flash this to ESP32
 *   2. Open Serial Monitor (baud: 115200)
 *   3. Run the Python collector script on your laptop
 *   4. The Python script handles labelling automatically
 *
 * VOLTAGE DIVIDER REMINDER:
 *   MQ sensors output 5V -- use 10k/20k divider before ADC pin!
 *   ESP32 ADC max = 3.3V
 */

#include <DHT.h>

// ── Pin Definitions ──────────────────────────────────────
#define MQ2_PIN    34
#define MQ7_PIN    35
#define MQ135_PIN  32
#define MQ303_PIN  33
#define MQ136_PIN  25
#define DHT_PIN     4
#define DHT_TYPE   DHT22

// ── Constants ────────────────────────────────────────────
#define ADC_MAX       4095.0
#define VREF          3.3
#define RL_VALUE      10.0    // Load resistor value in kOhm (on sensor board)
#define INTERVAL_MS   2000    // One reading every 2 seconds

DHT dht(DHT_PIN, DHT_TYPE);

// ── Rs/R0 calibration ratios (from datasheet clean air) ──
// Calibrate these in a clean-air environment before collecting data
// Run calibration session (gas class = CLEAN) first to find your R0 values
// Default values below are approximate -- replace with your calibrated values
float R0_MQ2   = 10.0;
float R0_MQ7   = 10.0;
float R0_MQ135 = 10.0;
float R0_MQ303 = 10.0;
float R0_MQ136 = 10.0;

// ── Read raw ADC and convert to voltage ──────────────────
float readVoltage(int pin) {
  // Average 10 readings for stability
  long sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(pin);
    delay(5);
  }
  float avg = sum / 10.0;
  return (avg / ADC_MAX) * VREF;
}

// ── Convert voltage to Rs/R0 ratio ───────────────────────
// Rs = ((Vc - Vout) / Vout) * RL
// ppm_proxy = Rs/R0  (lower = more gas)
float voltageToRatio(float voltage, float R0) {
  if (voltage <= 0.01) return 0.0;  // Avoid divide by zero
  float Vc  = VREF;
  float Rs  = ((Vc - voltage) / voltage) * RL_VALUE;
  return Rs / R0;
}

// ── Simple ppm approximation ──────────────────────────────
// For data collection purposes -- not calibrated ppm
// Real calibration requires reference gas
float ratioToPPM_MQ2(float ratio) {
  // From MQ-2 datasheet curve approximation: ppm = a * ratio^b
  return 574.25 * pow(ratio, -2.222);
}

float ratioToPPM_MQ7(float ratio) {
  // CO detection curve
  return 99.042 * pow(ratio, -1.518);
}

float ratioToPPM_MQ135(float ratio) {
  // NH3/VOC curve
  return 102.2 * pow(ratio, -2.473);
}

float ratioToPPM_MQ303(float ratio) {
  // Mercury vapor approximation (mg/m3)
  return 0.005 * ratio;
}

float ratioToPPM_MQ136(float ratio) {
  // H2S curve
  return 116.6020682 * pow(ratio, -2.769034857);
}

// ── Setup ─────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(2000);
  dht.begin();

  // Print CSV header (Python script reads this)
  Serial.println("mq2_ppm,mq7_ppm,mq135_ppm,mq303_ppm,mq136_ppm,temperature_c,humidity_pct");

  // Warm-up period (MQ sensors need 30-60 sec warm-up)
  Serial.println("#WARMUP:Sensors warming up for 30 seconds...");
  for (int i = 30; i > 0; i--) {
    Serial.print("#WARMUP:");
    Serial.println(i);
    delay(1000);
  }
  Serial.println("#READY:Sensors ready. Starting data collection.");
}

// ── Main Loop ─────────────────────────────────────────────
void loop() {
  // Read sensors
  float v2   = readVoltage(MQ2_PIN);
  float v7   = readVoltage(MQ7_PIN);
  float v135 = readVoltage(MQ135_PIN);
  float v303 = readVoltage(MQ303_PIN);
  float v136 = readVoltage(MQ136_PIN);

  // Convert to ratios
  float r2   = voltageToRatio(v2,   R0_MQ2);
  float r7   = voltageToRatio(v7,   R0_MQ7);
  float r135 = voltageToRatio(v135, R0_MQ135);
  float r303 = voltageToRatio(v303, R0_MQ303);
  float r136 = voltageToRatio(v136, R0_MQ136);

  // Convert to ppm
  float ppm2   = ratioToPPM_MQ2(r2);
  float ppm7   = ratioToPPM_MQ7(r7);
  float ppm135 = ratioToPPM_MQ135(r135);
  float ppm303 = r303 * 0.05;      // Mercury: direct ratio × scale
  float ppm136 = ratioToPPM_MQ136(r136);

  // Read DHT22
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  // Handle DHT read failure
  if (isnan(temp)) temp = 28.0;
  if (isnan(hum))  hum  = 65.0;

  // Print ONE CSV data row (Python script captures this)
  Serial.print(ppm2,   4); Serial.print(",");
  Serial.print(ppm7,   4); Serial.print(",");
  Serial.print(ppm135, 4); Serial.print(",");
  Serial.print(ppm303, 4); Serial.print(",");
  Serial.print(ppm136, 4); Serial.print(",");
  Serial.print(temp,   2); Serial.print(",");
  Serial.println(hum,  2);

  delay(INTERVAL_MS);
}
