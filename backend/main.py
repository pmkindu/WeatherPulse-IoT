from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import time
import openmeteo_requests
import requests_cache
from retry_requests import retry

app = FastAPI(title="WeatherPulse-IoT API")

# In-Memory-Speicher für Telemetriedaten
telemetry_db: List[dict] = []

# Koordinaten für Bad Waldsee
LATITUDE = 47.92
LONGITUDE = 9.75

# Open-Meteo Client mit Cache und Retry-Logik
cache_session = requests_cache.CachedSession('.cache', expire_after=600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


class TelemetryData(BaseModel):
    temperature: float
    humidity: float
    timestamp: Optional[float] = None


def fetch_open_meteo_weather():
    """Holt die aktuellen Wetterdaten von Open-Meteo für Bad Waldsee."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ["temperature_2m", "relative_humidity_2m"]
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        current = response.Current()
        return {
            "temperature": round(current.Variables(0).Value(), 1),
            "humidity": round(current.Variables(1).Value(), 1)
        }
    except Exception as e:
        print(f"Fehler beim Abrufen der Open-Meteo Daten: {e}")
        return None


def validate_telemetry(data: TelemetryData) -> dict:
    """Führt Plausibilitätsprüfungen durch."""
    is_plausible = True
    warnings = []

    # 1. Grenzwertprüfung
    if not (-30.0 <= data.temperature <= 60.0):
        is_plausible = False
        warnings.append(f"Unrealistische Temperatur: {data.temperature}°C")

    if not (0.0 <= data.humidity <= 100.0):
        is_plausible = False
        warnings.append(f"Unrealistische Luftfeuchtigkeit: {data.humidity}%")

    # 2. Sprungerkennung
    if telemetry_db:
        last_entry = telemetry_db[-1]
        temp_diff = abs(data.temperature - last_entry["temperature"])
        if temp_diff > 10.0:
            is_plausible = False
            warnings.append(f"Temperatursprung zu hoch: ΔT = {temp_diff:.1f}°C")

    # 3. Abgleich mit Open-Meteo API
    ref_weather = fetch_open_meteo_weather()
    if ref_weather:
        api_temp_diff = abs(data.temperature - ref_weather["temperature"])
        if api_temp_diff > 5.0:
            is_plausible = False
            warnings.append(
                f"Starke Abweichung zur Wetter-API: ΔT = {api_temp_diff:.1f}°C "
                f"(Referenz: {ref_weather['temperature']}°C)"
            )

    return {
        "is_plausible": is_plausible,
        "warnings": warnings,
        "reference_weather": ref_weather
    }


# Statische Dateien einbinden
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    """Liefert die Hauptseite (Dashboard) aus."""
    return FileResponse("static/index.html")


@app.get("/api/status")
def read_status():
    """Systemstatus-Endpunkt."""
    return {"status": "online", "system": "WeatherPulse-IoT"}


@app.post("/telemetry")
def receive_telemetry(data: TelemetryData):
    """Nimmt Messwerte entgegen, prüft auf Plausibilität und speichert sie."""
    current_time = data.timestamp if data.timestamp else time.time()
    validation = validate_telemetry(data)

    record = {
        "temperature": data.temperature,
        "humidity": data.humidity,
        "timestamp": current_time,
        "is_plausible": validation["is_plausible"],
        "warnings": validation["warnings"],
        "reference_weather": validation["reference_weather"]
    }

    telemetry_db.append(record)

    return {
        "status": "success",
        "received": record
    }


@app.get("/telemetry")
def get_telemetry_history():
    """Gibt die gespeicherten Telemetriedaten zurück."""
    return telemetry_db


@app.get("/external-weather")
def get_external_weather():
    """Gibt die aktuellen Wetterdaten der Open-Meteo API zurück."""
    weather = fetch_open_meteo_weather()
    if not weather:
        raise HTTPException(status_code=503, detail="Wetter-API nicht erreichbar")
    return {
        "location": "Bad Waldsee",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "temperature": weather["temperature"],
        "humidity": weather["humidity"]
    }