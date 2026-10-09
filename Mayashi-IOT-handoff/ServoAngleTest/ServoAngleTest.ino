#include <ESP32Servo.h>

const int SERVO_PIN = 26;     // servo signal wire connected to GPIO D26
const int STOP_ANGLE = 90;     // fixed stop angle for the gate

Servo gateServo;

void moveToAngle(int angle) {
  gateServo.write(angle);
  Serial.print("Servo angle: ");
  Serial.print(angle);
  Serial.println(" deg");
  delay(500);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  gateServo.attach(SERVO_PIN, 500, 2400);

  Serial.println("Servo angle test - signal on D26");
  Serial.print("Holding at fixed angle: ");
  Serial.print(STOP_ANGLE);
  Serial.println(" deg");
  Serial.println();
}

void loop() {
  moveToAngle(STOP_ANGLE);
  Serial.println("Servo is holding position.");
  Serial.println();
  delay(2000);
}
