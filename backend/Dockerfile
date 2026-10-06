# Offizielles Python-Image als Basis nutzen
FROM python:3.14-slim

# Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Requirements kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den gesamten Backend-Code kopieren
COPY . .

# Port 8000 für den Container freigeben
EXPOSE 8000

# Server beim Starten des Containers ausführen
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]