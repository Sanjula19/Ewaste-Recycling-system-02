#ifndef MOISTURE_SENSOR_H
#define MOISTURE_SENSOR_H

// Call once in setup() to configure the analog pin
void moistureInit();

// Single averaged reading (10 samples) — fast, but may catch a
// mid-transition value. Prefer readMoistureStable() for real decisions.
int readMoisture();

// Waits until consecutive readings stop changing before returning —
// this is what the main sorting logic should actually use.
int readMoistureStable();

// True if the value is within the expected sensor range
// (outside this range usually means a disconnected/faulty sensor)
bool moistureValid(int value);

// True if the value indicates a WET item, based on threshold + direction
bool isWet(int value);

#endif
