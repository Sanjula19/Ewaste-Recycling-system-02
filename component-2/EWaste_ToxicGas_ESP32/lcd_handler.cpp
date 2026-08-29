#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "config.h"
#include "lcd_handler.h"

LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);

// ── Helper: right-aligned number in fixed width ──────────────
void printPadded(int value, int width) {
    String s = String(value);
    while (s.length() < (unsigned)width) s = " " + s;
    lcd.print(s);
}

void initLCD() {
    Wire.begin(LCD_SDA, LCD_SCL);
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("E-Waste Monitor ");
    lcd.setCursor(0, 1);
    lcd.print("  Initializing..");
    delay(1500);
    lcd.clear();
    Serial.println("LCD initialized.");
}

void showReadyScreen() {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("System  Ready!  ");
    lcd.setCursor(0, 1);
    lcd.print("  Monitoring... ");
    delay(1000);
    lcd.clear();
}

void updateLCD(const SensorData& data, AlertLevel level) {

    static bool          screenA    = true;
    static unsigned long lastSwitch = 0;
    const  unsigned long SWITCH_MS  = 3000;   // swap every 3 seconds

    // ── Switch screen every 3 seconds ──
    unsigned long now = millis();
    if (now - lastSwitch >= SWITCH_MS) {
        lastSwitch = now;
        screenA    = !screenA;
        lcd.clear();   // clear ONCE on switch — no constant flicker
    }

    // ── Status text (exactly 8 chars) ──
    const char* status;
    if      (level == ALERT_DANGER)  status = " DANGER ";
    else if (level == ALERT_CAUTION) status = "CAUTION ";
    else                             status = "  SAFE  ";

    if (screenA) {
        // ════════════════════
        //  SCREEN A: Gas Sensors
        // ════════════════════
        //
        //  Row 0: "2:XXXX 7:XXXX   "   (MQ-2 and MQ-7)
        //  Row 1: "135:XXXX DANGER "   (MQ-135 and status)

        lcd.setCursor(0, 0);
        lcd.print("2:");
        printPadded(data.mq2_raw, 4);
        lcd.print(" 7:");
        printPadded(data.mq7_raw, 4);
        lcd.print("   ");            // 3 spaces → fills to 16 chars

        lcd.setCursor(0, 1);
        lcd.print("135:");
        printPadded(data.mq135_raw, 4);
        lcd.print(status);           // 8 chars → fills to 16 chars

    } else {
        // ════════════════════
        //  SCREEN B: Temperature & Humidity
        // ════════════════════
        //
        //  Row 0: "T:32C   H:81%   "   (left half temp, right half humidity)
        //  Row 1: "    ALL SAFE    "   (status centered)

        // Left half of row 0 (columns 0–7): temperature
        lcd.setCursor(0, 0);
        lcd.print("T:");
        lcd.print((int)data.temperature);
        lcd.print("C");

        // Right half of row 0 (columns 8–15): humidity
        lcd.setCursor(8, 0);
        lcd.print("H:");
        lcd.print((int)data.humidity);
        lcd.print("%");

        // Row 1: status centered (all exactly 16 chars)
        lcd.setCursor(0, 1);
        if      (level == ALERT_DANGER)  lcd.print("    ** DANGER **");
        else if (level == ALERT_CAUTION) lcd.print("   * CAUTION *  ");
        else                             lcd.print("    ALL SAFE    ");
    }
}