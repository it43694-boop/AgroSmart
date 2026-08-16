"""ML & MLOps API routes for AgroSmart."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import auth

router = APIRouter(prefix="/api/ml", tags=["ml"])

# Lazy singleton: the heavy ML service (imports tensorflow, etc.) is only
# instantiated on first actual use, not at module import / app startup time.
# This avoids blocking the server's port binding on low-CPU instances.
_advanced_ml_service = None
_ml_service_load_attempted = False
_ml_service_load_error = None


def _get_ml_service():
    """Return the AdvancedMLService singleton, loading it lazily on first call."""
    global _advanced_ml_service, _ml_service_load_attempted, _ml_service_load_error

    if not _ml_service_load_attempted:
        _ml_service_load_attempted = True
        try:
            from services.ml_service import AdvancedMLService
            _advanced_ml_service = AdvancedMLService()
        except Exception as exc:
            _advanced_ml_service = None
            _ml_service_load_error = str(exc)
            print(f"ML service unavailable: {exc}")

    return _advanced_ml_service


def _ml_service_available() -> bool:
    return _get_ml_service() is not None


@router.post("/predict-yield")
def predict_yield(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Prédire le rendement des cultures avec intervalle de confiance"""
    advanced_ml_service = _get_ml_service()
    if not advanced_ml_service:
        raise HTTPException(status_code=503, detail="Service ML non disponible")

    try:
        crop_data = payload.get("crop_data", {
            "age_days": payload.get("age_days", 30),
            "planted_area": payload.get("planted_area", 1.0),
        })
        weather_data = payload.get("weather_data", {
            "temperature": payload.get("temperature", 25),
            "humidity": payload.get("humidity", 60),
            "precipitation": payload.get("precipitation", 5),
        })
        sensor_data = payload.get("sensor_data", payload.get("sensors", []))

        result = advanced_ml_service.predict_yield(
            crop_data=crop_data,
            weather_data=weather_data,
            sensor_data=sensor_data,
        )

        try:
            advanced_ml_service.record_yield_prediction(db, current_user.id, payload, result)
        except Exception:
            pass

        return result

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur prédiction rendement: {str(exc)}")


