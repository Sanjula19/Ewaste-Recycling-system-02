#ifndef SENSORS_H
#define SENSORS_H

struct SensorData {
    float temperature;
    float humidity;
    int   mq2_raw;
    int   mq135_raw;
    int   mq7_raw;
    bool  dht_valid;
};

void       initSensors();
SensorData readSensors();

#endif
