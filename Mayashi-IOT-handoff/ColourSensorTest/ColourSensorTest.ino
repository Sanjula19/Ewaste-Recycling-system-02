// =====================================================================
//  Component 4 - Predictive Economic Valuation & Strategic Disposition
//  Terminal firmware  (R26-IT-015, SLIIT)
// =====================================================================
//
//  Conveyor belt carries items past two fixed stations:
//  IR sensor (arrival trigger) -> colour sensor (classify) -> Wi-Fi ->
//  FastAPI backend -> decision -> LED + diverter gate
//
//  Everything the separate test sketches did, in one program:
//    BlinkTest         -> boot heartbeat on the onboard LED
//    ColourSensorTest  -> TCS34725 read + I2C scan on failure
//    LedTest/LedDebug  -> three status LEDs with a startup self-test
//    UltrasonicTest    -> HC-SR04 bin level + 7.5 cm lockout
//    ServoAngleTest    -> confirmed the diverter gate's pin/position (D26)
//    IRSensorTest      -> fixed; now the arrival trigger
//    ItemScan          -> the scan cycle and backend round trip
//
//  HOW IT RUNS
//  Two independent jobs share the loop, neither blocking the other:
//
//    1. SCAN CYCLE   the IR sensor fires as an item passes it on the
//                    belt -> settle -> colour read -> POST -> LED per the
//                    backend's decision -> the gate does one release
//                    motion (GATE_RELEASE then back to GATE_HOME) to
//                    drop the item into the single bin -> HOLD material
//                    additionally gets crushed (D14, now wired). Every
//                    material goes to the same bin for now -- no
//                    diverting by decision yet, that's a later step once
//                    separate bins exist. Edge-triggered: the item must
//                    clear the IR beam (it does, the belt keeps moving)
//                    before the next scan will fire. Falls back to the
//                    colour sensor's own Clear-channel drop as the
//                    trigger if USE_IR is switched off below.
//
//    2. BIN MONITOR  runs on its own timer every BIN_CHECK_MS regardless
//                    of what the scan cycle is doing, so a filling bin is
//                    noticed between items rather than only during one.
//                    Crossing the threshold latches a LOCKOUT that
//                    refuses further scans until the bin is emptied.
//
//  Anything not physically wired is switched off in the FEATURES block
//  below, so this file runs unchanged as hardware is added.
// =====================================================================


// ---------------------------------------------------------------------
//  1. SET THESE BEFORE UPLOADING
// ---------------------------------------------------------------------
#define WIFI_SSID   "iPhone"
#define WIFI_PASS   "12345678"
#define BACKEND_IP  "172.20.10.4"     // the laptop running the backend
#define BACKEND_PORT 8000

// The laptop's IP changes every time it reconnects to Wi-Fi. If posting
// suddenly starts failing, check `ipconfig` first -- it is almost always
// this and not the code.


// ---------------------------------------------------------------------
//  2. FEATURES - turn on only what is actually wired
// ---------------------------------------------------------------------
#define USE_COLOUR      1   // TCS34725  - required; it is also the trigger
#define USE_LEDS        1   // 3 status LEDs
#define USE_ULTRASONIC  1   // HC-SR04 bin level + lockout
#define USE_GATE_SERVO  1   // SG90 routing gate
#define USE_BUZZER      0   // active buzzer            (not wired yet)
#define USE_CRUSHER     1   // compaction servo, D14 -- HOLD items get crushed now
#define USE_IR          1   // FC-51 - fixed; now the scan trigger (colour Clear-drop is the fallback below)