@router.post("/predict-price")
def predict_price(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Prédire le prix des cultures pour les 7 prochains jours"""
    advanced_ml_service = _get_ml_service()
    if not advanced_ml_service:
        raise HTTPException(status_code=503, detail="Service ML non disponible")

    try:
        crop_type = payload.get("crop_type", "mil")
        market_location = payload.get("market_location", payload.get("region", "Mali"))
        quality_grade = payload.get("quality_grade", "A")

        result = advanced_ml_service.predict_price(
            crop_type=crop_type,
            market_location=market_location,
            quality_grade=quality_grade,
        )
        return result

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur prédiction prix: {str(exc)}")


@router.post("/assess-weather-risks")
def assess_weather_risks(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Évaluer les risques météorologiques pour les cultures"""
    advanced_ml_service = _get_ml_service()
    if not advanced_ml_service:
        raise HTTPException(status_code=503, detail="Service ML non disponible")

    try:
        crop_data = payload.get("crop_data", {
            "crop_type": payload.get("crop_type", "mil"),
            "region": payload.get("region", "Mali"),
            "age_days": payload.get("age_days", 30),
            "soil_type": payload.get("soil_type", "fertile"),
        })
        weather_forecast = payload.get("weather_data", {})

        result = advanced_ml_service.assess_weather_risks(
            crop_data=crop_data,
            weather_forecast=weather_forecast,
        )
        return result

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur évaluation risques: {str(exc)}")


@router.post("/recommendations")
def get_recommendations(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Générer des recommandations agronomiques"""
    advanced_ml_service = _get_ml_service()
    if not advanced_ml_service:
        raise HTTPException(status_code=503, detail="Service ML non disponible")

    try:
        crop_data = payload.get("crop_data", {
            "crop_type": payload.get("crop_type", "mil"),
            "region": payload.get("region", "Mali"),
            "age_days": payload.get("age_days", 30),
            "soil_type": payload.get("soil_type", "fertile"),
        })
        sensor_data = payload.get("sensor_data")
        if sensor_data is None:
            soil_data = payload.get("soil_data")
            if isinstance(soil_data, dict):
                sensor_data = [soil_data]
            elif isinstance(soil_data, list):
                sensor_data = soil_data
            else:
                sensor_data = []

        weather_data = payload.get("weather_data", {})

        result = advanced_ml_service.generate_agronomic_recommendations(
            crop_data=crop_data,
            sensor_data=sensor_data,
            weather_data=weather_data,
        )

        try:
            advanced_ml_service.record_ai_recommendations(db, current_user.id, payload, result)
        except Exception:
            pass

        return {"recommendations": result}

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur recommandations: {str(exc)}")


@router.get("/model-status")
def model_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Expose the current active model version and basic drift metrics."""
    if current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès restreint aux administrateurs")

    advanced_ml_service = _get_ml_service()
    return {
        "active_model_versions": {
            "yield": advanced_ml_service.model_versions.get("yield") if advanced_ml_service else None,
            "price": advanced_ml_service.model_versions.get("price") if advanced_ml_service else None,
            "crop_recommendation": advanced_ml_service.model_versions.get("crop_recommendation") if advanced_ml_service else None,
        },
        "drift_metrics": getattr(advanced_ml_service, "_drift_metrics", {}) if advanced_ml_service else {},
    }


@router.post("/retrain")
def retrain_models(
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrain the ML models using real DB-backed data when available."""
    if current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès restreint aux administrateurs")

    advanced_ml_service = _get_ml_service()
    if not advanced_ml_service:
        raise HTTPException(status_code=503, detail="Service ML non disponible")

    try:
        advanced_ml_service.train_yield_prediction_model()
        advanced_ml_service.train_price_prediction_model()
        advanced_ml_service.train_crop_recommendation_model()
        return {"status": "retrained", "source": "real_data_if_available"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur entraînement: {str(exc)}")


@router.post("/promote-model")
def promote_model(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Promote a registered model version from staging to ready and activate it."""
    if current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès restreint aux administrateurs")

    model_name = payload.get("model_name") or payload.get("name")
    version = payload.get("version")
    if not model_name or not version:
        raise HTTPException(status_code=400, detail="model_name et version sont requis")

    promoted = model_registry.promote_model(model_name, version)
    if promoted is None:
        raise HTTPException(status_code=404, detail="Version de modèle introuvable")

    return {
        "model_name": model_name,
        "version": version,
        "status": promoted.get("status"),
        "active": model_registry.get_active_model_version(model_name) == version,
    }


@router.get("/audit")
def ml_audit_history(
    kind: str = "all",
    limit: int = 50,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Récupère l'historique MLOps des prédictions et recommandations."""
    if user_id is not None and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès restreint aux administrateurs")

    target_user_id = user_id if user_id is not None else current_user.id
    response = {}

    if kind in ("all", "yield"):
        yield_records = db.query(models.YieldPrediction)
        yield_records = yield_records.filter(models.YieldPrediction.user_id == target_user_id)
        yield_records = yield_records.order_by(models.YieldPrediction.prediction_date.desc())
        yield_records = yield_records.limit(limit).all()
        response["yield_predictions"] = [
            {
                "id": rec.id,
                "crop_id": rec.crop_id,
                "predicted_yield": rec.predicted_yield,
                "unit": rec.yield_unit,
                "confidence_interval_low": rec.confidence_interval_low,
                "confidence_interval_high": rec.confidence_interval_high,
                "prediction_date": rec.prediction_date.isoformat() if rec.prediction_date else None,
                "actual_yield": rec.actual_yield,
                "accuracy_score": rec.accuracy_score,
                "factors_used": rec.factors_used,
                "ai_model_version": rec.ai_model_version,
            }
            for rec in yield_records
        ]

    if kind in ("all", "recommendation"):
        rec_records = db.query(models.AIRecommendation)
        rec_records = rec_records.filter(models.AIRecommendation.user_id == target_user_id)
        rec_records = rec_records.order_by(models.AIRecommendation.created_at.desc())
        rec_records = rec_records.limit(limit).all()
        response["ai_recommendations"] = [
            {
                "id": rec.id,
                "crop_id": rec.crop_id,
                "recommendation_type": rec.recommendation_type,
                "title": rec.title,
                "description": rec.description,
                "priority_level": rec.priority_level,
                "confidence_score": rec.confidence_score,
                "expected_impact": rec.expected_impact,
                "weather_factors": rec.weather_factors,
                "sensor_data": rec.sensor_data,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
                "ai_model_version": rec.ai_model_version,
            }
            for rec in rec_records
        ]

    if not response:
        raise HTTPException(status_code=400, detail="Paramètre 'kind' invalide. Utilisez 'all', 'yield' ou 'recommendation'.")

    return response