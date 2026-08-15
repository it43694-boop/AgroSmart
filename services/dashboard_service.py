from sqlalchemy.orm import Session
import datetime
import schemas
import models
from services.user_service import compute_credit_score
from services.user_service import get_advisor_recommendation
from services.weather_service import fetch_weather_data
from services.market_service import fetch_markets
from services.satellite_service import fetch_satellite
from services.agro_brain_service import agro_brain, MALI_SOIL_DATA
from mali_data import get_region_by_coords, get_region_coords


def _resolve_user_lat_lon(user: models.User, lat: float = 0.0, lon: float = 0.0) -> tuple[float, float]:
    """Détermine les coordonnées de l'utilisateur en priorité sur la localisation de la parcelle."""
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


def build_dashboard_response(db: Session, user_id: int, lat: float = 0.0, lon: float = 0.0) -> schemas.DashboardResponse:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("Utilisateur introuvable")

    resolved_lat, resolved_lon = _resolve_user_lat_lon(user, lat, lon)
    weather = fetch_weather_data(lat=resolved_lat, lon=resolved_lon)
    advisor = get_advisor_recommendation(user, lat=resolved_lat, lon=resolved_lon)
    credit_score = compute_credit_score(user)
    market_info = fetch_markets(lat=resolved_lat, lon=resolved_lon)
    satellite_info = fetch_satellite(lat=resolved_lat, lon=resolved_lon)

    region = get_region_by_coords(resolved_lat, resolved_lon)
    soil_type = MALI_SOIL_DATA.get(region).soil_type if region in MALI_SOIL_DATA else "sableux"
    crop_type = (user.crops[0].name if user.crops else "mil").lower()

    yield_prediction = agro_brain.predict_yield(
        crop=crop_type,
        region=region,
        soil_type=soil_type,
        rainfall=weather.get("rainfall") or 500,
        fertilizer_amount=100,
        temperature=weather.get("temperature_celsius") or 28,
    )

    price_prediction = {
        "crop_type": crop_type,
        "current_price": market_info.crop_prices.get(crop_type) if hasattr(market_info, 'crop_prices') else market_info.crop_prices.get(crop_type),
        "currency": "XOF",
        "unit": "kg",
        "market_trend": market_info.market_trend if hasattr(market_info, 'market_trend') else market_info.get('market_trend'),
        "source": market_info.source if hasattr(market_info, 'source') else market_info.get('source'),
    }

    total_revenue = sum(record.revenue for record in user.finance_records or [])
    total_cost = sum(record.cost for record in user.finance_records or [])

    return schemas.DashboardResponse(
        user=schemas.UserResponse.from_orm(user),
        weather=schemas.WeatherResponse(
            location=weather["location"],
            summary=weather.get("summary", "Données météo récupérées"),
            temperature_celsius=weather.get("temperature_celsius"),
            humidity=weather.get("humidity"),
            wind_speed=weather.get("wind_speed"),
            rainfall=weather.get("rainfall"),
            soil_moisture=weather.get("soil_moisture"),
            forecast=weather.get("forecast", []),
            alert=weather.get("alert"),
            source=weather.get("source"),
        ),
        advisor=advisor,
        total_revenue=total_revenue,
        total_cost=total_cost,
        net_income=total_revenue - total_cost,
        credit_score=credit_score,
        market_info=market_info,
        satellite_info=satellite_info,
        yield_prediction=yield_prediction,
        price_prediction=price_prediction,
    )
