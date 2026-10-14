#include <Arduino.h>
#include "config.h"
#include "UltrasonicSensor.h"

// ============================================================
//  ULTRASONIC SENSOR (HC-SR04)
//  Role: WHEN — detects item presence only. Does not influence
//  the wet/dry decision in any way; that comes from MoistureSensor.
// ============================================================

void ultrasonicInit() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT);

  if (duration == 0) {
    return -1;  // no echo received — treat as "nothing detected"
  }

  return duration * 0.0343 / 2.0;
}
