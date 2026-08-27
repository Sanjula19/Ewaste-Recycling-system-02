// Item scan - Component 4 terminal firmware
//
//   colour sensor -> Wi-Fi -> FastAPI backend -> SELL/HOLD -> LED
//
// Place an item on the sensor: the Clear value drops, one averaged
// colour reading is taken and POSTed to the backend, and the LED the
// backend names is lit. Remove the item to arm the next scan.
//
// TRIGGER: the item is detected by the drop in the TCS34725's Clear
// channel, not by the IR sensor. The design doc describes exactly this
// ("Clear/Lux intensity drops drastically, acting as a contactless
// Material Presence Proximity Detector"), so the IR module is not needed
// on this path at all. The previous IR-triggered version is kept beside
// this file as ItemScan_IRversion.ino.bak.
//
// The backend is asked for ?compact=true, which returns ~230 bytes
// instead of ~14 KB - the full reply embeds a 90-day forecast series
// that only the dashboard chart uses.
//
// ---- BEFORE UPLOADING, set these three ----------------------------
#define WIFI_SSID  "iPhone"
#define WIFI_PASS  "12345678"
#define BACKEND_IP "172.20.10.4"        // this laptop; re-check with ipconfig
// -------------------------------------------------------------------
// The laptop IP changes every time it reconnects to Wi-Fi. If posting
// suddenly starts failing, check that first.

// ---- LOCAL CLASSIFICATION RULE ------------------------------------
// Colour alone cannot separate the grey metals from each other, so this
// build answers only the one question the sensor CAN answer reliably:
// is this copper, or is it not? Copper is genuinely reddish; cardboard
// and yellow both sit well below it on r/c and b/c (measured 26 Aug).
//
//   copper           r/c 0.569   b/c 0.248
//   brown cardboard  r/c 0.515   b/c 0.197
//   yellow           r/c 0.507   b/c 0.177
//
// Re-measure with your own copper sample and adjust if needed.
const float COPPER_MIN_RC = 0.55;   // red must dominate this strongly
const float COPPER_MIN_BC = 0.22;   // and blue must not be too low

// What each outcome means locally. Note the backend's live forecast
// currently says copper = SELL NOW; this fixed rule deliberately
// overrides it so the demo is deterministic. Set USE_BACKEND_DECISION
// to true to follow the forecast instead and keep the LED and the
// dashboard in agreement.
const bool  USE_BACKEND_DECISION = false;
#define COPPER_DECISION      "HOLD"       // yellow
#define NON_COPPER_DECISION  "SELL NOW"   // green
// -------------------------------------------------------------------

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "Adafruit_TCS34725.h"

const int SDA_PIN = 16;   // board pin RX2 / GPIO16
const int SCL_PIN = 17;   // board pin TX2 / GPIO17

// ---- IR obstacle sensor (DISABLED) --------------------------------
// The FC-51 was the original trigger, but the colour sensor's own Clear
// drop does the same job without extra hardware -- and this module
// overheated on 26 Aug, most likely reversed VCC/GND. Left here, wired
// but inert, in case it is brought back for output-chute jam detection
// (see PROJECT_PROGRESS.md section 6).
//
// To re-enable: uncomment the three blocks marked [IR], set pinMode in
// setup(), and gate scanItem() on irTriggered() instead of the Clear drop.
//
// const int IR_PIN = 27;              // [IR] active LOW when blocked
// bool irTriggered() { return digitalRead(IR_PIN) == LOW; }
// -------------------------------------------------------------------

const int LED_GREEN  = 19;   // SELL (and pyrolysis dispatch)
const int LED_YELLOW = 23;   // HOLD / crushing
const int LED_RED    = 4;    // BIN FULL - driven by the lockout, not by a scan

// Weight is NOT measured here. Only Component 3 has a load cell; the
// real system looks weight up server-side from that station's open item
// record. Until that handoff exists, one fixed value keeps the pipeline
// runnable end to end.
const float PLACEHOLDER_WEIGHT_KG = 2.5;