// ---------------------------------------------------------------------
//  3. PIN MAP  (ESP32 DevKit V1, USB facing you)
// ---------------------------------------------------------------------
//   Dxx on the silkscreen == GPIOxx, except RX2/TX2 which are 16/17.
//
//   TCS34725   SDA -> GPIO 16 (RX2)   SCL -> GPIO 17 (TX2)
//   Green LED  GPIO 21   SELL / dispatched
//   Yellow LED GPIO 18   HOLD / crushing
//   Red LED    GPIO 4    BIN FULL
//   HC-SR04    Trig GPIO 5, Echo GPIO 22  (Echo THROUGH a 1k/2k divider)
//   SG90 gate  GPIO 26   (per ServoAngleTest.ino) - single bin for now
//   Crusher    GPIO 14   wired -- runs on HOLD, still lands in the single bin
//   Buzzer     GPIO 13   (later)
//   IR OUT     GPIO 27   arrival trigger
//
//   D19 and D23 are deliberately unused: both stopped driving on 27 Aug
//   after being run without current-limiting resistors.
// ---------------------------------------------------------------------
const int PIN_SDA        = 16;
const int PIN_SCL        = 17;
const int PIN_LED_GREEN  = 21;
const int PIN_LED_YELLOW = 18;
const int PIN_LED_RED    = 4;
const int PIN_LED_ONBOARD = 2;    // soldered to the board - cannot be miswired
const int PIN_TRIG       = 5;
const int PIN_ECHO       = 22;
const int PIN_GATE       = 26;    // diverter servo -- see ServoAngleTest.ino
const int PIN_CRUSHER    = 14;    // wired -- moved off 26 once the gate took that pin
const int PIN_BUZZER     = 13;
const int PIN_IR         = 27;


// ---------------------------------------------------------------------
//  4. TUNING
// ---------------------------------------------------------------------
// Weight is NOT measured here. Only Component 3 has a load cell; in the
// integrated system the backend looks the weight up from that station's
// open item record. Until that handoff exists this fixed value keeps the
// pipeline runnable end to end.
const float PLACEHOLDER_WEIGHT_KG = 2.5;

// Trigger: fire when Clear falls below this fraction of the empty-plate
// baseline measured at boot. Relative, so it adapts to room lighting
// instead of relying on a threshold that only works on one bench.
const float TRIGGER_DROP = 0.60;

// 800 ms, not 300: the sensor's illuminator LED visibly ramps for about a
// second after an item lands (raw counts climbed 8,384 -> 13,000 over the
// first 15 samples on 27 Aug). Reading earlier classifies a half-lit item.
const int SETTLE_MS = 800;
const int COLOUR_SAMPLES = 5;

// Copper vs not-copper is the only question three colour channels can
// answer reliably on this bench. Measured 26-27 Aug:
//
//   material           r/c     g/c     b/c
//   copper             0.569   0.293   0.248
//   brown cardboard    0.515   0.295   0.197
//   yellow             0.507   0.306   0.177
//   bright neutral     0.569   0.477   0.462
//
// Note the last row: its r/c is IDENTICAL to copper's, so a rule built on
// r/c alone calls it copper. Copper is red because red DOMINATES (green
// and blue near 0.25-0.29); a bright neutral surface has all three
// channels close together and merely leans warm. Hence blue needs a
// BAND, not just a floor.
const float COPPER_MIN_RC = 0.55;
const float COPPER_MIN_BC = 0.20;
const float COPPER_MAX_BC = 0.35;

// Bin is full when the waste surface rises within this distance of the
// lid-mounted sensor. Measured against the real bin: 7.5 cm.
const float BIN_FULL_CM   = 7.5;
const unsigned long BIN_CHECK_MS = 4000;   // how often to re-measure

// Single bin for now -- no diverting between market/compactor/pyrolysis
// yet, so the gate does the same release motion for every item
// regardless of what it was classified as. GATE_HOME (per
// ServoAngleTest.ino) is the resting position; GATE_RELEASE is a brief
// swing away from it to let the item drop into the bin. Tune both
// against the real mechanism -- these are placeholders.
const int GATE_HOME    = 90;
const int GATE_RELEASE = 60;

// How long the IR reading must hold steady before it's believed. The
// raw signal chatters when an item sits right at the edge of the
// detection range -- same behaviour IRSensorTest.ino was written to handle.
const unsigned long IR_DEBOUNCE_MS = 150;

const unsigned long HTTP_TIMEOUT_MS = 30000;  // first request loads the model (~13 s)

// DEBUG PACING: pause this long after each logged step in the scan cycle,
// so the whole IR -> colour -> POST -> LED -> gate sequence is slow
// enough to actually read on Serial Monitor instead of scrolling past in
// under a second. Turn down to a few hundred ms (or 0) once you're not
// actively watching each scan happen.
const unsigned long STEP_DELAY_MS = 1200;

// How long each lamp stays lit during the boot self-test. Long enough to
// walk around the board and actually confirm each colour, not just catch
// a flash out of the corner of your eye.
const unsigned long LED_SELFTEST_MS = 1500;


