#ifndef MQTT_HANDLER_H
#define MQTT_HANDLER_H

#include "sensors.h"

void initMQTT();
void maintainMQTT();
void publishSensorData(const SensorData& data);

#endif
