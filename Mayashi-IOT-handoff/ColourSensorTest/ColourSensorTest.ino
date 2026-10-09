// TCS34725 colour sensor test - Component 4 material classifier
// ESP32 DevKit V1.
//
// Prints raw R/G/B/Clear twice a second, plus the r/c and b/c ratios the
// backend's classification thresholds are actually expressed in, and says
// whether the current reading would be called copper.
//
// WHY THIS FILE WAS REWRITTEN
// Despite its name, this sketch previously held the HC-SR04 ultrasonic
// test, and before this commit it held a byte-for-byte copy of the whole
// 768-line main/main.ino terminal firmware. Opening it to "check the
// colour sensor" would have flashed the entire terminal. It is now what
// its name says.
//
// ---- WIRING -------------------------------------------------------
// Pins, gain and integration time match main/main.ino exactly, so a
// reading taken here is directly comparable to one the terminal takes.
// Change them in both or in neither.
//
//   VIN -> 3V3        (NOT 5 V - ESP32 GPIOs are not 5 V tolerant)
//   GND -> GND
//   SDA -> GPIO 16    (silkscreen RX2)
//   SCL -> GPIO 17    (silkscreen TX2)
//
// RX2/TX2 are the one place where the Dxx silkscreen does not equal the
// GPIO number: they are GPIO 16 and 17. Everything else on this board is
// Dxx == GPIOxx. SENSOR_PIN_SUMMARY.md has the full map.
//
// Serial Monitor: 115200 baud.
//
// ---- WHAT TO DO WITH THE NUMBERS ----------------------------------
// Ratios, not raw counts, are what classification uses: raw R/G/B all
// scale with how much light reaches the sensor, so they move when the
// room lights change or the item sits a few mm higher. Dividing by Clear
// cancels most of that.
//
// The thresholds below are copied from main/main.ino, measured on this
// bench 26-27 Aug:
//
//   material           r/c     g/c     b/c
//   copper             0.569   0.293   0.248
//   brown cardboard    0.515   0.295   0.197
//   yellow             0.507   0.306   0.177
//   bright neutral     0.569   0.477   0.462
//
// Note the last row: its r/c is IDENTICAL to copper's, which is why blue
// needs a BAND and not just a floor. Copper is red because red DOMINATES
// (green and blue both near 0.25-0.29); a bright neutral surface merely
// leans warm with all three channels close together.
//
// To re-measure a material: hold it still over the sensor, wait for the
// numbers to settle (the illuminator LED ramps for about a second after
// something lands - raw counts climbed 8,384 -> 13,000 over the first 15
// samples on 27 Aug), then read the ratios.

#include <Wire.h>
#include "Adafruit_TCS34725.h"

// Must match main/main.ino.
const int PIN_SDA = 16;   // RX2
const int PIN_SCL = 17;   // TX2

const int PIN_LED_ONBOARD = 2;   // soldered to the board, used to flag a fault

const unsigned long SAMPLE_MS = 500;

// Copied from main/main.ino. Copper vs not-copper is the only question
// three colour channels answer reliably on this bench.
const float COPPER_MIN_RC = 0.55;
const float COPPER_MIN_BC = 0.20;
const float COPPER_MAX_BC = 0.35;

// Same gain and integration time as the terminal firmware.
Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_154MS,
                                          TCS34725_GAIN_16X);

void scanI2C() {
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
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_ONBOARD, OUTPUT);
  delay(500);

  Serial.println();
  Serial.println(F("TCS34725 colour sensor test - Component 4"));
  Serial.print(F("SDA = GPIO ")); Serial.print(PIN_SDA);
  Serial.print(F(" (RX2),  SCL = GPIO ")); Serial.print(PIN_SCL);
  Serial.println(F(" (TX2)"));

  Wire.begin(PIN_SDA, PIN_SCL);
  if (!tcs.begin()) {
    Serial.println(F("TCS34725 NOT FOUND"));
    scanI2C();
    // Nothing useful to do without the sensor, so blink the onboard LED
    // rather than printing zeros that look like real readings.
    while (1) {
      digitalWrite(PIN_LED_ONBOARD, !digitalRead(PIN_LED_ONBOARD));
      delay(300);
    }
  }

  Serial.println(F("TCS34725 ready (16x gain, 154 ms integration)"));
  Serial.println();
  Serial.println(F("     R      G      B      C       r/c     g/c     b/c    copper?"));
  Serial.println(F("  -----  -----  -----  -----    -----   -----   -----   -------"));
}

void loop() {
  uint16_t r, g, b, c;
  tcs.getRawData(&r, &g, &b, &c);

  Serial.print(F("  "));
  Serial.printf("%5u  %5u  %5u  %5u", r, g, b, c);

  // Clear reads 0 in full darkness, or with the sensor unpowered but the
  // bus still answering. Dividing would give inf/NaN, which looks like a
  // sensor fault rather than the "no light" it actually is.
  if (c == 0) {
    Serial.println(F("        --      --      --   (C=0, no light)"));
  } else {
    float rc = (float)r / (float)c;
    float gc = (float)g / (float)c;
    float bc = (float)b / (float)c;

    bool isCopper = (rc >= COPPER_MIN_RC) &&
                    (bc >= COPPER_MIN_BC) && (bc <= COPPER_MAX_BC);

    Serial.printf("    %5.3f   %5.3f   %5.3f   %s",
                  rc, gc, bc, isCopper ? "COPPER" : "-");
    Serial.println();
  }

  delay(SAMPLE_MS);
}
