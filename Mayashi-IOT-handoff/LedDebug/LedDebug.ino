// LED debug - blinks all three status pins FOREVER.
//
// Use this instead of LedTest when an LED won't light and you need to
// know whether the problem is the wiring or the code. There is no
// startup-only sequence to miss here and nothing to type: every pin
// blinks on a loop for as long as the board is powered.
//
// Plug your LED into D19, D23 or D4 in turn - whichever pin it is on,
// it should blink within 3 seconds.
//
// The onboard blue LED (GPIO 2) blinks with them. That one is soldered
// to the board, so if IT blinks the sketch is definitely running and any
// dark LED is a wiring problem, not a code problem.

const int LED_GREEN  = 19;
const int LED_YELLOW = 23;
const int LED_RED    = 4;
const int LED_ONBOARD = 2;   // soldered to the board - our reference

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(LED_GREEN,   OUTPUT);
  pinMode(LED_YELLOW,  OUTPUT);
  pinMode(LED_RED,     OUTPUT);
  pinMode(LED_ONBOARD, OUTPUT);

  Serial.println("LED debug - each pin blinks in turn, forever.");
  Serial.println("If the onboard BLUE led blinks, the sketch is running.");
  Serial.println("Any external LED that stays dark is a WIRING problem.");
}

void pulse(int pin, const char *label) {
  digitalWrite(pin, HIGH);
  digitalWrite(LED_ONBOARD, HIGH);
  Serial.print("ON  -> ");
  Serial.println(label);
  delay(1000);

  digitalWrite(pin, LOW);
  digitalWrite(LED_ONBOARD, LOW);
  delay(400);
}

void loop() {
  pulse(LED_GREEN,  "D19  (green / SELL)");
  pulse(LED_YELLOW, "D23  (yellow / HOLD)");
  pulse(LED_RED,    "D4   (red / BIN FULL)");
}
