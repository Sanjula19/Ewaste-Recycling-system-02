/**
 * E-Waste Toxic Gas Detection System Firmware
 * Board: ESP32 DevKit V1
 * 
 * Hardware Pin Mapping:
 * - GPIO 34 (ADC1_CH6) : MQ-2 AOUT (via voltage divider)
 * - GPIO 35 (ADC1_CH7) : MQ-7 AOUT (via voltage divider)
 * - GPIO 32 (ADC1_CH4) : MQ-135 AOUT (via voltage divider)
 * - GPIO 25 (ADC1_CH8) : MQ-136 AOUT (via voltage divider)
 * - GPIO 4  : DHT22 Data (10kΩ pull-up to 3.3V)
 * - GPIO 21 : LCD I2C SDA
 * - GPIO 22 : LCD I2C SCL
 * - GPIO 26 : Red LED (via 220Ω)
 * - GPIO 27 : Yellow LED (via 220Ω)
 * - GPIO 14 : Green LED (via 220Ω)
 * - GPIO 13 : Active Buzzer
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// =========================================================================
// Configuration
// =========================================================================

// WiFi Config
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// MQTT Config
const char* MQTT_BROKER   = "broker.hivemq.com";
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT_ID = "ESP32_EWasteGasMonitor_123";
const char* MQTT_TOPIC    = "ewaste/gas/readings";

// Pin Definitions
#define PIN_MQ2      34 // LPG, Propane, Methane
#define PIN_MQ7      35 // CO
#define PIN_MQ135    32 // Benzene, Ammonia, CO2
#define PIN_MQ136    25 // H2S
#define PIN_DHT      4
#define PIN_LED_RED  26
#define PIN_LED_YEL  27
#define PIN_LED_GRN  14
#define PIN_BUZZER   13

// DHT Sensor
#define DHTTYPE DHT22
DHT dht(PIN_DHT, DHTTYPE);

// LCD Display
// Address usually 0x27 or 0x3F. 16 columns, 2 rows
LiquidCrystal_I2C lcd(0x27, 16, 2); 

// =========================================================================
// Sensor Calibration Parameters
// =========================================================================

// Note on MQ-7: Ideally it needs 60s at 5V and 90s at 1.4V heating cycles.
// We are using simplified continuous read as we use breakout boards.

const float V_REF = 3.3; // ESP32 ADC reference voltage
const int ADC_RES = 4095; // ESP32 ADC resolution (12-bit)

// MQ-2: RL=5k, R0=9.83, a=574.25, b=-2.222 (LPG)
const float MQ2_RL = 5.0;
const float MQ2_R0 = 9.83;
const float MQ2_A = 574.25;
const float MQ2_B = -2.222;

// MQ-7: RL=10k, R0=10.0, a=99.042, b=-1.518 (CO)
const float MQ7_RL = 10.0;
const float MQ7_R0 = 10.0;
const float MQ7_A = 99.042;
const float MQ7_B = -1.518;

// MQ-135: RL=20k, R0=76.63, a=110.47, b=-2.862 (Benzene)
const float MQ135_RL = 20.0;
const float MQ135_R0 = 76.63;
const float MQ135_A = 110.47;
const float MQ135_B = -2.862;

// MQ-136: RL=10k, R0=15.0, a=36.737, b=-3.536 (H2S)
const float MQ136_RL = 10.0;
const float MQ136_R0 = 15.0;
const float MQ136_A = 36.737;
const float MQ136_B = -3.536;

// Safety Thresholds (ppm)
#define CO_SAFE      9.0
#define CO_DANGER    35.0
#define BENZ_SAFE    1.7
#define BENZ_DANGER  5.0
#define H2S_SAFE     5.0
#define H2S_DANGER   10.0
#define LPG_SAFE     1000.0
#define LPG_DANGER   5000.0

// System States
enum SystemState {
  STARTUP,
  WARM_UP,
  CALIBRATE,
  RUNNING
};
SystemState currentState = STARTUP;

// Timers
unsigned long previousMillis = 0;
const long INTERVAL = 5000; // 5 seconds
unsigned long warmupStart = 0;
const long WARMUP_TIME = 60000; // 60 seconds

// Globals
WiFiClient espClient;
PubSubClient client(espClient);
int lcdState = 0;

// Function Prototypes
void connectWiFi();
void connectMQTT();
float readGas(int pin, float RL, float R0, float a, float b);
int checkSafety(float lpg, float co, float benz, float h2s);

void setup() {
  Serial.begin(115200);
  
  // Init Pins
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_YEL, OUTPUT);
  pinMode(PIN_LED_GRN, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  
  // Init LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.print("E-Waste Monitor");
  
  // Init DHT
  dht.begin();
  
  // Setup WiFi and MQTT
  connectWiFi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
  
  // Start Warm-up
  currentState = WARM_UP;
  warmupStart = millis();
  Serial.println("Starting warm-up phase (60s)...");
  lcd.clear();
  lcd.print("Warming up...");
}

void loop() {
  if (!client.connected() && currentState == RUNNING) {
    connectMQTT();
  }
  client.loop();
  
  unsigned long currentMillis = millis();
  
  switch(currentState) {
    case WARM_UP:
      if (currentMillis - warmupStart >= WARMUP_TIME) {
        currentState = CALIBRATE;
        lcd.clear();
        lcd.print("Calibrating...");
        Serial.println("Warm-up complete. Calibrating...");
      }
      break;
      
    case CALIBRATE:
      // Note: Full dynamic calibration usually requires clean air.
      // We will use pre-defined R0 values here.
      delay(2000);
      currentState = RUNNING;
      lcd.clear();
      lcd.print("System Ready!");
      Serial.println("System Ready and Running.");
      break;
      
    case RUNNING:
      if (currentMillis - previousMillis >= INTERVAL) {
        previousMillis = currentMillis;
        
        // Read DHT
        float h = dht.readHumidity();
        float t = dht.readTemperature();
        
        // Read Gases
        float lpg  = readGas(PIN_MQ2, MQ2_RL, MQ2_R0, MQ2_A, MQ2_B);
        float co   = readGas(PIN_MQ7, MQ7_RL, MQ7_R0, MQ7_A, MQ7_B);
        float benz = readGas(PIN_MQ135, MQ135_RL, MQ135_R0, MQ135_A, MQ135_B);
        float h2s  = readGas(PIN_MQ136, MQ136_RL, MQ136_R0, MQ136_A, MQ136_B);
        
        // Graceful handling of missing sensors (if ADC reads 0, set ppm to 0)
        if (lpg < 0) lpg = 0;
        if (co < 0) co = 0;
        if (benz < 0) benz = 0;
        if (h2s < 0) h2s = 0;

        // Print to Serial
        Serial.printf("T:%.1fC H:%.1f%% | LPG:%.1f CO:%.1f Benz:%.1f H2S:%.1f (ppm)\n", t, h, lpg, co, benz, h2s);
        
        // Update LCD
        lcd.clear();
        if (lcdState == 0) {
          lcd.setCursor(0, 0);
          lcd.printf("T:%.1fC H:%.1f%%", t, h);
          lcd.setCursor(0, 1);
          lcd.printf("CO:%.1f ppm", co);
        } else if (lcdState == 1) {
          lcd.setCursor(0, 0);
          lcd.printf("Benz:%.1f ppm", benz);
          lcd.setCursor(0, 1);
          lcd.printf("H2S:%.1f ppm", h2s);
        } else {
          lcd.setCursor(0, 0);
          lcd.printf("LPG:%.1f ppm", lpg);
        }
        lcdState = (lcdState + 1) % 3;
        
        // Status Check
        int status = checkSafety(lpg, co, benz, h2s);
        digitalWrite(PIN_LED_GRN, status == 0 ? HIGH : LOW);
        digitalWrite(PIN_LED_YEL, status == 1 ? HIGH : LOW);
        digitalWrite(PIN_LED_RED, status == 2 ? HIGH : LOW);
        
        if (status == 2) {
          tone(PIN_BUZZER, 1000, 500); // 1kHz beep for 500ms
        } else {
          noTone(PIN_BUZZER);
        }
        
        // Publish JSON
        char payload[256];
        snprintf(payload, sizeof(payload), 
          "{\"temp\":%.1f,\"hum\":%.1f,\"lpg\":%.1f,\"co\":%.1f,\"benzene\":%.1f,\"h2s\":%.1f,\"status\":%d}",
          t, h, lpg, co, benz, h2s, status);
          
        if (client.publish(MQTT_TOPIC, payload)) {
          Serial.println("MQTT Publish OK");
        } else {
          Serial.println("MQTT Publish Failed");
        }
      }
      break;
      
    default:
      break;
  }
}

// Read gas sensor and calculate ppm
float readGas(int pin, float RL, float R0, float a, float b) {
  int adcVal = analogRead(pin);
  if (adcVal == 0 || adcVal >= ADC_RES) return -1.0; // Sensor missing or disconnected/shorted
  
  float vOut = (adcVal / (float)ADC_RES) * V_REF;
  if (vOut == 0) return -1.0;
  
  float Rs = RL * (V_REF - vOut) / vOut;
  float ratio = Rs / R0;
  
  // ppm = a * (Rs/R0)^b
  float ppm = a * pow(ratio, b);
  return ppm;
}

// Check safety levels and return status: 0=Safe, 1=Caution, 2=Danger
int checkSafety(float lpg, float co, float benz, float h2s) {
  int level = 0;
  
  // Caution checks
  if (co >= CO_SAFE || benz >= BENZ_SAFE || h2s >= H2S_SAFE || lpg >= LPG_SAFE) {
    level = 1;
  }
  
  // Danger checks
  if (co >= CO_DANGER || benz >= BENZ_DANGER || h2s >= H2S_DANGER || lpg >= LPG_DANGER) {
    level = 2;
  }
  
  return level;
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected.");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT broker...");
    if (client.connect(MQTT_CLIENT_ID)) {
      Serial.println(" connected!");
    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}
