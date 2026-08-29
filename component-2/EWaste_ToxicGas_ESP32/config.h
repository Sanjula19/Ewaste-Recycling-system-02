#ifndef CONFIG_H
#define CONFIG_H

// ======================================================
// Wi-Fi
// ======================================================
#define WIFI_SSID     "S A N J U L A"
#define WIFI_PASSWORD "sanjula@1234"

// ======================================================
// HiveMQ Cloud
// ======================================================
#define MQTT_HOST      "8c22931e95374473bea07f2ce5b65093.s1.eu.hivemq.cloud"
#define MQTT_PORT      8883
#define MQTT_USER      "hivemq.webclient.1786954284059"
#define MQTT_PASSWORD  "3yFM1cjfifMAV4UzzbReWpykGepk9cCO"
#define MQTT_CLIENT_ID "ESP32_EWASTE_01"
#define MQTT_PUB_TOPIC    "ewaste/esp32/sensors"
#define MQTT_STATUS_TOPIC "ewaste/esp32/status"

// ======================================================
// DHT22
// ======================================================
#define DHTPIN  4
#define DHTTYPE DHT22

// ======================================================
// MQ Sensors
// ======================================================
#define MQ2_PIN   34
#define MQ135_PIN 32
#define MQ7_PIN   35   // add tomorrow — reads 0 until wired

// ======================================================
// LEDs
// ======================================================
#define LED_GREEN  14
#define LED_YELLOW 27
#define LED_RED    26


// ======================================================
// Buzzer
// ======================================================
#define BUZZER_PIN 13

// ======================================================
// LCD I2C
// ======================================================
#define LCD_SDA      21
#define LCD_SCL      22
#define LCD_I2C_ADDR 0x27   // if blank try 0x3F
#define LCD_COLS     16
#define LCD_ROWS     2

// ======================================================
// Alert thresholds — raw ADC (0-4095)
// NOT WHO limits — prototype thresholds only
// ======================================================
#define THRESHOLD_YELLOW 2300
#define THRESHOLD_RED    3000   // high sensor response

// ======================================================
// Timing
// ======================================================
#define SENSOR_SAMPLE_COUNT    10
#define SENSOR_SAMPLE_DELAY_MS 10
#define MQTT_PUBLISH_INTERVAL  5000

#endif
