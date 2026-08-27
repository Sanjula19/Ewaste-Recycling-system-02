// IR obstacle sensor test - FC-51 style 3-pin module (VCC / GND / OUT)
// ESP32 DevKit V1, Component 4 object-placement trigger.
//
// The module's OUT is ACTIVE LOW: it goes LOW when an object is detected
// and sits HIGH when the path is clear.

const int IR_PIN  = 27;   // sensor OUT
const int LED_PIN = 2;    // onboard blue LED mirrors the detection

bool lastState = false;

void setup() {
  Serial.begin(115200);
  pinMode(IR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("IR sensor test - move your hand in front of the sensor");
}

void loop() {
  bool detected = (digitalRead(IR_PIN) == LOW);   // active LOW

  digitalWrite(LED_PIN, detected ? HIGH : LOW);

  // only print on change, so the monitor stays readable
  if (detected != lastState) {
    Serial.println(detected ? "OBJECT DETECTED" : "clear");
    lastState = detected;
  }

  delay(50);
}
