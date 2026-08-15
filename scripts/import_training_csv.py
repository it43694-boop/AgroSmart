import csv
import datetime
import sys
from pathlib import Path

from database import SessionLocal, init_db
import models

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


def _load_rows(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return list(pd.read_csv(file_path).to_dict(orient="records")) if pd is not None else list(csv.DictReader(file_path.open("r", encoding="utf-8-sig", newline="")))
    if suffix in {".xlsx", ".xls"}:
        if pd is None:
            raise RuntimeError("pandas est requis pour importer des fichiers Excel")
        return list(pd.read_excel(file_path).to_dict(orient="records"))
    raise ValueError("Format non supporté. Utilisez un fichier CSV ou Excel")


def import_data(path: str):
    init_db()
    db = SessionLocal()
    try:
        user = db.query(models.User).first()
        if user is None:
            user = models.User(
                full_name="Demo Farmer",
                email="demo@example.com",
                username="demo_farmer",
                hashed_password="demo-password",
                role="farmer",
                is_validated=True,
                is_active=True,
            )
            db.add(user)
            db.flush()

        crop = db.query(models.Crop).filter(models.Crop.owner_id == user.id).first()
        if crop is None:
            crop = models.Crop(name="Maïs importé", surface=3.0, owner_id=user.id)
            db.add(crop)
            db.flush()

        rows = _load_rows(path)
        inserted = 0
        for row in rows:
            location = (row.get("location") or row.get("region") or "Inconnu")
            weather = models.WeatherData(
                location=str(location),
                latitude=float(row.get("latitude", 0.0) or 0.0),
                longitude=float(row.get("longitude", 0.0) or 0.0),
                temperature=float(row.get("temperature", 0.0) or 0.0),
                humidity=float(row.get("humidity", 0.0) or 0.0),
                precipitation=float(row.get("precipitation", 0.0) or 0.0),
                soil_moisture=float(row.get("soil_moisture", 0.0) or 0.0),
                timestamp=datetime.datetime.utcnow(),
            )
            db.add(weather)

            sensor = models.SensorReading(
                user_id=user.id,
                sensor_type=str(row.get("sensor_type") or "temperature"),
                value=float(row.get("sensor_value", row.get("value", 0.0)) or 0.0),
                unit=str(row.get("sensor_unit") or "°C"),
                location=str(location),
                timestamp=datetime.datetime.utcnow(),
            )
            db.add(sensor)

            yield_record = models.YieldPrediction(
                user_id=user.id,
                crop_id=crop.id,
                predicted_yield=float(row.get("predicted_yield", 0.0) or 0.0),
                actual_yield=float(row.get("actual_yield", 0.0) or 0.0),
                factors_used=str(row),
                prediction_date=datetime.datetime.utcnow(),
            )
            db.add(yield_record)
            inserted += 1

        db.commit()
        print(f"{inserted} lignes importées depuis {path}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_training_csv.py <fichier.csv|fichier.xlsx>")
        raise SystemExit(1)
    import_data(sys.argv[1])
