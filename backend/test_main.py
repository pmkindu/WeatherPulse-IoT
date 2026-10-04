from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app, telemetry_db, fetch_open_meteo_weather


try:
    client = TestClient(app)
except TypeError:
    client = TestClient(app=app)


def setup_function():
    # Vor jedem Test den In-Memory-Speicher leeren
    telemetry_db.clear()


def test_read_root():
    # Testen, ob die Hauptseite HTML ausliefert
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_read_status():
    # Testen des System-Status-Endpunkts
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "system": "WeatherPulse-IoT"}


def test_post_telemetry_success():
    # Holen der aktuellen Live-Wert, damit die Abweichung im Test immer 0 ist
    ext_weather = client.get("/external-weather").json()
    ref_temp = ext_weather.get("temperature", 15.0)

    payload = {"temperature": ref_temp, "humidity": 50.0}
    response = client.post("/telemetry", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["received"]["is_plausible"] is True
    assert len(data["received"]["warnings"]) == 0


def test_post_telemetry_invalid_extremes():
    # Test mit unrealistischer Temperatur (80°C)
    payload = {"temperature": 80.0, "humidity": 50.0}
    response = client.post("/telemetry", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["received"]["is_plausible"] is False
    assert any("Unrealistische Temperatur" in w for w in data["received"]["warnings"])


def test_post_telemetry_sudden_jump():
    # 1. Erster Messwert
    client.post("/telemetry", json={"temperature": 15.0, "humidity": 50.0})
    
    # 2. Plötzlicher Sprung um 15°C auf 30°C
    response = client.post("/telemetry", json={"temperature": 30.0, "humidity": 50.0})
    
    assert response.status_code == 200
    data = response.json()
    assert data["received"]["is_plausible"] is False
    assert any("Temperatursprung zu hoch" in w for w in data["received"]["warnings"])


def test_get_telemetry_history():
    # Testen der Historie-Abfrage
    client.post("/telemetry", json={"temperature": 22.5, "humidity": 45.0})
    response = client.get("/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["temperature"] == 22.5


def test_get_external_weather():
    response = client.get("/external-weather")
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Bad Waldsee"
    assert "temperature" in data
    assert "humidity" in data


def test_get_external_weather_failure():
    # Simuliert den 503-Fehler, wenn Open-Meteo nicht antwortet
    with patch("main.fetch_open_meteo_weather", return_value=None):
        response = client.get("/external-weather")
        assert response.status_code == 503
        assert response.json()["detail"] == "Wetter-API nicht erreichbar"