// ---------------------------------------------------------------------
//  5. LIBRARIES
// ---------------------------------------------------------------------
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#if USE_COLOUR
  #include "Adafruit_TCS34725.h"
  Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_154MS,
                                            TCS34725_GAIN_16X);
#endif

#if USE_GATE_SERVO || USE_CRUSHER
  #include <ESP32Servo.h>          // NOT the stock Servo library - AVR only
  #if USE_GATE_SERVO
    Servo gateServo;
  #endif
  #if USE_CRUSHER
    Servo crusherServo;
  #endif
#endif


// ---------------------------------------------------------------------
//  6. STATE
// ---------------------------------------------------------------------
uint16_t baselineClear = 0;      // empty-plate reading, taken at boot
bool     itemPresent   = false;  // debounced "something is on the plate"
bool     binLocked     = false;  // latched by the bin monitor
unsigned long lastBinCheck = 0;
uint32_t scanCount = 0;


// ---------------------------------------------------------------------
//  7. OUTPUT HELPERS
// ---------------------------------------------------------------------
void ledsOff() {
#if USE_LEDS
  digitalWrite(PIN_LED_GREEN,  LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED,    LOW);
#endif
}

// One status is true at a time, so every change starts from all-off --
// the panel can never show two verdicts at once.
void setLed(const char *colour) {
#if USE_LEDS
  ledsOff();
  if      (!strcmp(colour, "green"))  digitalWrite(PIN_LED_GREEN,  HIGH);
  else if (!strcmp(colour, "yellow")) digitalWrite(PIN_LED_YELLOW, HIGH);
  else if (!strcmp(colour, "red"))    digitalWrite(PIN_LED_RED,    HIGH);
#endif
}

void beep(int ms) {
#if USE_BUZZER
  if (ms <= 0) return;
  digitalWrite(PIN_BUZZER, HIGH);
  delay(ms);
  digitalWrite(PIN_BUZZER, LOW);
#endif
}

// Prints one line, then pauses STEP_DELAY_MS -- used to mark each phase
// of the scan cycle so it's readable on Serial Monitor instead of
// flashing past.
void logStep(const __FlashStringHelper *msg) {
  Serial.println(msg);
  delay(STEP_DELAY_MS);
}

// Move, let it arrive, then release. A servo left attached keeps actively
// holding position -- it buzzes, draws current and heats up for no reason
// once the item has already gone through the gate.
void moveGate(int angle) {
#if USE_GATE_SERVO
  angle = constrain(angle, 10, 170);      // avoid the mechanical end stops
  gateServo.attach(PIN_GATE, 500, 2400);
  gateServo.write(angle);
  delay(700);
  gateServo.detach();
  Serial.print(F("   gate -> "));
  Serial.print(angle);
  Serial.println(F(" deg"));
#endif
}

void runCrusher() {
#if USE_CRUSHER
  crusherServo.attach(PIN_CRUSHER, 500, 2500);
  crusherServo.write(120);   // press down
  delay(900);
  crusherServo.write(20);    // release
  delay(900);
  crusherServo.detach();
  Serial.println(F("   crusher: compaction stroke complete"));
#endif
}


// ---------------------------------------------------------------------
//  7b. IR - scan trigger
// ---------------------------------------------------------------------
#if USE_IR
bool irTriggered() {
  return digitalRead(PIN_IR) == LOW;   // active LOW, per IRSensorTest.ino
}
#endif


// ---------------------------------------------------------------------
//  8. ULTRASONIC - bin level
// ---------------------------------------------------------------------
#if USE_ULTRASONIC
const unsigned long ECHO_TIMEOUT_US = 30000UL;   // ~5 m, past the sensor's useful range
const float CM_PER_US = 0.0343f / 2.0f;          // 343 m/s, halved for the round trip

float pingOnce() {
  // A clean low first: a floating Trig can latch the module into
  // re-triggering itself.
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);            // datasheet minimum
  digitalWrite(PIN_TRIG, LOW);

  unsigned long us = pulseIn(PIN_ECHO, HIGH, ECHO_TIMEOUT_US);
  if (us == 0) return -1.0f;        // nothing came back
  return us * CM_PER_US;
}

