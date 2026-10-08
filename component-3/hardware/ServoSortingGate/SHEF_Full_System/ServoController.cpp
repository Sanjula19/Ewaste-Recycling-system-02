#include <Arduino.h>
#include <ESP32Servo.h>
#include "config.h"
#include "ServoController.h"

// ============================================================
//  SERVO CONTROLLER
//  Role: physically executes the sort decision made by
//  MoistureSensor's isWet(). Direction: DRY -> LEFT, WET -> RIGHT.
// ============================================================

static Servo sortingServo;

void servoInit() {
  ESP32PWM::allocateTimer(0);
  sortingServo.setPeriodHertz(50);

  delay(1000); // let power rails stabilize before attaching — prevents boot jerk

  sortingServo.attach(SERVO_PIN, 500, 2400);
  sortingServo.write(HOME_ANGLE);
  delay(1000);
}

void moveServo(int angle) {
  Serial.print("Servo -> ");
  Serial.print(angle);
  Serial.println(" degrees");

  sortingServo.write(angle);
  delay(700); // give the servo time to physically complete the move
}

void servoGoHome() {
  sortingServo.write(HOME_ANGLE);
}

void sortItem(bool wet) {
  Serial.println();
  Serial.println("--------- SORTING ---------");

  if (wet) {
    Serial.println("RESULT: WET");
    Serial.println("Moving to WET bin (RIGHT)...");
    moveServo(WET_ANGLE);
  } else {
    Serial.println("RESULT: DRY");
    Serial.println("Moving to DRY bin (LEFT)...");
    moveServo(DRY_ANGLE);
  }

  Serial.println("Holding gate...");
  delay(SORT_HOLD_TIME);

  Serial.println("Returning to HOME...");
  servoGoHome();
  delay(HOME_SETTLE_TIME);

  Serial.println("HOME position reached.");
}
