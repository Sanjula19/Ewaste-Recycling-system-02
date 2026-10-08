#ifndef SERVO_CONTROLLER_H
#define SERVO_CONTROLLER_H

// Call once in setup() — attaches the servo and moves it to HOME
void servoInit();

// Moves the servo to a specific angle and waits for the physical move
void moveServo(int angle);

// Immediately commands the servo to HOME_ANGLE (no wait)
void servoGoHome();

// Full sort sequence: move to WET or DRY angle, hold, return home
void sortItem(bool wet);

#endif
