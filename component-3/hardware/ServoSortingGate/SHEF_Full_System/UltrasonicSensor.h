#ifndef ULTRASONIC_SENSOR_H
#define ULTRASONIC_SENSOR_H

// Call once in setup() to configure the Trig/Echo pins
void ultrasonicInit();

// Returns distance in cm, or -1 if no echo was received
float readDistance();

#endif