// Median of 5, not mean. The HC-SR04 throws the occasional wild reading
// when an echo bounces off the bin wall instead of the waste, and one
// spike drags an average badly -- the median just ignores it.
float measureBinCm() {
  const int N = 5;
  float v[N];
  int n = 0;
  for (int i = 0; i < N; i++) {
    float d = pingOnce();
    if (d > 0) v[n++] = d;
    delay(60);                      // <60 ms and the last burst echoes into the next
  }
  if (n == 0) return -1.0f;

  for (int i = 1; i < n; i++) {     // insertion sort; n is 5
    float key = v[i];
    int j = i - 1;
    while (j >= 0 && v[j] > key) { v[j + 1] = v[j]; j--; }
    v[j + 1] = key;
  }
  return v[n / 2];
}
#endif


// ---------------------------------------------------------------------
//  9. NETWORK
// ---------------------------------------------------------------------
String backendUrl(const char *path) {
  return String("http://") + BACKEND_IP + ":" + BACKEND_PORT + path;
}

// Reports the bin level and picks up the lockout verdict. Returns true if
// the backend says the bin is full.
bool reportBinLevel(float cm) {
  if (WiFi.status() != WL_CONNECTED) return binLocked;

  JsonDocument req;
  req["bin_id"] = "bin-01";
  req["distance_cm"] = cm;
  req["full_threshold_cm"] = BIN_FULL_CM;

  String body;
  serializeJson(req, body);

  HTTPClient http;
  http.begin(backendUrl("/api/iot/bin-status"));
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT_MS);
  int code = http.POST(body);

  bool locked = binLocked;
  if (code == 200) {
    String respBody = http.getString();
    JsonDocument res;
    if (!deserializeJson(res, respBody)) {
      locked = res["locked"] | false;
      if (res["just_locked"] | false) {
        Serial.println(F("!! BIN FULL - SYSTEM LOCKOUT, dispatch required"));
        beep(600);
      }
    }
  }
  http.end();
  return locked;
}


// ---------------------------------------------------------------------
//  10. CLASSIFY
// ---------------------------------------------------------------------
bool looksLikeCopper(uint16_t r, uint16_t g, uint16_t b, uint16_t c) {
  if (c == 0) return false;                  // no light means no opinion
  float rc = (float)r / c;
  float bc = (float)b / c;
  return (rc >= COPPER_MIN_RC) && (bc >= COPPER_MIN_BC) && (bc <= COPPER_MAX_BC);
}


