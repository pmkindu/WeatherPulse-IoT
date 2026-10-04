#include <Arduino.h>
#include <Wire.h>
#include <DHT20.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

// --- WLAN & API KONFIGURATION ---
const char* ssid = "Prince Box 2";         // WiFi SSID eintragen
const char* password = "22478026228893134190"; // WiFi Passwort eintragen

// PC-IP
const char* serverUrl = "http://192.168.178.21:8000/telemetry";

DHT20 dht;
WiFiClient wifiClient;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println("\nWeatherPulse-IoT: Starting...");

  // I2C Pins für NodeMCU: SDA = D2 (GPIO4), SCL = D1 (GPIO5)
  Wire.begin(D2, D1);
  dht.begin();

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
}

void loop() {
  int status = dht.read();

  if (status == DHT20_OK) {
    float temp = dht.getTemperature();
    float hum = dht.getHumidity();

    Serial.print("Readings -> Temp: ");
    Serial.print(temp);
    Serial.print(" *C | Humidity: ");
    Serial.print(hum);
    Serial.println(" %");

    // HTTP POST an das FastAPI-Backend senden
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(wifiClient, serverUrl);
      http.addHeader("Content-Type", "application/json");

      // JSON Payload aufbauen
      String jsonPayload = "{\"temperature\": " + String(temp) + ", \"humidity\": " + String(hum) + "}";

      int httpResponseCode = http.POST(jsonPayload);

      if (httpResponseCode > 0) {
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);
      } else {
        Serial.print("Error code: ");
        Serial.println(httpResponseCode);
      }
      http.end();
    } else {
      Serial.println("WiFi Disconnected! Cannot send data.");
    }
  } else {
    Serial.print("ERROR reading DHT20 sensor, status code: ");
    Serial.println(status);
  }

  // Intervall: Alle 60 Sekunden
  delay(60000);
}