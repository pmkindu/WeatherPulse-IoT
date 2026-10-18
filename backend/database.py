from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite-Datenbankdatei im Backend-Verzeichnis
SQLALCHEMY_DATABASE_URL = "sqlite:///./weather_data.db"

# connect_args={"check_same_thread": False} ist speziell für SQLite mit FastAPI erforderlich
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class WeatherData(Base):
    __tablename__ = "weather_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    status = Column(String, default="OK")  # OK, WARNING, ERROR, etc.
    message = Column(String, default="Normal operation")  # Detailmeldung der Plausibilitätsprüfung
    ref_temperature = Column(Float, nullable=True)  # Open-Meteo Referenztemperatur


# Erstellt die Tabellen automatisch beim Start, falls sie noch nicht existieren
def init_db():
    Base.metadata.create_all(bind=engine)


# Dependency für FastAPI Endpunkte
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()