// ---------------------------------------------------------------------
//  11. SCAN -> POST -> ACT
// ---------------------------------------------------------------------
void postAndAct(uint16_t r, uint16_t g, uint16_t b, uint16_t c, bool isCopper) {
  if (WiFi.status() != WL_CONNECTED) {
    setLed(isCopper ? "yellow" : "green");
    Serial.println(F("   offline - not posted; LED follows the local rule"));
    return;
  }

  // The API validates r/g/b as 0-255 but the sensor returns 16-bit
  // channels. Scaling by Clear rather than a fixed maximum keeps the
  // values steady whether the item sits close to the sensor or further
  // away -- the same normalisation the printed ratios use.
  uint8_t r8 = c ? (uint8_t)constrain((long)r * 255 / c, 0, 255) : 0;
  uint8_t g8 = c ? (uint8_t)constrain((long)g * 255 / c, 0, 255) : 0;
  uint8_t b8 = c ? (uint8_t)constrain((long)b * 255 / c, 0, 255) : 0;

  JsonDocument req;
  req["device_id"] = "c4-terminal";
  req["bin_id"]    = "bin-01";
  req["weight_kg"] = PLACEHOLDER_WEIGHT_KG;
  // Telling the backend what this is, rather than making it guess from
  // three colour channels, is the honest split: the sensor answers
  // "copper or not", the backend does the valuation it is good at.
  req["known_material"] = isCopper ? "copper" : "aluminium";
  JsonObject col = req["color"].to<JsonObject>();
  col["r"] = r8;  col["g"] = g8;  col["b"] = b8;  col["lux"] = c;

  String body;
  serializeJson(req, body);
  Serial.print(F("   -> POST /api/iot/ingest  "));
  Serial.println(body);

  HTTPClient http;
  // ?compact=true returns ~230 bytes instead of ~14 KB: the full reply
  // embeds a 90-point forecast series that only the dashboard chart uses,
  // and parsing that on an ESP32 wastes memory it does not have.
  http.begin(backendUrl("/api/iot/ingest?compact=true"));
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT_MS);
  Serial.println(F("   waiting for backend..."));
  int code = http.POST(body);
  Serial.print(F("   <- HTTP ")); Serial.println(code);

  if (code == 200) {
    String respBody = http.getString();
    Serial.print(F("      ")); Serial.println(respBody);
    JsonDocument res;
    if (deserializeJson(res, respBody)) {
      Serial.println(F("   bad JSON from backend"));
    } else {
      const char *material = res["classified_as"]   | "?";
      const char *decision = res["decision"]        | "?";
      const char *led      = res["actuator"]["led"] | "green";
      int   beepMs         = res["actuator"]["beep_ms"]    | 120;
      float priceKg        = res["price_lkr_per_kg"] | 0.0f;
      float value          = res["value_lkr"]        | 0.0f;
      float energy         = res["energy_kwh"]       | 0.0f;

      Serial.print(F("   "));
      Serial.print(material);
      Serial.print(F("  |  "));
      Serial.print(decision);
      if (priceKg > 0) { Serial.print(F("  |  Rs.")); Serial.print(priceKg, 2); Serial.print(F("/kg")); }
      if (value   > 0) { Serial.print(F("  |  batch Rs.")); Serial.print(value, 2); }
      if (energy  != 0) { Serial.print(F("  |  ")); Serial.print(energy, 2); Serial.print(F(" kWh")); }
      Serial.println();

      const char *facility = res["facility"] | "";
      if (strlen(facility)) { Serial.print(F("   destination: ")); Serial.println(facility); }

      logStep(F("   [5/5] applying decision..."));

      beep(beepMs);
      setLed(led);
      Serial.print(F("   LED -> "));
      Serial.println(led);
      delay(STEP_DELAY_MS);

      // Single bin: one release motion for every item, independent of
      // material or decision -- the backend's gate_angle field is not
      // used here, there's still only one destination. Revisit once
      // separate bins exist.
      Serial.println(F("   releasing item into bin..."));
      moveGate(GATE_RELEASE);
      delay(STEP_DELAY_MS);
      Serial.println(F("   reopening pathway..."));
      moveGate(GATE_HOME);

      // Crusher is wired now (D14) -- HOLD material gets compacted after
      // it lands, independent of which bin it's in.
      bool crush = res["actuator"]["crush"] | false;
      if (crush) {
        delay(STEP_DELAY_MS);
        Serial.println(F("   crushing (HOLD)..."));
        runCrusher();
      }

      // The backend echoes the lockout state on every scan, so a bin that
      // filled up between bin-monitor ticks still gets caught here.
      if (res["locked"] | false) {
        binLocked = true;
        Serial.println(F("   backend reports BIN FULL"));
      }
    }
  } else if (code == 422) {
    // The backend's colour heuristic recognises reddish-copper and
    // bright-neutral-aluminium only; it refuses to guess at anything else
    // rather than fabricating a classification.
    Serial.println(F("   backend could not classify this colour (422)"));
  } else {
    Serial.print(F("   POST failed, HTTP "));
    Serial.println(code);
    if (code == -11) Serial.println(F("   (-11 = read timeout; first request after a backend restart is slow)"));
  }

  http.end();
}


void scanItem() {
#if USE_COLOUR
  logStep(F("   [2/5] settling (colour sensor ramp-up + item landing)..."));
  delay(SETTLE_MS);

  logStep(F("   [3/5] sampling colour sensor..."));
  uint32_t sr = 0, sg = 0, sb = 0, sc = 0;
  for (int i = 0; i < COLOUR_SAMPLES; i++) {
    uint16_t r, g, b, c;
    tcs.getRawData(&r, &g, &b, &c);
    sr += r; sg += g; sb += b; sc += c;
    Serial.print(F("      sample ")); Serial.print(i + 1);
    Serial.print(F("/")); Serial.print(COLOUR_SAMPLES);
    Serial.print(F(": R=")); Serial.print(r);
    Serial.print(F(" G="));  Serial.print(g);
    Serial.print(F(" B="));  Serial.print(b);
    Serial.print(F(" C="));  Serial.println(c);
    delay(200);   // spread the samples out so they're readable too
  }
  uint16_t r = sr / COLOUR_SAMPLES;
  uint16_t g = sg / COLOUR_SAMPLES;
  uint16_t b = sb / COLOUR_SAMPLES;
  uint16_t c = sc / COLOUR_SAMPLES;

  scanCount++;
  Serial.print(F(">> ITEM DETECTED  #"));
  Serial.println(scanCount);
  Serial.print(F("   average: R=")); Serial.print(r);
  Serial.print(F(" G="));   Serial.print(g);
  Serial.print(F(" B="));   Serial.print(b);
  Serial.print(F(" C="));   Serial.print(c);
  if (c) {
    Serial.print(F("   r/c=")); Serial.print((float)r / c, 3);
    Serial.print(F(" g/c="));   Serial.print((float)g / c, 3);
    Serial.print(F(" b/c="));   Serial.print((float)b / c, 3);
  }
  Serial.println();

  bool isCopper = looksLikeCopper(r, g, b, c);
  Serial.print(F("   local verdict: "));
  Serial.println(isCopper ? F("COPPER") : F("NOT COPPER"));
  delay(STEP_DELAY_MS);

  logStep(F("   [4/5] posting to backend..."));
  postAndAct(r, g, b, c, isCopper);
#endif
}


