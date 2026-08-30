#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// =====================================================
// BEFORE UPLOADING, set these three
// =====================================================
//
// This board does NOT have its own moisture sensor. It asks the
// Component 3 backend for the latest reading posted by the separate
// SHEF ESP32/DHT22 unit (POST /api/sensor/moisture), then sorts the
// physical item accordingly. See component-3/REAL-COMPONENT-3.md,
// section "IoT / moisture handling".
//
#define WIFI_SSID    "iPhone"
#define WIFI_PASS    "12345678"
#define BACKEND_IP   "172.20.10.4"      // this laptop; re-check with ipconfig
#define BACKEND_PORT 8003               // component-3 backend (uvicorn ... --port 8003)
// =====================================================
// The laptop IP changes every time it reconnects to Wi-Fi. If the fetch
// suddenly starts failing (falls back to the alternating pattern below),
// check that first.


// =====================================================
// PIN CONFIGURATION
// =====================================================

#define TRIG_PIN 5
#define ECHO_PIN 18

#define SERVO_PIN 25


// =====================================================
// SERVO POSITIONS
// =====================================================
//
// CENTER = 90°
//
// DRY = 45°  (45° left from center)
// WET = 135° (45° right from center)
//
// Total movement = 90°
//
// =====================================================

const int SERVO_DRY    = 45;
const int SERVO_CENTER = 90;
const int SERVO_WET    = 135;


// =====================================================
// ULTRASONIC
// =====================================================

const float DETECTION_DISTANCE = 15.0;


// =====================================================
// TIMING
// =====================================================

const unsigned long SORT_TIME = 3000;
const unsigned long CENTER_TIME = 1500;


// =====================================================
// SERVO
// =====================================================

Servo mg90s;


// =====================================================
// FALLBACK: ALTERNATING TEST PATTERN
// =====================================================
//
// Used only when the backend can't be reached (Wi-Fi down, backend not
// running, or the reading is still the un-set default with no timestamp
// yet). Keeps the mechanism demoable even offline, same as before:
//
// 1st object = DRY
// 2nd object = WET
// 3rd object = DRY
// 4th object = WET
//

bool nextIsWet = false;


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);


  // Ultrasonic
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(TRIG_PIN, LOW);


  // Servo
  mg90s.setPeriodHertz(50);

  mg90s.attach(
    SERVO_PIN,
    500,
    2400
  );


  // Start at CENTER
  mg90s.write(SERVO_CENTER);

  delay(1500);


  // Wi-Fi
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected, this board is ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WIFI FAILED - will sort using the alternating fallback pattern");
  }


  // Startup
  Serial.println();
  Serial.println("========================================");
  Serial.println("       SERVO SORTING GATE - COMPONENT 3");
  Serial.println("========================================");

  Serial.println();

  Serial.print("Moisture SOURCE: http://");
  Serial.print(BACKEND_IP);
  Serial.print(":");
  Serial.print(BACKEND_PORT);
  Serial.println("/api/sensor/moisture/latest");
  Serial.println("Fallback (if unreachable): alternating DRY/WET test pattern");
  Serial.println("Ultrasonic: ENABLED");
  Serial.println("Servo: ENABLED");

  Serial.println();

  Serial.println("SERVO POSITIONS");
  Serial.println("----------------------------------------");

  Serial.println("DRY    = 45 degrees");
  Serial.println("CENTER = 90 degrees");
  Serial.println("WET    = 135 degrees");

  Serial.println();

  Serial.println("MOVEMENT");
  Serial.println("----------------------------------------");

  Serial.println("CENTER -> DRY -> CENTER");
  Serial.println("CENTER -> WET -> CENTER");

  Serial.println();

  Serial.println("SERVO = CENTER");

  Serial.println("SYSTEM READY");

  Serial.println();
}


// =====================================================
// READ ULTRASONIC DISTANCE
// =====================================================

float readDistance() {

  digitalWrite(TRIG_PIN, LOW);

  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);

  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);


  unsigned long duration = pulseIn(
    ECHO_PIN,
    HIGH,
    30000
  );


  if (duration == 0) {

    return -1;
  }


  float distance =
    duration * 0.0343 / 2.0;


  return distance;
}


