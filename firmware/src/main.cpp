#include <Arduino.h>
#include <Wire.h>
#include <DHT20.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <U8g2lib.h>
#include <ArduinoJson.h>

// --- WLAN & API KONFIGURATION ---
const char* ssid = "Prince Box 2";               // WiFi SSID
const char* password = "22478026228893134190";   // WiFi Passwort

// Server-URL
// const char* serverUrl = "http://192.168.178.21:8000/telemetry";
const char* serverUrl = "http://63.187.26.225:8000/telemetry";

// --- SENSOR & DISPLAY INSTANZEN ---
DHT20 dht;
WiFiClient wifiClient;

// 1.3" I2C OLED (SH1106 Chip)
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
// Falls ein SSD1306 Display genutzt wird, stattdessen folgende Zeile einkommentieren:
// U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

// Globale Variablen für Display-Anzeige
float localTemp = 0.0;
float localHum = 0.0;
float apiTemp = 0.0;
float apiHum = 0.0;
bool isPlausible = true;
bool hasApiData = false;
String statusText = "Verbinde...";

// --- DISPLAY REFRESH FUNKTION ---
void updateDisplay() {
  u8g2.clearBuffer();

  // Header / Titel
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(0, 10, "WeatherPulse-IoT");
  u8g2.drawLine(0, 12, 128, 12);

  // Sensor Messwerte (DHT20)
  u8g2.setCursor(0, 25);
  u8g2.print("Sensor: ");
  u8g2.print(localTemp, 1);
  u8g2.print("C  ");
  u8g2.print((int)localHum);
  u8g2.print("%");

  // Open-Meteo API Referenzwerte
  u8g2.setCursor(0, 40);
  u8g2.print("API:    ");
  if (hasApiData) {
    u8g2.print(apiTemp, 1);
    u8g2.print("C  ");
    u8g2.print((int)apiHum);
    u8g2.print("%");
  } else {
    u8g2.print("Lade Daten...");
  }

  u8g2.drawLine(0, 44, 128, 44);

  // Plausibilitäts-Status Zeile
  u8g2.setCursor(0, 58);
  u8g2.print("Status: ");
  u8g2.print(statusText);

  u8g2.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println("\nWeatherPulse-IoT: Starting...");

  // I2C Pins für NodeMCU: SDA = D2 (GPIO4), SCL = D1 (GPIO5)
  Wire.begin(D2, D1);
  dht.begin();

  // OLED Display initialisieren
  u8g2.begin();
  updateDisplay();

  // WLAN Verbindung aufbauen
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  statusText = "WLAN OK";
  updateDisplay();
}

void loop() {
  int status = dht.read();

  if (status == DHT20_OK) {
    localTemp = dht.getTemperature();
    localHum = dht.getHumidity();

    Serial.print("Readings -> Temp: ");
    Serial.print(localTemp);
    Serial.print(" *C | Humidity: ");
    Serial.print(localHum);
    Serial.println(" %");

    // HTTP POST an das FastAPI-Backend senden
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(wifiClient, serverUrl);
      http.addHeader("Content-Type", "application/json");

      // JSON Payload aufbauen
      String jsonPayload = "{\"temperature\":" + String(localTemp, 2) + 
                           ",\"humidity\":" + String(localHum, 2) + "}";

      int httpResponseCode = http.POST(jsonPayload);

      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);
        Serial.println("Response: " + response);

        // Server-Antwort parsen (falls das Backend Referenzwerte & Status zurückgibt)
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, response);

if (!error) {
          // 1. API-Referenzwetter auslesen (direkte Prüfung auf Temperatur-Feld)
          if (doc["reference_weather"].containsKey("temperature")) {
            apiTemp = doc["reference_weather"]["temperature"];
            apiHum  = doc["reference_weather"]["humidity"];
            hasApiData = true;
          } 
          // Falls die Werte flach im JSON liegen
          else if (doc.containsKey("api_temperature")) {
            apiTemp = doc["api_temperature"];
            apiHum  = doc["api_humidity"];
            hasApiData = true;
          }

          // 2. Plausibilität auslesen (unter 'received' oder auf Hauptebene)
          if (doc["received"].containsKey("is_plausible")) {
            isPlausible = doc["received"]["is_plausible"];
          } else if (doc.containsKey("is_plausible")) {
            isPlausible = doc["is_plausible"];
          }

          // 3. Status-Text festlegen
          if (isPlausible) {
            statusText = "OK (Normal)";
          } else {
            statusText = "AUFFAELLIG!";
          }
        } else {
          statusText = "Gesendet OK";
        }
      } else {
        Serial.print("Error code: ");
        Serial.println(httpResponseCode);
        statusText = "HTTP Fehler!";
      }
      http.end();
    } else {
      Serial.println("WiFi Disconnected! Cannot send data.");
      statusText = "Kein WLAN";
    }
  } else {
    Serial.print("ERROR reading DHT20 sensor, status code: ");
    Serial.println(status);
    statusText = "Sensor Fehler";
  }

  // OLED Display aktualisieren
  updateDisplay();

  // Intervall: Alle 60 Sekunden
  delay(60000);
}