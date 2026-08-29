#include <Arduino.h>
#include <WiFi.h>
#include "config.h"
#include "wifi_handler.h"

void connectWiFi() {
    Serial.println();
    Serial.println("================================");
    Serial.println("Wi-Fi INITIALIZATION");
    Serial.println("================================");

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.print("Connecting to Wi-Fi");

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Wi-Fi CONNECTED!");
        Serial.print("ESP32 IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("Wi-Fi FAILED — will retry in loop.");
    }
}

void maintainWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;
    Serial.println("Wi-Fi lost — reconnecting...");
    WiFi.disconnect();
    delay(500);
    connectWiFi();
}