// =====================================================
// FETCH LIVE MOISTURE STATUS FROM THE BACKEND
// =====================================================
//
// GET /api/sensor/moisture/latest -> { moisture_status, raw_value, timestamp }
// (component-3/backend/app/api/routes/sensor.py)
//
// Returns true and sets `isWet` when a real reading was obtained.
// Returns false (leaving `isWet` untouched) when Wi-Fi is down, the
// request fails, or the backend hasn't received a sensor reading yet
// (timestamp still null) - the caller should fall back to the
// alternating test pattern in that case.

bool fetchIsWet(bool &isWet) {

  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;

  String url = String("http://") + BACKEND_IP + ":" + BACKEND_PORT + "/api/sensor/moisture/latest";

  http.begin(url);
  http.setTimeout(4000);

  int code = http.GET();

  bool ok = false;

  if (code == 200) {

    JsonDocument res;
    DeserializationError err = deserializeJson(res, http.getString());

    if (!err && !res["timestamp"].isNull()) {

      const char *status = res["moisture_status"] | "";

      if (!strcmp(status, "Wet")) {
        isWet = true;
        ok = true;
      } else if (!strcmp(status, "Dry")) {
        isWet = false;
        ok = true;
      }
    }
  } else {
    Serial.print("   moisture fetch failed, HTTP ");
    Serial.println(code);
  }

  http.end();

  return ok;
}


// =====================================================
// MOVE TO CENTER
// =====================================================

void moveToCenter() {

  Serial.println("Servo -> CENTER (90 degrees)");

  mg90s.write(SERVO_CENTER);

  delay(CENTER_TIME);
}


// =====================================================
// SORT DRY
// =====================================================

void sortDry(const char *source) {

  Serial.println();
  Serial.println("----------------------------------------");
  Serial.print("CLASSIFICATION: DRY  (");
  Serial.print(source);
  Serial.println(")");
  Serial.println("----------------------------------------");

  Serial.println("CENTER -> DRY");

  Serial.println("Servo -> 45 degrees");

  mg90s.write(SERVO_DRY);

  delay(SORT_TIME);


  Serial.println("DRY drop completed.");


  // Return home / center
  moveToCenter();


  Serial.println("DRY cycle completed.");

  Serial.println();
}


// =====================================================
// SORT WET
// =====================================================

void sortWet(const char *source) {

  Serial.println();
  Serial.println("----------------------------------------");
  Serial.print("CLASSIFICATION: WET  (");
  Serial.print(source);
  Serial.println(")");
  Serial.println("----------------------------------------");

  Serial.println("CENTER -> WET");

  Serial.println("Servo -> 135 degrees");

  mg90s.write(SERVO_WET);

  delay(SORT_TIME);


  Serial.println("WET drop completed.");


  // Return home / center
  moveToCenter();


  Serial.println("WET cycle completed.");

  Serial.println();
}


// =====================================================
// WAIT FOR OBJECT TO LEAVE
// =====================================================

void waitForObjectToLeave() {

  Serial.println("Waiting for object to leave...");

  delay(500);


  while (true) {

    float distance = readDistance();


    if (distance < 0) {

      delay(200);

      continue;
    }


    Serial.print("Distance: ");

    Serial.print(distance, 1);

    Serial.println(" cm");


    if (distance > DETECTION_DISTANCE) {

      Serial.println("Object cleared.");

      break;
    }


    delay(300);
  }
}


// =====================================================
// MAIN LOOP
// =====================================================

void loop() {

  float distance = readDistance();


  if (distance < 0) {

    delay(300);

    return;
  }


  Serial.print("Distance: ");

  Serial.print(distance, 1);

  Serial.println(" cm");


  // ===================================================
  // OBJECT DETECTED
  // ===================================================

  if (distance <= DETECTION_DISTANCE) {

    Serial.println();
    Serial.println(">>> OBJECT DETECTED");


    // -----------------------------------------------
    // Ask the backend for the live moisture reading
    // first. Only fall back to the alternating pattern
    // if the backend can't be reached.
    // -----------------------------------------------

    bool isWet = false;
    bool gotLiveReading = fetchIsWet(isWet);

    if (gotLiveReading) {

      if (isWet) {
        sortWet("live sensor");
      } else {
        sortDry("live sensor");
      }

    } else {

      if (nextIsWet == false) {

        sortDry("fallback pattern");

        nextIsWet = true;

      } else {

        sortWet("fallback pattern");

        nextIsWet = false;
      }
    }


    // Wait until object is removed
    waitForObjectToLeave();


    Serial.println();
    Serial.println("========================================");
    Serial.println("SERVO = CENTER (90 degrees)");
    Serial.println("========================================");

    Serial.println();
  }


  delay(300);
}
