// Blink test - ESP32 DevKit V1 onboard blue LED
// Confirms the board, the COM8 port, and the toolchain all work
// before any sensors or servos are wired up.

const int LED_PIN = 2;   // onboard blue LED on most ESP32 DevKit boards

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("Blink test started");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  Serial.println("LED ON");
  delay(500);

  digitalWrite(LED_PIN, LOW);
  Serial.println("LED OFF");
  delay(500);
}
