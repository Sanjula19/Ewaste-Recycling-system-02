#ifndef LCD_HANDLER_H
#define LCD_HANDLER_H

#include "sensors.h"
#include "alert_handler.h"

void initLCD();
void updateLCD(const SensorData& data, AlertLevel level);
void showReadyScreen();

#endif
