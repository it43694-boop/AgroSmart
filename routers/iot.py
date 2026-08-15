"""IoT API routes - Sensor data and dashboard"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
import datetime
import random

from database import get_db
import models
import auth

router = APIRouter(prefix="/api/iot", tags=["iot"])


@router.get("/dashboard/{user_id}/")
def get_iot_dashboard(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get IoT dashboard data for a user"""
    if current_user.id != user_id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    # Mock dashboard data (en prod: vraies données IoT)
    return {
        "user_id": user_id,
        "status": "ok",
        "maintenance_due_in_days": 15,
        "recommended_action": "Vérifier le système d'irrigation",
        "resource_optimization": {
            "water_usage": "85% efficient",
            "energy_usage": "78% efficient",
            "fertilizer_usage": "optimal"
        },
        "predicted_alert": "Aucune alerte prédictive",
        "last_updated": datetime.datetime.utcnow().isoformat()
    }


@router.get("/sensors/{user_id}/")
def get_sensor_readings(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get sensor readings for a user"""
    if current_user.id != user_id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    # Mock sensor readings (en prod: vraies données depuis la DB)
    readings = []
    sensor_types = ["Température", "Humidité", "Humidité sol", "pH", "Luminosité"]
    units = ["°C", "%", "%", "pH", "lux"]
    locations = ["Champ 1", "Champ 2", "Serre", "Pépinière", "Stockage"]
    
    for i in range(10):
        readings.append({
            "id": i + 1,
            "sensor_type": sensor_types[i % len(sensor_types)],
            "value": round(random.uniform(20, 35), 2) if i % len(sensor_types) == 0 else
                    round(random.uniform(40, 90), 2) if i % len(sensor_types) in [1, 2] else
                    round(random.uniform(6.0, 7.5), 2) if i % len(sensor_types) == 3 else
                    round(random.uniform(500, 1000), 2),
            "unit": units[i % len(units)],
            "location": locations[i % len(locations)],
            "timestamp": (datetime.datetime.utcnow() - datetime.timedelta(minutes=i*5)).isoformat()
        })
    
    return readings


@router.post("/sensors/{user_id}/")
def add_sensor_reading(user_id: int, reading: Dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Add a new sensor reading"""
    if current_user.id != user_id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    # En prod: sauvegarder dans la base de données
    return {
        "status": "success",
        "message": "Lecture de capteur enregistrée",
        "reading": {
            "sensor_type": reading.get("sensor_type"),
            "value": reading.get("value"),
            "unit": reading.get("unit"),
            "location": reading.get("location"),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    }


@router.get("/farms/{farm_id}/status/")
def get_farm_status(farm_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get IoT status for a specific farm"""
    # Mock farm status
    return {
        "farm_id": farm_id,
        "sensors_active": 4,
        "sensors_total": 5,
        "battery_level": 87,
        "last_sync": "2 minutes ago",
        "data_freshness": "green",
        "alerts": [
            {"level": "warning", "message": "Température au-dessus de 35°C"}
        ]
    }
