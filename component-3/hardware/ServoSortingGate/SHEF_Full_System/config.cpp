#include "config.h"

// ============================================================
//  SHEF IoT — GLOBAL CONFIGURATION (values)
//  THIS is the file you edit to calibrate or tune the system.
//  config.h just declares these exist; this file sets them.
// ============================================================

// ---------------- PIN DEFINITIONS ----------------
const int TRIG_PIN      = 5;
const int ECHO_PIN      = 18;
const int MOISTURE_PIN  = 35;
const int SERVO_PIN     = 13;


// ---------------- MOISTURE CALIBRATION ----------------

// Your measured dry/open-air value (CONFIRMED, stable)
const int MOISTURE_DRY_REF = 3657;

// IMPORTANT: Replace 2400 with your FINAL stable wet reading.
// Test with a real wet item, wait for "(stable)" to print, use that number.
const int MOISTURE_WET_REF = 2400;

// Automatically calculated midpoint — no need to compute by hand
const int MOISTURE_THRESHOLD = (MOISTURE_DRY_REF + MOISTURE_WET_REF) / 2;

// Your sensor reads LOWER when wet (confirmed from your test data)
const bool WET_IS_HIGHER = false;

// Valid reading range — outside this means sensor disconnected/faulty
const int MOISTURE_MIN_VALID = 1500;
const int MOISTURE_MAX_VALID = 4095;

// Number of samples averaged per single reading
const int MOISTURE_SAMPLES = 10;

// Stabilization polling — prevents reading mid-transition values
const int           STABLE_DRIFT        = 15;    // ADC counts — considered stable below this change
const int           STABLE_READS_NEEDED = 3;      // consecutive stable readings required
const unsigned long MAX_STABILIZE_TIME  = 4000;   // ms — safety timeout if it never settles


// ---------------- SERVO SETTINGS ----------------
const int HOME_ANGLE = 90;   // neutral: gate flat/centered
const int DRY_ANGLE  = 25;   // tips LEFT toward dry bin
const int WET_ANGLE  = 155;  // tips RIGHT toward wet bin


// ---------------- TIMING & DETECTION ----------------
const float         DETECTION_DISTANCE = 13.0;   // cm
const unsigned long ECHO_TIMEOUT       = 30000;  // us — prevents loop freeze on no echo
const unsigned long SETTLE_TIME        = 800;    // ms — initial wait before sampling moisture
const unsigned long SORT_HOLD_TIME     = 1200;   // ms — hold gate open over bin
const unsigned long HOME_SETTLE_TIME   = 1000;   // ms — time for servo to physically return home
const unsigned long OBJECT_CHECK_DELAY = 200;    // ms — polling interval while waiting for object to leave
