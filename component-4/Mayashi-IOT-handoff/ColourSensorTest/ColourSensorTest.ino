// HC-SR04 ultrasonic test - Component 4 bin-level sensor
// ESP32 DevKit V1.
//
// Prints the measured distance twice a second and flags BIN FULL once
// the surface is closer than the lockout threshold.
//
// ---- READ THIS BEFORE PLUGGING IN --------------------------------
// The sensor runs on 5 V, so its Echo pin drives 5 V. ESP32 GPIOs are
// 3.3 V parts and are NOT 5 V tolerant. Echo must reach GPIO 18 through
// a divider, never directly:
//
//   Echo ──[ 1 kΩ ]──┬──▶ GPIO 18      junction sits at ~3.33 V
//                    │
//                 [ 2 kΩ ]
//                    │
//                   GND
//
//   5 V x 2k / (1k + 2k) = 3.33 V
//
// Trig is an ESP32 output going into a 5 V input, which is fine direct -
// the HC-SR04 reads anything above ~2.5 V as high. Only Echo needs the
// divider.
// -------------------------------------------------------------------
//
// Wiring:
//   VCC  -> VIN (5 V, NOT 3V3 - the module browns out at 3.3 V)
//   GND  -> GND rail
//   Trig -> GPIO 5  (D5)   direct
//   Echo -> GPIO 18 (D18)  THROUGH THE DIVIDER ABOVE

const int TRIG_PIN = 5;    // board pin D5
const int ECHO_PIN = 22;   // board pin D18 - via 1k/2k divider

// Bin is considered full when the waste surface rises to within this
// distance of the lid-mounted sensor. 5 cm per the design doc; measure
// against the real bin and adjust.
const float BIN_FULL_CM = 5.0;

// pulseIn gives up after this long. 30 ms of round trip is about 5 m,
// comfortably past the HC-SR04's useful 4 m range, and it keeps the
// loop from stalling when no echo comes back at all.
const unsigned long ECHO_TIMEOUT_US = 30000UL;

// Speed of sound is 343 m/s = 0.0343 cm/us. The pulse travels to the
// target and back, hence the halving.
const float CM_PER_US = 0.0343f / 2.0f;

const int SAMPLES = 5;   // median of this many pings per printed row

// Returns distance in cm, or -1 if nothing echoed back.
float pingOnce() {
  // A clean low before the pulse - a floating Trig can otherwise latch
  // the module into re-triggering itself.
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);        // datasheet: 10 us minimum trigger
  digitalWrite(TRIG_PIN, LOW);

  unsigned long us = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (us == 0) return -1.0f;    // timed out - out of range or miswired

  return us * CM_PER_US;
}

// Median, not mean. The HC-SR04 throws occasional wild readings when an
// echo bounces off the bin wall instead of the waste, and a single
// spike drags an average badly - the median just ignores it.
float measure() {
  float v[SAMPLES];
  int n = 0;

  for (int i = 0; i < SAMPLES; i++) {
    float d = pingOnce();
    if (d > 0) v[n++] = d;
    delay(60);   // >60 ms between pings, or the previous burst echoes
                 // back into the next reading
  }

  if (n == 0) return -1.0f;

  // insertion sort - n is 5, anything cleverer is wasted
  for (int i = 1; i < n; i++) {
    float key = v[i];
    int j = i - 1;
    while (j >= 0 && v[j] > key) {
      v[j + 1] = v[j];
      j--;
    }
    v[j + 1] = key;
  }

  return v[n / 2];
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  Serial.println("HC-SR04 test - Trig D5, Echo D18 (via 1k/2k divider)");
  Serial.print("bin-full threshold: ");
  Serial.print(BIN_FULL_CM, 1);
  Serial.println(" cm");
  Serial.println("Move your hand towards the sensor to watch the distance close.");
  Serial.println();
}

void loop() {
  float cm = measure();

  if (cm < 0) {
    // Every ping timed out. Either nothing is in range, or Echo is not
    // actually reaching the pin.
    Serial.println("no echo - out of range, or check Echo on D18 and 5 V on VCC");
  } else {
    Serial.print(cm, 1);
    Serial.print(" cm");

    if (cm <= BIN_FULL_CM) {
      Serial.print("   <-- BIN FULL");
    }
    Serial.println();
  }

  delay(500);
}
