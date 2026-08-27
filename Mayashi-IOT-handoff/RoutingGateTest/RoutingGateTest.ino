// SG90 routing gate test - Component 4
// Type 1, 2 or 3 in Serial Monitor to send the gate to each bin position,
// so you can tune the angles against the real chute before wiring the logic.
//
// Needs the ESP32Servo library (NOT the standard Servo library - that one
// is AVR-only and will not compile for ESP32).

#include <ESP32Servo.h>

const int SERVO_PIN = 25;   // board pin D25

// Tune these once the chute is built.
// Avoid 0 and 180 - servos buzz and stall against their end stops.
const int ANGLE_MARKET    = 30;    // SELL    -> market liquidation bin
const int ANGLE_COMPACTOR = 90;    // HOLD    -> compactor, MG996R crushes
const int ANGLE_PYROLYSIS = 150;   // polymer -> pyrolysis feedstock

Servo gate;

void moveGate(int angle, const char *label) {
  gate.write(angle);
  Serial.print("gate -> ");
  Serial.print(label);
  Serial.print("  (");
  Serial.print(angle);
  Serial.println(" deg)");
  delay(600);            // let it physically arrive before accepting the next
}

void setup() {
  Serial.begin(115200);

  ESP32PWM::allocateTimer(0);      // required on ESP32
  gate.setPeriodHertz(50);         // standard 50Hz servo frame
  gate.attach(SERVO_PIN, 500, 2400);   // SG90 pulse range in microseconds

  moveGate(ANGLE_COMPACTOR, "CENTRE (home)");
  Serial.println("Type 1 = market/SELL, 2 = compactor/HOLD, 3 = pyrolysis");
}

void loop() {
  if (!Serial.available()) return;

  char c = Serial.read();
  switch (c) {
    case '1': moveGate(ANGLE_MARKET,    "MARKET / SELL");    break;
    case '2': moveGate(ANGLE_COMPACTOR, "COMPACTOR / HOLD"); break;
    case '3': moveGate(ANGLE_PYROLYSIS, "PYROLYSIS");        break;
  }
}
