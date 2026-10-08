#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
//  SHEF IoT — GLOBAL CONFIGURATION (declarations)
//  Values are defined in config.cpp — edit values there,
//  this file only declares that they exist.
// ============================================================

// ---------------- PIN DEFINITIONS ----------------
extern const int TRIG_PIN;
extern const int ECHO_PIN;
extern const int MOISTURE_PIN;
extern const int SERVO_PIN;

// ---------------- MOISTURE CALIBRATION ----------------
extern const int  MOISTURE_DRY_REF;
extern const int  MOISTURE_WET_REF;
extern const int  MOISTURE_THRESHOLD;
extern const bool WET_IS_HIGHER;

extern const int MOISTURE_MIN_VALID;
extern const int MOISTURE_MAX_VALID;
extern const int MOISTURE_SAMPLES;

extern const int           STABLE_DRIFT;
extern const int           STABLE_READS_NEEDED;
extern const unsigned long MAX_STABILIZE_TIME;

// ---------------- SERVO SETTINGS ----------------
extern const int HOME_ANGLE;
extern const int DRY_ANGLE;
extern const int WET_ANGLE;

// ---------------- TIMING & DETECTION ----------------
extern const float         DETECTION_DISTANCE;
extern const unsigned long ECHO_TIMEOUT;
extern const unsigned long SETTLE_TIME;
extern const unsigned long SORT_HOLD_TIME;
extern const unsigned long HOME_SETTLE_TIME;
extern const unsigned long OBJECT_CHECK_DELAY;

#endif
