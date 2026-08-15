"""
User Service - Logique métier pour les utilisateurs
"""
import datetime
from sqlalchemy.orm import Session
from typing import Optional
import models
import schemas
from mali_ml import get_recommendation, predict_revenue
from mali_data import get_region_by_coords, get_cercle_by_coords, get_region_coords
from ml_model import predict_action
from services.weather_service import fetch_weather_data
from services.market_service import fetch_markets


def compute_credit_score(user: models.User) -> schemas.CreditScoreResponse:
    """Calcule le score de crédit basé sur les enregistrements financiers"""
    total_revenue = sum(record.revenue for record in user.finance_records)
    total_cost = sum(record.cost for record in user.finance_records)
    net_income = total_revenue - total_cost
    record_count = len(user.finance_records)
    ratio = (net_income / total_revenue) if total_revenue > 0 else -1.0
    score = 300
    if ratio > 0.5:
        score = 750
    elif ratio > 0.2:
        score = 650
    elif ratio >= 0:
        score = 550
    else:
        score = 420
    score += min(100, record_count * 10)
    score = min(850, max(300, score))
    if score >= 720:
        rating = "Excellent"
    elif score >= 650:
        rating = "Bon"
    elif score >= 580:
        rating = "Moyen"
    else:
        rating = "Faible"
    return schemas.CreditScoreResponse(
        score=score,
        rating=rating,
        details=[
            f"Revenu total: {total_revenue:.2f} XOF",
            f"Coût total: {total_cost:.2f} XOF",
            f"Revenu net: {net_income:.2f} XOF",
            f"Nombre d'enregistrements financiers: {record_count}",
        ],
    )


def estimate_gains(user: models.User, lat: float, lon: float) -> dict:
    """Estimation des gains basée sur ML Mali"""
    try:
        markets = fetch_markets(lat=lat, lon=lon)
    except:
        markets = schemas.MarketResponse(crop_prices={"maïs": 220.0}, market_trend="Stable", source="Fallback")

    total_surface = user.total_surface or 0.0
    crops = user.crops or []
    estimated_revenue = 0.0
    details = []

    for crop in crops:
        crop_name = crop.name.lower()

        try:
            # Use Mali ML for revenue prediction
            revenue = predict_revenue(
                crop_name=crop_name,
                surface_ha=crop.surface,
                lat=lat,
                lon=lon,
                month=datetime.datetime.now().month
            )
            estimated_revenue += revenue
            details.append(f"{crop.name}: {crop.surface:.1f} ha → {revenue:.0f} XOF (ML-prédit)")
        except:
            # Fallback to basic calculation
            price_per_tonne = markets.crop_prices.get(crop_name, 220.0)
            yield_per_ha = 2.0
            revenue = crop.surface * yield_per_ha * price_per_tonne
            estimated_revenue += revenue
            details.append(f"{crop.name}: {crop.surface:.1f} ha x {yield_per_ha} t/ha x {price_per_tonne:.0f} XOF/t = {revenue:.0f} XOF")

    # Historical trend adjustment from market data
    trend_multiplier = 1.0
    if markets.market_trend == "Hausse":
        trend_multiplier = 1.1
    elif markets.market_trend == "Baisse":
        trend_multiplier = 0.9

    estimated_revenue *= trend_multiplier

    # Cost estimation (simplified Mali-aware values in XOF)
    cost_per_ha = 150000.0  # XOF per hectare base
    try:
        region = get_region_by_coords(lat, lon)
        if region in ["Tombouctou", "Gao"]:
            cost_per_ha = 180000.0  # Higher costs in arid regions
        elif region in ["Koulikoro", "Ségou"]:
            cost_per_ha = 140000.0  # Lower costs in better-irrigated regions
    except:
        pass

    estimated_cost = total_surface * cost_per_ha
    net_gain = estimated_revenue - estimated_cost

    return {
        "estimated_revenue": estimated_revenue,
        "estimated_cost": estimated_cost,
        "net_gain": net_gain,
        "details": details,
        "market_trend": markets.market_trend,
    }


def _resolve_user_coords(user: models.User, lat: float = 0.0, lon: float = 0.0) -> tuple[float, float]:
    """Returns the best available coordinates for a user.

    Priority:
    1. Explicit request coordinates
    2. First field coordinates if the user has geolocated fields
    3. User region/cercle coordinates
    4. Default Mali fallback coordinates
    """
    if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
        return float(lat), float(lon)

    if getattr(user, "fields", None):
        for field in user.fields:
            if getattr(field, "latitude", None) is not None and getattr(field, "longitude", None) is not None:
                return float(field.latitude), float(field.longitude)

    if getattr(user, "region", None):
        coords = get_region_coords(user.region)
        if coords:
            return coords

    return 12.6392, -8.0029


