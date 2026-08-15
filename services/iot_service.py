import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import logging
import json

import models

logger = logging.getLogger("iot_service")


def store_sensor_reading(user_id: int, sensor_type: str, value: float, unit: str,
                        location: Optional[str] = None, crop_id: Optional[int] = None,
                        device_id: Optional[str] = None, metadata: Optional[Dict] = None,
                        db: Session = None) -> models.SensorReading:
    """Store a sensor reading in the time-series database"""
    if db is None:
        from database import get_db
        db = next(get_db())

    metadata_json = json.dumps(metadata) if metadata else None

    reading = models.SensorReading(
        user_id=user_id,
        sensor_type=sensor_type,
        value=value,
        unit=unit,
        location=location,
        crop_id=crop_id,
        device_id=device_id,
        metadata_json=metadata_json,
        timestamp=datetime.datetime.utcnow()
    )

    db.add(reading)
    db.commit()
    db.refresh(reading)

    logger.info(f"Sensor reading stored: {sensor_type}={value}{unit} for user {user_id}")
    return reading


def get_sensor_readings(user_id: int, sensor_type: Optional[str] = None,
                       crop_id: Optional[int] = None, hours: int = 24,
                       db: Session = None) -> List[models.SensorReading]:
    """Retrieve sensor readings from the time-series database"""
    if db is None:
        from database import get_db
        db = next(get_db())

    query = db.query(models.SensorReading).filter(
        models.SensorReading.user_id == user_id,
        models.SensorReading.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    )

    if sensor_type:
        query = query.filter(models.SensorReading.sensor_type == sensor_type)
    if crop_id:
        query = query.filter(models.SensorReading.crop_id == crop_id)

    return query.order_by(models.SensorReading.timestamp.desc()).all()


def get_sensor_analytics(user_id: int, sensor_type: str, hours: int = 24,
                        db: Session = None) -> Dict[str, Any]:
    """Get analytics for sensor data"""
    readings = get_sensor_readings(user_id, sensor_type, hours=hours, db=db)

    if not readings:
        return {"count": 0, "average": 0, "min": 0, "max": 0, "trend": "stable"}

    values = [r.value for r in readings]
    timestamps = [r.timestamp for r in readings]

    # Calculate trend
    if len(values) >= 2:
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        trend = "increasing" if sum(second_half)/len(second_half) > sum(first_half)/len(first_half) else "decreasing"
    else:
        trend = "stable"

    return {
        "count": len(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "trend": trend,
        "latest_value": values[0] if values else 0,
        "latest_timestamp": timestamps[0].isoformat() if timestamps else None
    }


def _predict_maintenance(readings: List[models.SensorReading]) -> Dict[str, Any]:
    alert = None
    due_in_days = None
    action = None
    resource_optimization = {
        "irrigation": "Normal",
        "energy": "Normal",
        "water_flow": "Stable"
    }

    values_by_type = {}
    for reading in readings:
        values_by_type.setdefault(reading.sensor_type, []).append(reading.value)

    vibration = values_by_type.get("pump_vibration", [])
    battery = values_by_type.get("battery_level", [])
    water_flow = values_by_type.get("water_flow", [])
    soil_moisture = values_by_type.get("soil_moisture", [])

    if vibration and max(vibration) >= 70:
        alert = "Votre pompe va tomber en panne dans 3 jours - intervention préventive"
        due_in_days = 3
        action = "Inspecter le moteur de la pompe et remplacer les pièces usées."
        resource_optimization["energy"] = "Réduire la charge de la pompe"
        resource_optimization["water_flow"] = "Stabiliser le débit"
    elif battery and min(battery) <= 25:
        alert = "Niveau de batterie critique détecté - maintenance nécessaire"
        due_in_days = 2
        action = "Remplacer ou recharger la batterie de l’équipement IoT." 
        resource_optimization["energy"] = "Activer le mode basse consommation"
    elif water_flow and len(water_flow) >= 3 and water_flow[-1] < water_flow[-2] * 0.75:
        alert = "Débit d’eau en baisse rapide - vérifier la pompe et les canalisations"
        due_in_days = 4
        action = "Vérifier les filtres et la pompe pour éviter une panne."
        resource_optimization["water_flow"] = "Optimiser la distribution d’eau"
    elif soil_moisture and min(soil_moisture) < 20:
        alert = "Humidité du sol faible - optimiser l’irrigation"
        due_in_days = 5
        action = "Ajuster l’irrigation pour maintenir un niveau de sol adéquat."
        resource_optimization["irrigation"] = "Augmenter l’irrigation modérément"
    else:
        alert = "Aucun risque critique détecté pour le moment."
        due_in_days = None
        action = "Surveillance continue recommandée."

    return {
        "predicted_alert": alert,
        "maintenance_due_in_days": due_in_days,
        "recommended_action": action,
        "resource_optimization": resource_optimization
    }


def record_sensor_reading(db: Session, data: Dict[str, Any]) -> models.SensorReading:
    timestamp = data.get("timestamp")
    if timestamp:
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp)
        except Exception:
            timestamp = datetime.datetime.utcnow()
    else:
        timestamp = datetime.datetime.utcnow()

    sensor = models.SensorReading(
        user_id=data["user_id"],
        sensor_type=data["sensor_type"],
        value=data["value"],
        unit=data["unit"],
        location=data.get("location"),
        timestamp=timestamp
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


def get_latest_sensor_readings(db: Session, user_id: int, limit: int = 25) -> List[models.SensorReading]:
    return (
        db.query(models.SensorReading)
        .filter(models.SensorReading.user_id == user_id)
        .order_by(models.SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_iot_dashboard(db: Session, user_id: int) -> Dict[str, Any]:
    readings = get_latest_sensor_readings(db, user_id, limit=30)
    if not readings:
        return {
            "user_id": user_id,
            "latest_readings": [],
            "predicted_alert": "Aucune donnée de capteur disponible.",
            "maintenance_due_in_days": None,
            "recommended_action": "Aucun capteur actif.",
            "resource_optimization": {
                "irrigation": "N/A",
                "energy": "N/A",
                "water_flow": "N/A"
            },
            "status": "no_data"
        }

    prediction = _predict_maintenance(readings)
    return {
        "user_id": user_id,
        "latest_readings": readings,
        "status": "ok",
        **prediction
    }
