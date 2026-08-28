// All LEDs ON, held steady - Component 4
//
// The simplest possible wiring test: every status LED is switched on in
// setup() and left on. Nothing blinks, nothing cycles, nothing has to be
// typed - so there is no timing to miss and no sequence to misread.
//
// Look at the board: any LED that is dark has a wiring or pin fault.
// The onboard blue LED is driven too, as a reference - if IT is lit, the
// sketch is definitely running and every dark lamp is hardware.

const int LED_GREEN   = 21;   // D21 - SELL
const int LED_YELLOW  = 22;   // D22 - HOLD
const int LED_RED     = 4;    // D4  - BIN FULL
const int LED_ONBOARD = 2;    // soldered to the board - cannot be miswired

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(LED_GREEN,   OUTPUT);
  pinMode(LED_YELLOW,  OUTPUT);
  pinMode(LED_RED,     OUTPUT);
  pinMode(LED_ONBOARD, OUTPUT);

  digitalWrite(LED_GREEN,   HIGH);
  digitalWrite(LED_YELLOW,  HIGH);
  digitalWrite(LED_RED,     HIGH);
  digitalWrite(LED_ONBOARD, HIGH);

  Serial.println("All LEDs held ON:");
  Serial.println("  GPIO 21  green   (D21)");
  Serial.println("  GPIO 22  yellow  (D22)");
  Serial.println("  GPIO 4   red     (D4)");
  Serial.println("  GPIO 2   onboard blue - reference");
  Serial.println();
  Serial.println("Blue lit but another dark  ->  that lamp's wiring or pin.");
  Serial.println("Blue dark too              ->  sketch not running, re-upload.");
}

void loop() {
  // Nothing to do. The pins stay HIGH until the board is reset.
}
