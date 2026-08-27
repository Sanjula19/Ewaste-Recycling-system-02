// TCS34725 colour sensor check - ESP32 DevKit V1
// Prints raw R / G / B / Clear plus a calculated lux value.
// If the sensor isn't found it scans the I2C bus so you can see
// whether anything is responding at all.

#include <Wire.h>
#include "Adafruit_TCS34725.h"

const int SDA_PIN = 16;   // board pin RX2 / GPIO16
const int SCL_PIN = 17;   // board pin TX2 / GPIO17

Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_154MS,
                                          TCS34725_GAIN_16X);

void scanI2C() {
  Serial.println("Scanning I2C bus...");
  byte found = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  device found at 0x");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) {
    Serial.println("  nothing on the bus - check SDA on GPIO16 (RX2), SCL on GPIO17 (TX2), and 3V3 power to VIN");
  } else {
    Serial.println("  (the TCS34725 should show up at 0x29)");
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);                       // let the serial monitor catch up
  Wire.begin(SDA_PIN, SCL_PIN);

  if (!tcs.begin()) {
    Serial.println("TCS34725 NOT FOUND");
    scanI2C();
    while (1) delay(2000);
  }

  Serial.println("TCS34725 ready");
  Serial.println("R\tG\tB\tClear\tLux");
}

void loop() {
  uint16_t r, g, b, c;
  tcs.getRawData(&r, &g, &b, &c);
  uint16_t lux = tcs.calculateLux(r, g, b);

  Serial.print(r);   Serial.print('\t');
  Serial.print(g);   Serial.print('\t');
  Serial.print(b);   Serial.print('\t');
  Serial.print(c);   Serial.print('\t');
  Serial.println(lux);

  delay(500);
}
