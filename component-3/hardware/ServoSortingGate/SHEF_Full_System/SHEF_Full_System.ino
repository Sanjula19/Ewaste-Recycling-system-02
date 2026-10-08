/*
 * ============================================================
 *  SHEF IoT — MOISTURE SORTING SYSTEM (Main Sketch)
 *  Project R26-IT-015 | Component 3
 * ============================================================
 *
 *  FILE STRUCTURE:
 *    SHEF_Full_System.ino    - this file: setup(), loop(), orchestration
 *    config.h                 - ALL pins, calibration, timing constants
 *    UltrasonicSensor.h/.cpp  - distance detection (WHEN an item arrives)
 *    MoistureSensor.h/.cpp    - moisture read + wet/dry decision (WHERE it sorts)
 *    ServoController.h/.cpp   - physical servo movement + sorting action
 *
 *  IMPORTANT: this folder must be named exactly "SHEF_Full_System"
 *  (matching this .ino file's name) for Arduino IDE to open it
 *  correctly and see the other tabs.
 *
 *  TO CALIBRATE: open config.h — that is the ONLY file you should
 *  need to edit for tuning angles, thresholds, or timing.
 * ============================================================
 */

#include "config.h"
#include "UltrasonicSensor.h"
#include "MoistureSensor.h"
#include "ServoController.h"

void testSensors();
void waitForObjectToLeave();

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("======================================");
  Serial.println(" SHEF IoT MOISTURE SORTING SYSTEM");
  Serial.println("======================================");

  ultrasonicInit();
  moistureInit();
  servoInit();

  Serial.println();
  Serial.print("Dry reference: ");
  Serial.println(MOISTURE_DRY_REF);

  Serial.print("Wet reference: ");
  Serial.println(MOISTURE_WET_REF);
  if (MOISTURE_WET_REF == 2400) {
    Serial.println("  [WARNING] This is still the PLACEHOLDER value — calibrate it in config.h!");
  }

  Serial.print("Moisture threshold: ");
  Serial.println(MOISTURE_THRESHOLD);

  Serial.println();
  Serial.println("Servo HOME test:");
  Serial.print("HOME angle = ");
  Serial.println(HOME_ANGLE);
  Serial.println();

  testSensors();

  Serial.println();
  Serial.println("======================================");
  Serial.println(" SYSTEM READY");
  Serial.println("======================================");
}


// ============================================================
//  STARTUP SENSOR CHECK
// ============================================================
void testSensors() {
  Serial.println("Testing moisture sensor...");
  int moisture = readMoisture();
  Serial.print("Moisture ADC = ");
  Serial.println(moisture);

  if (moistureValid(moisture)) {
    Serial.println("Moisture sensor: OK");
  } else {
    Serial.println("Moisture sensor: CHECK WIRING");
  }

  Serial.println("Testing ultrasonic...");
  float distance = readDistance();

  if (distance < 0) {
    Serial.println("Ultrasonic: NO ECHO");
  } else {
    Serial.print("Distance = ");
    Serial.print(distance);
    Serial.println(" cm");
  }
}


// ============================================================
//  WAIT FOR OBJECT TO LEAVE (prevents re-triggering same item)
// ============================================================
void waitForObjectToLeave() {
  Serial.println("Waiting for object to leave...");

  unsigned long start = millis();

  while (millis() - start < 5000) { // 5 second safety timeout
    float distance = readDistance();

    if (distance < 0 || distance >= DETECTION_DISTANCE) {
      Serial.println("Object left detection area.");
      delay(500);
      return;
    }

    delay(OBJECT_CHECK_DELAY);
  }

  Serial.println("Object wait timeout.");
}


// ============================================================
//  MAIN LOOP
// ============================================================
void loop() {
  float distance = readDistance();

  // ---- NO OBJECT: hold gate at home ----
  if (distance < 0 || distance >= DETECTION_DISTANCE) {
    servoGoHome();
    delay(150);
    return;
  }

  // ---- OBJECT DETECTED ----
  Serial.println();
  Serial.println("======================================");
  Serial.print("OBJECT DETECTED: ");
  Serial.print(distance);
  Serial.println(" cm");
  Serial.println("======================================");

  Serial.println("Waiting for object to settle...");
  delay(SETTLE_TIME);

  // ---- Read moisture (STABLE — waits until the value stops moving) ----
  Serial.println("Waiting for moisture reading to stabilize...");
  int moisture = readMoistureStable();
  Serial.print("Moisture ADC (stable): ");
  Serial.println(moisture);

  // ---- Sensor health check ----
  if (!moistureValid(moisture)) {
    Serial.println();
    Serial.println("ERROR: INVALID MOISTURE READING");
    Serial.println("Sorting cancelled.");

    servoGoHome();
    delay(HOME_SETTLE_TIME);
    waitForObjectToLeave();
    return;
  }

  // ---- Classification (this is what actually drives the servo) ----
  Serial.print("Threshold: ");
  Serial.println(MOISTURE_THRESHOLD);
  Serial.print("Direction: wet=");
  Serial.println(WET_IS_HIGHER ? "higher" : "lower");

  bool wet = isWet(moisture);

  if (wet) {
    Serial.println("CLASSIFICATION: WET");
  } else {
    Serial.println("CLASSIFICATION: DRY");
  }

  // ---- SORT ----
  sortItem(wet);

  // ---- Prevent the same object from triggering again ----
  waitForObjectToLeave();

  Serial.println();
  Serial.println("Cycle complete.");
  Serial.println("Ready for next item.");
  delay(300);
}
