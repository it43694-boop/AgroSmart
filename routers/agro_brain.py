"""AgroBrain API routes - AI predictions for agriculture"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import datetime

from database import get_db
import models
import auth
from services.agro_brain_service import AgroBrainService

router = APIRouter(prefix="/api/agro-brain", tags=["agro-brain"])

# Initialize AgroBrain service
agro_brain_service = AgroBrainService()


@router.post("/predict/")
def predict_agriculture(
    data: Dict,
    db: Session = Depends(get_db),
    request: Optional[object] = None,
):
    """AI prediction for agriculture based on soil, season, and region"""
    try:
        region = data.get("region", "Sikasso")
        soil_type = data.get("soil_type", "argileux")
        season = data.get("season", "hivernage")
        crop_type = data.get("crop_type", "maïs")
        temperature = data.get("temperature")
        rainfall = data.get("rainfall")
        
        # Use AgroBrain service for crop recommendation
        recommendation = agro_brain_service.recommend_crop(
            region=region,
            soil_type=soil_type,
            season=season,
            temperature=temperature,
            rainfall=rainfall
        )
        
        # Predict yield if crop type is specified
        if crop_type:
            fertilizer_amount = data.get("fertilizer_amount", 100)
            yield_prediction = agro_brain_service.predict_yield(
                crop=crop_type,
                region=region,
                soil_type=soil_type,
                rainfall=rainfall or 500,
                fertilizer_amount=fertilizer_amount,
                temperature=temperature
            )
        else:
            yield_prediction = None
        
        predictions = {
            "region": region,
            "soil_type": soil_type,
            "season": season,
            "crop_type": crop_type,
            "recommendation": {
                "crop_name": recommendation.crop_name,
                "confidence_score": recommendation.confidence_score,
                "expected_yield": recommendation.expected_yield,
                "water_requirement": recommendation.water_requirement,
                "fertilizer_needs": recommendation.fertilizer_needs,
                "risk_factors": recommendation.risk_factors,
                "adaptation_tips": recommendation.adaptation_tips
            },
            "yield_prediction": yield_prediction,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        return predictions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur prédiction: {str(e)}")


@router.get("/recommendations/{user_id}/")
def get_recommendations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get AI recommendations for a user"""
    if current_user.id != user_id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    try:
        # Get user's region and soil type from profile
        region = current_user.region or "Sikasso"
        soil_type = data.get("soil_type", "argileux") if hasattr(current_user, 'soil_type') else "argileux"
        season = "hivernage"  # Default to rainy season
        
        # Get crop recommendation
        recommendation = agro_brain_service.recommend_crop(region, soil_type, season)
        
        recommendations = {
            "user_id": user_id,
            "crop_recommendation": {
                "crop_name": recommendation.crop_name,
                "confidence_score": recommendation.confidence_score,
                "expected_yield": recommendation.expected_yield,
                "water_requirement": recommendation.water_requirement,
                "fertilizer_needs": recommendation.fertilizer_needs,
                "risk_factors": recommendation.risk_factors,
                "adaptation_tips": recommendation.adaptation_tips
            },
            "fertilizer_recommendation": {
                "type": "NPK 15-15-15",
                "amount_kg_per_ha": recommendation.fertilizer_needs.get("azote", 150),
                "application_schedule": ["2024-06-15", "2024-07-15", "2024-08-15"]
            },
            "irrigation_recommendation": {
                "frequency": "3 fois par semaine",
                "duration_hours": 2,
                "water_amount_liters": recommendation.water_requirement * 10
            },
            "pest_control_recommendation": {
                "monitoring_frequency": "hebdomadaire",
                "treatment_threshold": "5% infestation",
                "recommended_pesticides": ["Biopesticide A", "Biopesticide B"]
            },
            "crop_rotation_suggestion": "maïs → haricot → sorgho",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recommandations: {str(e)}")


@router.post("/analyze-soil/")
def analyze_soil(
    soil_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Analyze soil data and provide recommendations"""
    try:
        ph = soil_data.get("ph", 6.5)
        nitrogen = soil_data.get("nitrogen", 50)  # mg/kg
        phosphorus = soil_data.get("phosphorus", 30)  # mg/kg
        potassium = soil_data.get("potassium", 40)  # mg/kg
        region = soil_data.get("region", "Sikasso")
        
        analysis = {
            "ph": ph,
            "ph_status": "optimal" if 6.0 <= ph <= 7.0 else "acide" if ph < 6.0 else "alcalin",
            "nitrogen": nitrogen,
            "nitrogen_status": "suffisant" if nitrogen >= 40 else "déficient",
            "phosphorus": phosphorus,
            "phosphorus_status": "suffisant" if phosphorus >= 25 else "déficient",
            "potassium": potassium,
            "potassium_status": "suffisant" if potassium >= 35 else "déficient",
            "overall_health": "bon" if all([6.0 <= ph <= 7.0, nitrogen >= 40, phosphorus >= 25, potassium >= 35]) else "amélioration nécessaire",
            "recommendations": [],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        if ph < 6.0:
            analysis["recommendations"].append("Ajouter chaux pour augmenter le pH")
        elif ph > 7.0:
            analysis["recommendations"].append("Ajouter soufre pour diminuer le pH")
        
        if nitrogen < 40:
            analysis["recommendations"].append("Ajouter engrais azoté")
        if phosphorus < 25:
            analysis["recommendations"].append("Ajouter engrais phosphaté")
        if potassium < 35:
            analysis["recommendations"].append("Ajouter engrais potassique")
        
        # Get crop recommendation based on soil analysis
        soil_type = "argileux" if ph > 6.5 else "sableux" if ph < 6.0 else "limoneux"
        crop_rec = agro_brain_service.recommend_crop(region, soil_type, "hivernage")
        analysis["recommended_crops"] = [crop_rec.crop_name]
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur analyse sol: {str(e)}")


@router.post("/optimize-resources/")
def optimize_resources(
    farm_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Optimize resource usage for a farm"""
    try:
        optimization = agro_brain_service.optimize_resources(farm_data)
        return optimization
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur optimisation: {str(e)}")


@router.post("/detect-risks/")
def detect_risks(
    risk_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Detect agricultural risks in real-time"""
    try:
        region = risk_data.get("region", "Sikasso")
        crop = risk_data.get("crop", "maïs")
        current_conditions = risk_data.get("conditions", {})
        
        risks = agro_brain_service.detect_risks(region, crop, current_conditions)
        return {
            "region": region,
            "crop": crop,
            "risks": risks,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur détection risques: {str(e)}")
