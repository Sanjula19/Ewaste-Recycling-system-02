#include <Arduino.h>
#include "config.h"
#include "alert_handler.h"

void initAlerts() {
    pinMode(LED_GREEN,  OUTPUT);
    pinMode(LED_YELLOW, OUTPUT);
    pinMode(LED_RED,    OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);

    // Boot state — green ON
    digitalWrite(LED_GREEN,  HIGH);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED,    LOW);
    digitalWrite(BUZZER_PIN, LOW);

    Serial.println("Alert system initialized.");
}

AlertLevel evaluateAlert(const SensorData& data) {
     int maxReading = max({data.mq2_raw, data.mq135_raw, data.mq7_raw});
    if (maxReading >= THRESHOLD_RED)    return ALERT_DANGER;
    if (maxReading >= THRESHOLD_YELLOW) return ALERT_CAUTION;
    return ALERT_NORMAL;
}

void applyAlert(AlertLevel level) {
    digitalWrite(LED_GREEN,  LOW);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED,    LOW);
    digitalWrite(BUZZER_PIN, LOW);

    if (level == ALERT_NORMAL) {
        digitalWrite(LED_GREEN, HIGH);

    } else if (level == ALERT_CAUTION) {
        digitalWrite(LED_YELLOW, HIGH);
        // 1 short beep
        digitalWrite(BUZZER_PIN, HIGH);
        delay(200);
        digitalWrite(BUZZER_PIN, LOW);

    } else if (level == ALERT_DANGER) {
        digitalWrite(LED_RED, HIGH);
        // 3 fast beeps
        for (int i = 0; i < 3; i++) {
            digitalWrite(BUZZER_PIN, HIGH);
            delay(150);
            digitalWrite(BUZZER_PIN, LOW);
            delay(100);
        }
    }
}