// ---------------------------------------------------------------------
//  12. SETUP
// ---------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println(F("=== Component 4 terminal ==="));

  pinMode(PIN_LED_ONBOARD, OUTPUT);
#if USE_LEDS
  pinMode(PIN_LED_GREEN,  OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED,    OUTPUT);
  ledsOff();

  // Self-test: each lamp in turn, so a dead one is obvious before any
  // decision depends on it.
  Serial.println(F("LED self-test..."));
  const int lamps[3]   = { PIN_LED_GREEN, PIN_LED_YELLOW, PIN_LED_RED };
  const char *names[3] = { "green (D21)", "yellow (D18)", "red (D4)" };
  for (int i = 0; i < 3; i++) {
    digitalWrite(lamps[i], HIGH);
    Serial.print(F("   ")); Serial.println(names[i]);
    delay(LED_SELFTEST_MS);
    digitalWrite(lamps[i], LOW);
  }
  Serial.println(F("   any lamp that stayed dark is a wiring fault"));
#endif

#if USE_BUZZER
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
#endif

#if USE_IR
  // PULLUP matters: with a plain INPUT an unconnected OUT wire floats and
  // reads as random detections. With the pullup a disconnected sensor
  // reads HIGH = "clear" instead.
  pinMode(PIN_IR, INPUT_PULLUP);
  Serial.println(F("IR ready (D27, active LOW) - primary scan trigger"));
#endif

#if USE_ULTRASONIC
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  digitalWrite(PIN_TRIG, LOW);
  Serial.println(F("HC-SR04 ready (Trig D5, Echo D22 via 1k/2k divider)"));
#endif

#if USE_GATE_SERVO || USE_CRUSHER
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  #if USE_GATE_SERVO
    gateServo.setPeriodHertz(50);
    moveGate(GATE_HOME);            // park centre so the chute starts known
  #endif
  #if USE_CRUSHER
    crusherServo.setPeriodHertz(50);
  #endif
#endif

#if USE_COLOUR
  Wire.begin(PIN_SDA, PIN_SCL);
  if (!tcs.begin()) {
    Serial.println(F("TCS34725 NOT FOUND"));
    Serial.println(F("Scanning I2C bus..."));
    byte found = 0;
    for (byte addr = 1; addr < 127; addr++) {
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        Serial.print(F("   device at 0x")); Serial.println(addr, HEX);
        found++;
      }
    }
    if (!found) Serial.println(F("   nothing on the bus - check SDA on RX2, SCL on TX2, power to VIN"));
    else        Serial.println(F("   (the TCS34725 should answer at 0x29)"));
    // Halt: even with IR doing the triggering, nothing can be classified
    // without the colour sensor, so there is nothing useful to do without it.
    while (1) { digitalWrite(PIN_LED_ONBOARD, !digitalRead(PIN_LED_ONBOARD)); delay(300); }
  }
  Serial.println(F("TCS34725 ready (16x gain, 154 ms)"));

  // Baseline: what an EMPTY plate looks like. Everything downstream is
  // relative to this, so the trigger adapts to the room instead of a
  // hardcoded threshold. KEEP THE PLATE CLEAR DURING STARTUP.
  uint32_t sum = 0;
  for (int i = 0; i < 10; i++) {
    uint16_t r, g, b, c;
    tcs.getRawData(&r, &g, &b, &c);
    sum += c;
    delay(60);
  }
  baselineClear = sum / 10;
  Serial.print(F("baseline Clear (empty plate): "));
  Serial.println(baselineClear);
  if (baselineClear < 500) {
    Serial.println(F("   WARNING: very dim. Check the sensor's white LED and that"));
    Serial.println(F("   nothing is connected to its LED pin. Triggering will be unreliable."));
  }