def get_advisor_recommendation(user: Optional[models.User], lat: float = 0.0, lon: float = 0.0) -> schemas.AdvisorResponse:
    """Génère des recommandations d'advisor pour l'utilisateur avec fallback robuste."""
    if user is None:
        class _AnonymousUser:
            def __init__(self):
                self.crops = []
                self.region = None
                self.total_surface = 0.0

        user = _AnonymousUser()

    lat, lon = _resolve_user_coords(user, lat, lon)

    try:
        weather = fetch_weather_data(lat=lat, lon=lon)
    except Exception:
        weather = {"temperature_celsius": 25.0, "rainfall": 5.0, "soil_moisture": 0.5}

    if not isinstance(weather, dict):
        weather = {"temperature_celsius": 25.0, "rainfall": 5.0, "soil_moisture": 0.5}

    days_since_planting = 0
    if user.crops:
        planting_dates = [crop.planting_date for crop in user.crops if crop.planting_date]
        if planting_dates:
            earliest = min(planting_dates)
            days_since_planting = max(0, (datetime.datetime.utcnow() - earliest).days)

    # Get Mali-specific recommendation using ML
    temp = weather.get("temperature", weather.get("temperature_celsius", 25.0))
    rain = weather.get("rainfall", 5.0)
    soil_moisture = weather.get("soil_moisture")
    if soil_moisture is None:
        soil_moisture = 0.5
    elif isinstance(soil_moisture, str):
        try:
            soil_moisture = float(soil_moisture)
        except ValueError:
            soil_moisture = 0.5

    try:
        # Use Mali ML for intelligent recommendations
        region = get_region_by_coords(lat, lon)
        cercle, region_name = get_cercle_by_coords(lat, lon)

        # Get ML-based recommendation
        ml_recommendation = get_recommendation(
            temperature=temp,
            rainfall=rain,
            soil_moisture=soil_moisture,
            days_since_planting=days_since_planting,
            lat=lat,
            lon=lon,
            current_crop=user.crops[0].name if user.crops else None
        )

        recommendation = ml_recommendation["recommendation"]
        details = [
            f"Région Mali : {region}",
            f"Cercle : {cercle}",
            f"Température : {temp:.1f} °C" if temp is not None else "Température : N/A",
            f"Pluie : {rain:.1f} mm" if rain is not None else "Pluie : N/A",
            f"Humidité du sol : {soil_moisture:.2f}" if soil_moisture is not None else "Humidité du sol : N/A",
            f"Culture recommandée : {ml_recommendation.get('suggested_crop', 'mil')}",
            f"Jours depuis plantation : {days_since_planting}"
        ]

        # Add alerts
        if ml_recommendation.get("alerts"):
            for alert in ml_recommendation["alerts"]:
                details.append(f"⚠️  {alert['level'].upper()}: {alert['message']}")

        return schemas.AdvisorResponse(recommendation=recommendation, details=details)

    except Exception as e:
        print(f"Mali ML error: {e}, falling back to generic advisor")
        # Fallback to generic advisor if ML fails
        action = predict_action(
            temperature=temp,
            rainfall=rain,
            soil_moisture=soil_moisture,
            days_since_planting=days_since_planting,
        )

        planting_advice = ""
        if temp > 20 and temp < 35 and rain > 10:
            planting_advice = "Conditions favorables pour planter."
        elif temp < 15:
            planting_advice = "Température trop basse. Attendez un réchauffement."
        elif rain < 5:
            planting_advice = "Précipitations insuffisantes. Planifiez l'irrigation."
        else:
            planting_advice = "Surveillez les conditions météorologiques."

        watering_advice = ""
        if soil_moisture < 0.3:
            watering_advice = "Arrosage urgent recommandé."
        elif soil_moisture < 0.5:
            watering_advice = "Arrosage conseillé dans les prochains jours."
        else:
            watering_advice = "Sol suffisamment humide."

        recommendation = f"{action.capitalize()}. {planting_advice} {watering_advice}"
        details = [
            f"Région : {user.region or 'Mali'}",
            f"Température : {temp:.1f} °C" if temp is not None else "Température : N/A",
            f"Pluie : {rain:.1f} mm" if rain is not None else "Pluie : N/A",
            f"Humidité du sol : {soil_moisture:.2f}" if soil_moisture is not None else "Humidité du sol : N/A",
            f"Jours depuis plantation : {days_since_planting}",
        ]
        return schemas.AdvisorResponse(recommendation=recommendation, details=details)