const int   SETTLE_MS    = 300;   // let the item come to rest
const int   SAMPLES      = 5;     // average this many reads
const float TRIGGER_DROP = 0.60;  // fire when Clear falls below 60% of baseline

Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_154MS,
                                          TCS34725_GAIN_16X);

uint16_t baselineClear = 0;   // empty-plate Clear reading, measured at boot
bool     itemPresent   = false;

void allLedsOff() {
  digitalWrite(LED_GREEN,  LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED,    LOW);
}

void setLed(const char *colour) {
  allLedsOff();
  if      (!strcmp(colour, "green"))  digitalWrite(LED_GREEN,  HIGH);
  else if (!strcmp(colour, "yellow")) digitalWrite(LED_YELLOW, HIGH);
  else if (!strcmp(colour, "red"))    digitalWrite(LED_RED,    HIGH);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_GREEN,  OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED,    OUTPUT);
  allLedsOff();

  Wire.begin(SDA_PIN, SCL_PIN);
  if (!tcs.begin()) {
    Serial.println("TCS34725 NOT FOUND - check SDA GPIO16(RX2), SCL GPIO17(TX2), power to VIN");
    while (1) delay(2000);
  }
  Serial.println("TCS34725 ready");

  // Baseline: what an EMPTY plate looks like. Everything downstream is
  // relative to this, so the trigger adapts to whatever the room
  // lighting is instead of relying on a hardcoded threshold that only
  // works on one bench. Keep the plate clear during startup.
  uint32_t sum = 0;
  for (int i = 0; i < 10; i++) {
    uint16_t r, g, b, c;
    tcs.getRawData(&r, &g, &b, &c);
    sum += c;
    delay(60);
  }
  baselineClear = sum / 10;
  Serial.print("baseline Clear (empty plate): ");
  Serial.println(baselineClear);

  Serial.print("connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("connected, this board is ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WIFI FAILED - scans will read colour but not post");
  }

  Serial.println("--- ready, place an item ---");
}

bool looksLikeCopper(uint16_t r, uint16_t g, uint16_t b, uint16_t c) {
  if (c == 0) return false;                 // no light = no opinion
  float rc = (float)r / c;
  float bc = (float)b / c;
  return (rc >= COPPER_MIN_RC) && (bc >= COPPER_MIN_BC);
}

