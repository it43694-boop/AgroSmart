import json
from typing import List, Tuple

import numpy as np

from database import SessionLocal
import models


def _load_real_training_rows(limit: int = 500) -> List[dict]:
    db = SessionLocal()
    try:
        rows = []
        weather_rows = db.query(models.WeatherData).order_by(models.WeatherData.timestamp.desc()).limit(limit).all()
        for item in weather_rows:
            rows.append({
                "source": "weather",
                "temperature": item.temperature,
                "rainfall": item.precipitation,
                "humidity": item.humidity,
                "soil_moisture": item.soil_moisture,
                "location": item.location,
                "timestamp": item.timestamp,
            })

        sensor_rows = db.query(models.SensorReading).order_by(models.SensorReading.timestamp.desc()).limit(limit).all()
        for item in sensor_rows:
            rows.append({
                "source": "sensor",
                "temperature": item.value if item.sensor_type in {"temperature"} else None,
                "rainfall": None,
                "humidity": item.value if item.sensor_type in {"humidity"} else None,
                "soil_moisture": item.value if item.sensor_type in {"soil_moisture"} else None,
                "location": item.location,
                "timestamp": item.timestamp,
            })

        yield_rows = db.query(models.YieldPrediction).order_by(models.YieldPrediction.prediction_date.desc()).limit(limit).all()
        for item in yield_rows:
            payload = {}
            try:
                payload = json.loads(item.factors_used or "{}") if item.factors_used else {}
            except Exception:
                payload = {}

            weather_data = payload.get("weather_data") or {}
            crop_data = payload.get("crop_data") or {}
            rows.append({
                "source": "yield",
                "temperature": weather_data.get("temperature") if isinstance(weather_data, dict) else None,
                "rainfall": weather_data.get("precipitation") if isinstance(weather_data, dict) else None,
                "humidity": weather_data.get("humidity") if isinstance(weather_data, dict) else None,
                "soil_moisture": crop_data.get("soil_moisture") if isinstance(crop_data, dict) else None,
                "location": crop_data.get("region") if isinstance(crop_data, dict) else None,
                "timestamp": item.prediction_date,
                "target_yield": item.actual_yield if item.actual_yield is not None else item.predicted_yield,
            })

        return rows
    finally:
        db.close()


def build_real_training_dataset(limit: int = 500) -> Tuple[np.ndarray, np.ndarray]:
    rows = _load_real_training_rows(limit=limit)
    if not rows:
        raise ValueError("Aucune donnée réelle disponible pour l'entraînement")

    features = []
    targets = []

    for row in rows:
        temp = row.get("temperature")
        rain = row.get("rainfall")
        humidity = row.get("humidity")
        soil = row.get("soil_moisture")
        target = row.get("target_yield")

        if temp is None and humidity is None and soil is None and target is None:
            continue

        features.append([
            0.0 if temp is None else float(temp),
            0.0 if rain is None else float(rain),
            0.0 if humidity is None else float(humidity),
            0.0 if soil is None else float(soil),
        ])

        if target is not None:
            targets.append(float(target))
        elif temp is not None and soil is not None:
            targets.append(float(temp + soil * 10))
        elif temp is not None:
            targets.append(float(temp))
        else:
            targets.append(float(soil or 0.0))

    if len(features) < 1:
        raise ValueError("Trop peu de données réelles disponibles")

    X = np.array(features, dtype=float)
    y = np.array(targets, dtype=float)
    return X, y