#endif

  Serial.print(F("connecting to "));
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F("connected, this board is "));
    Serial.println(WiFi.localIP());
    Serial.print(F("backend: "));
    Serial.println(backendUrl(""));
  } else {
    Serial.println(F("WIFI FAILED - scans will read colour but not post"));
    Serial.println(F("   (2.4 GHz only; the ESP32 cannot join a 5 GHz network)"));
  }

  Serial.println(F("--- ready, place an item ---"));
}


// ---------------------------------------------------------------------
//  13. LOOP
// ---------------------------------------------------------------------
void loop() {

  // ---- Job 2: bin monitor, on its own cadence -----------------------
  // Deliberately outside the scan cycle so a filling bin is noticed
  // between items, not only while one is being processed.
#if USE_ULTRASONIC
  if (millis() - lastBinCheck >= BIN_CHECK_MS) {
    lastBinCheck = millis();
    float cm = measureBinCm();
    if (cm > 0) {
      bool wasLocked = binLocked;
      binLocked = reportBinLevel(cm);
      if (binLocked && !wasLocked) {
        setLed("red");
        Serial.print(F("!! BIN FULL at "));
        Serial.print(cm, 1);
        Serial.println(F(" cm - scanning suspended"));
      } else if (!binLocked && wasLocked) {
        ledsOff();
        Serial.println(F("bin cleared - scanning resumed"));
      }
    } else {
      Serial.println(F("bin: no echo - out of range, or check Echo on D22 and 5 V on VCC"));
    }
  }
#endif

  // ---- Job 1: scan cycle --------------------------------------------
#if USE_COLOUR
#if USE_IR
  // Debounce: the raw signal chatters when an item sits right at the
  // edge of the detection range (same behaviour IRSensorTest.ino saw).
  static bool irLastRaw    = false;
  static unsigned long irLastChangeMs = 0;
  bool irRaw = irTriggered();
  // Mirrors IRSensorTest.ino: the onboard blue LED (D2, soldered to the
  // board, can't be miswired) follows the RAW pin state every loop, not
  // just confirmed detections -- a hardware-guaranteed visual check that
  // doesn't depend on Serial Monitor being open at all.
  digitalWrite(PIN_LED_ONBOARD, irRaw ? HIGH : LOW);
  if (irRaw != irLastRaw) {
    irLastRaw = irRaw;
    irLastChangeMs = millis();
    // Unfiltered -- prints on every raw pin change, even ones too brief
    // to pass the debounce below. If nothing ever prints here while an
    // object is in front of the sensor, the pin isn't toggling at all
    // (wiring/power problem, not a firmware one). If this prints but
    // "[1/5] IR BEAM BROKEN" below never does, the blip isn't holding
    // for IR_DEBOUNCE_MS -- lower that constant or slow the belt.
    Serial.print(F("[IR] raw pin -> "));
    Serial.println(irRaw ? F("LOW (blocked)") : F("HIGH (clear)"));
  }
  bool covered = itemPresent;
  if (millis() - irLastChangeMs >= IR_DEBOUNCE_MS) covered = irRaw;
#else
  uint16_t r, g, b, c;
  tcs.getRawData(&r, &g, &b, &c);
  bool covered = (c < baselineClear * TRIGGER_DROP);
#endif

  if (covered && !itemPresent) {
    itemPresent = true;
    Serial.println(F("----------------------------------------"));
    logStep(F(">> [1/5] IR BEAM BROKEN - item arriving"));
    if (binLocked) {
      // Refuse rather than silently accept: the bin has nowhere to put it.
      Serial.println(F(">> item detected but BIN IS FULL - dispatch required"));
      setLed("red");
      beep(400);
    } else {
      scanItem();
    }
  } else if (!covered && itemPresent) {
    itemPresent = false;
    if (!binLocked) ledsOff();
    Serial.println(F("-- removed, ready for next --"));
  }
#endif

  delay(80);
}
