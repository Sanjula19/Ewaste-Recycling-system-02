#include <Arduino.h>
#include <DHT.h>
#include "config.h"
#include "sensors.h"

DHT dht(DHTPIN, DHTTYPE);

int readAverageADC(int pin) {
    long total = 0;
    for (int i = 0; i < SENSOR_SAMPLE_COUNT; i++) {
        total += analogRead(pin);
        delay(SENSOR_SAMPLE_DELAY_MS);
    }
    return total / SENSOR_SAMPLE_COUNT;
}

void initSensors() {
    Serial.println();
    Serial.println("================================");
    Serial.println("SENSOR INITIALIZATION");
    Serial.println("================================");

    analogReadResolution(12);
    pinMode(MQ2_PIN,   INPUT);
    pinMode(MQ135_PIN, INPUT);
    pinMode(MQ7_PIN,   INPUT);

    dht.begin();

    Serial.println("DHT22  initialized.");
    Serial.println("MQ-2   initialized.");
    Serial.println("MQ-135 initialized.");
    Serial.println("MQ-7   initialized (not wired yet).");
}

SensorData readSensors() {
    SensorData data;

    data.temperature = dht.readTemperature();
    data.humidity    = dht.readHumidity();

    if (isnan(data.temperature) || isnan(data.humidity)) {
        data.dht_valid = false;
        Serial.println("WARNING: DHT22 reading failed.");
    } else {
        data.dht_valid = true;
    }

    data.mq2_raw   = readAverageADC(MQ2_PIN);
    data.mq135_raw = readAverageADC(MQ135_PIN);
    data.mq7_raw   = readAverageADC(MQ7_PIN);   // 0 until wired

    return data;
}
