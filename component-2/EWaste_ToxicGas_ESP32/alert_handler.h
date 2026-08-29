#ifndef ALERT_HANDLER_H
#define ALERT_HANDLER_H

#include "sensors.h"

enum AlertLevel {
    ALERT_NORMAL  = 0,
    ALERT_CAUTION = 1,
    ALERT_DANGER  = 2
};

void       initAlerts();
AlertLevel evaluateAlert(const SensorData& data);
void       applyAlert(AlertLevel level);

#endif
