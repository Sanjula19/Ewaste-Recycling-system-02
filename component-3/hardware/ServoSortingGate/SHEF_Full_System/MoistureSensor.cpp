#include <Arduino.h>
#include "config.h"
#include "MoistureSensor.h"

// ============================================================
//  MOISTURE SENSOR (Capacitive)
//  Role: WHERE — this is what actually decides DRY vs WET,
//  and therefore which side the servo sorts the item to.
// ============================================================

void moistureInit() {
  pinMode(MOISTURE_PIN, INPUT);
}

int readMoisture() {
  long total = 0;

  for (int i = 0; i < MOISTURE_SAMPLES; i++) {
    total += analogRead(MOISTURE_PIN);
    delay(20);
  }

  return total / MOISTURE_SAMPLES;
}

int readMoistureStable() {
  unsigned long startTime = millis();
  int lastVal = readMoisture();
  int stableCount = 0;

  while (millis() - startTime < MAX_STABILIZE_TIME) {
    delay(200);
    int currentVal = readMoisture();
    int drift = abs(currentVal - lastVal);

    if (drift < STABLE_DRIFT) {
      stableCount++;
      if (stableCount >= STABLE_READS_NEEDED) {
        return currentVal;   // confirmed stable
      }
    } else {
      stableCount = 0;       // still moving, reset the streak
    }
    lastVal = currentVal;
  }

  Serial.println("  [WARN] Reading did not fully stabilize within timeout — using last value.");
  return lastVal;
}

bool moistureValid(int value) {
  if (value < MOISTURE_MIN_VALID) return false;
  if (value > MOISTURE_MAX_VALID) return false;
  return true;
}

bool isWet(int value) {
  if (WET_IS_HIGHER) {
    return value > MOISTURE_THRESHOLD;
  } else {
    return value < MOISTURE_THRESHOLD;
  }
}
