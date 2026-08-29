#include <Arduino.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "config.h"
#include "mqtt_handler.h"

WiFiClientSecure secureClient;
PubSubClient     mqttClient(secureClient);

void connectMQTT() {
    while (!mqttClient.connected()) {
        Serial.println();
        Serial.println("Connecting to HiveMQ Cloud...");

        String clientId = String(MQTT_CLIENT_ID) + "-" +
                          String((uint32_t)ESP.getEfuseMac(), HEX);

        if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
            Serial.println("MQTT CONNECTED!");
            mqttClient.publish(MQTT_STATUS_TOPIC, "ESP32 ONLINE", true);
        } else {
            Serial.print("MQTT FAILED. State: ");
            Serial.println(mqttClient.state());
            delay(5000);
        }
    }
}

void initMQTT() {
    Serial.println();
    Serial.println("================================");
    Serial.println("MQTT INITIALIZATION");
    Serial.println("================================");

    secureClient.setInsecure();   // temp TLS — OK for prototype
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);

    Serial.print("Broker: "); Serial.println(MQTT_HOST);
    Serial.print("Topic:  "); Serial.println(MQTT_PUB_TOPIC);

    connectMQTT();
}

void maintainMQTT() {
    if (!mqttClient.connected()) connectMQTT();
    mqttClient.loop();
}

void publishSensorData(const SensorData& data) {
    if (!data.dht_valid) {
        Serial.println("Skipping publish — invalid DHT22 data.");
        return;
    }

    char payload[350];
    snprintf(
        payload, sizeof(payload),
        "{"
        "\"device_id\":\"%s\","
        "\"temperature\":%.2f,"
        "\"humidity\":%.2f,"
        "\"mq2_raw\":%d,"
        "\"mq135_raw\":%d,"
        "\"mq7_raw\":%d"
        "}",
        MQTT_CLIENT_ID,
        data.temperature,
        data.humidity,
        data.mq2_raw,
        data.mq135_raw,
        data.mq7_raw
    );

    Serial.println();
    Serial.println("Publishing MQTT data:");
    Serial.println(payload);

    if (mqttClient.publish(MQTT_PUB_TOPIC, payload)) {
        Serial.println("MQTT publish SUCCESS");
    } else {
        Serial.println("MQTT publish FAILED");
    }
}
