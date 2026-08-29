#include <Arduino.h>
#include "config.h"
#include "wifi_handler.h"
#include "sensors.h"
#include "mqtt_handler.h"
#include "alert_handler.h"
#include "lcd_handler.h"

unsigned long lastPublish = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("================================");
    Serial.println("ESP32 E-WASTE GAS MONITOR");
    Serial.println("================================");

    initSensors();    // DHT22 + MQ sensors
    initAlerts();     // LEDs + Buzzer
    initLCD();        // LCD I2C
    connectWiFi();    // WiFi connection
    initMQTT();       // HiveMQ Cloud

    // Startup beep — 1 beep = system ready
    digitalWrite(BUZZER_PIN, HIGH);
    delay(300);
    digitalWrite(BUZZER_PIN, LOW);

    showReadyScreen();

    Serial.println("System ready.");
}

void loop() {
    maintainWiFi();
    maintainMQTT();

    // Run sensor cycle at the configured interval
    if (millis() - lastPublish >= MQTT_PUBLISH_INTERVAL) {
        lastPublish = millis();

        // 1. Read all sensors
        SensorData data = readSensors();

        // 2. Evaluate alert level
        AlertLevel level = evaluateAlert(data);

        // 3. Apply LEDs + Buzzer
        applyAlert(level);

        // 4. Update LCD display
        updateLCD(data, level);

        // 5. Publish to MQTT → Backend → Dashboard
        publishSensorData(data);
    }
}