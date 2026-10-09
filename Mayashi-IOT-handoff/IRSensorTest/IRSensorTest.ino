// HW-201 / FC-51 IR Sensor Test
// ESP32 DevKit V1
// OUT -> GPIO 27

const int IR_PIN = 27;

void setup() {
  Serial.begin(115200);
  pinMode(IR_PIN, INPUT);

  Serial.println("IR Sensor Test");
  Serial.println("Place an object in front of the sensor.");
}

void loop() {
  int sensorState = digitalRead(IR_PIN);

  if (sensorState == LOW) {
    Serial.println("OBJECT DETECTED");
  } else {
    Serial.println("CLEAR");
  }

  delay(500);
}