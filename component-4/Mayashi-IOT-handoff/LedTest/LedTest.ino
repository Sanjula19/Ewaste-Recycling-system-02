// Status LED test - Component 4
//
// Three status LEDs, per report section 6.1:
//   GREEN  (D21) = SELL
//   YELLOW (D22) = HOLD / crushing
//   RED    (D4)  = BIN FULL (lockout)
//
// Wiring for each LED:
//   ESP32 pin --[ 220 ohm ]--|>|-- GND
//                             ^
//        long leg (+) toward the resistor, short leg (-) to ground.
//        Backwards it just won't light - it won't be damaged.
//
// On startup all three blink together once, so you can see at a glance
// whether any of them is wired wrong. Then type 1/2/3/0 in the Serial
// Monitor to hold each state, the same way RoutingGateTest works.

const int LED_GREEN  = 21;   // board pin D21 - SELL
const int LED_YELLOW = 22;   // board pin D22 - HOLD / crushing
const int LED_RED    = 4;    // board pin D4  - BIN FULL

void allOff() {
  digitalWrite(LED_GREEN,  LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED,    LOW);
}

// Only one status is ever true at a time, so every state change starts
// from all-off. Keeps the panel from ever showing two verdicts at once.
void showState(int pin, const char *label) {
  allOff();
  if (pin >= 0) digitalWrite(pin, HIGH);
  Serial.print("state -> ");
  Serial.println(label);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_GREEN,  OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED,    OUTPUT);

  // Startup self-test: each LED alone, then all three together.
  Serial.println("--- LED self test ---");

  Serial.println("GREEN  (D21)");
  showState(LED_GREEN, "SELL");
  delay(700);

  Serial.println("YELLOW (D22)");
  showState(LED_YELLOW, "HOLD");
  delay(700);

  Serial.println("RED    (D4)");
  showState(LED_RED, "BIN FULL");
  delay(700);

  Serial.println("all three together");
  digitalWrite(LED_GREEN,  HIGH);
  digitalWrite(LED_YELLOW, HIGH);
  digitalWrite(LED_RED,    HIGH);
  delay(900);
  allOff();

  Serial.println("---------------------");
  Serial.println("Any LED that stayed dark is wired wrong or reversed.");
  Serial.println();
  Serial.println("Type:  1 = SELL (green)   2 = HOLD (yellow)");
  Serial.println("       3 = BIN FULL (red) 0 = all off");
}

void loop() {
  if (!Serial.available()) return;

  char c = Serial.read();
  switch (c) {
    case '1': showState(LED_GREEN,  "SELL (green)");     break;
    case '2': showState(LED_YELLOW, "HOLD (yellow)");    break;
    case '3': showState(LED_RED,    "BIN FULL (red)");   break;
    case '0': showState(-1,         "all off");          break;
  }
}