void postReading(uint16_t r, uint16_t g, uint16_t b, uint16_t c, bool isCopper) {
  if (WiFi.status() != WL_CONNECTED) {
    setLed(isCopper ? "yellow" : "green");
    Serial.println("   (offline - not posted; LED follows the local rule)");
    return;
  }

  // The API validates r/g/b as 0-255 but the sensor returns 16-bit
  // channels. Scaling by Clear rather than by a fixed maximum keeps the
  // values steady whether the item sits close to the sensor or further
  // away - the same normalisation the printed ratios use.
  uint8_t r8 = c ? (uint8_t)constrain((long)r * 255 / c, 0, 255) : 0;
  uint8_t g8 = c ? (uint8_t)constrain((long)g * 255 / c, 0, 255) : 0;
  uint8_t b8 = c ? (uint8_t)constrain((long)b * 255 / c, 0, 255) : 0;

  JsonDocument req;
  req["device_id"] = "c4-terminal";
  req["bin_id"]    = "bin-01";
  req["weight_kg"] = PLACEHOLDER_WEIGHT_KG;
  // Telling the backend what this is, rather than making it guess from
  // three colour channels, is the honest split: the sensor answers
  // "copper or not", the backend does the valuation it is actually good
  // at. Non-copper is sent as aluminium so the demo still produces a
  // real forecast -- swap this for an operator selection when the
  // dashboard can supply one.
  req["known_material"] = isCopper ? "copper" : "aluminium";
  JsonObject col = req["color"].to<JsonObject>();
  col["r"]   = r8;
  col["g"]   = g8;
  col["b"]   = b8;
  col["lux"] = c;

  String body;
  serializeJson(req, body);

  String url = String("http://") + BACKEND_IP + ":8000/api/iot/ingest?compact=true";
  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  // The backend caches each metal's model after the first request, but
  // that first one still costs ~15s (TensorFlow load + backtest). The
  // library default is 5s, which times out as HTTP -11 READ_TIMEOUT.
  http.setTimeout(30000);
  int code = http.POST(body);

  if (code == 200) {
    JsonDocument res;
    if (deserializeJson(res, http.getString())) {
      Serial.println("   bad JSON from backend");
    } else {
      const char *material = res["classified_as"]   | "?";
      const char *decision = res["decision"]        | "?";
      const char *led      = res["actuator"]["led"] | "";
      float priceKg = res["price_lkr_per_kg"] | 0.0f;
      float value   = res["value_lkr"]        | 0.0f;

      Serial.print("   ");
      Serial.print(material);
      Serial.print("  |  ");
      Serial.print(decision);
      if (priceKg > 0) {
        Serial.print("  |  Rs.");
        Serial.print(priceKg, 2);
        Serial.print("/kg");
      }
      if (value > 0) {
        Serial.print("  |  batch Rs.");
        Serial.print(value, 2);
      }
      Serial.println();

      if (USE_BACKEND_DECISION) {
        setLed(led);
        Serial.print("   LED -> ");
        Serial.print(led);
        Serial.println("   (following backend)");
      } else {
        // Local rule drives the lamp. Print the backend's verdict too so
        // a disagreement between the LED and the dashboard is visible
        // rather than mysterious.
        const char *localLed = isCopper ? "yellow" : "green";
        setLed(localLed);
        Serial.print("   LED -> ");
        Serial.print(localLed);
        Serial.print("   (local rule; backend said ");
        Serial.print(decision);
        Serial.println(")");
      }
    }
  } else if (code == 422) {
    // The backend's colour heuristic only recognises reddish-copper and
    // bright-neutral-aluminium; it refuses to guess at anything else
    // rather than fabricating a classification.
    Serial.println("   backend could not classify this colour (422)");
  } else {
    Serial.print("   POST failed, HTTP ");
    Serial.println(code);
  }

  http.end();
}

void scanItem() {
  delay(SETTLE_MS);

  uint32_t sr = 0, sg = 0, sb = 0, sc = 0;
  for (int i = 0; i < SAMPLES; i++) {
    uint16_t r, g, b, c;
    tcs.getRawData(&r, &g, &b, &c);
    sr += r;  sg += g;  sb += b;  sc += c;
  }
  uint16_t r = sr / SAMPLES;
  uint16_t g = sg / SAMPLES;
  uint16_t b = sb / SAMPLES;
  uint16_t c = sc / SAMPLES;

  Serial.println(">> ITEM DETECTED");
  Serial.print("   R=");  Serial.print(r);
  Serial.print(" G=");    Serial.print(g);
  Serial.print(" B=");    Serial.print(b);
  Serial.print(" C=");    Serial.print(c);
  if (c) {
    Serial.print("   r/c="); Serial.print((float)r / c, 3);
    Serial.print(" g/c=");   Serial.print((float)g / c, 3);
    Serial.print(" b/c=");   Serial.print((float)b / c, 3);
  }
  Serial.println();

  bool isCopper = looksLikeCopper(r, g, b, c);
  Serial.print("   local verdict: ");
  Serial.print(isCopper ? "COPPER" : "NOT COPPER");
  Serial.print("  ->  ");
  Serial.println(isCopper ? COPPER_DECISION : NON_COPPER_DECISION);

  postReading(r, g, b, c, isCopper);
}

void loop() {
  uint16_t r, g, b, c;
  tcs.getRawData(&r, &g, &b, &c);

  bool covered = (c < baselineClear * TRIGGER_DROP);

  if (covered && !itemPresent) {
    itemPresent = true;
    scanItem();
  } else if (!covered && itemPresent) {
    itemPresent = false;
    allLedsOff();
    Serial.println("-- removed, ready for next --");
  }

  delay(80);
}
