import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from security_service import require_user_view_access
from services.dashboard_service import build_dashboard_response
from services.user_service import compute_credit_score, get_advisor_recommendation
from services.weather_service import fetch_weather_data
from services.market_service import fetch_markets
from services.market_service import generate_price_evolution
from services.satellite_service import fetch_satellite
from utils import get_user_or_404
from mali_data import CROP_REQUIREMENTS

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/credit-score/{user_id}", response_model=schemas.CreditScoreResponse)
def get_credit_score(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    effective_user_id = user_id if current_user.effective_role == "admin" or user_id == current_user.id else current_user.id
    user = get_user_or_404(db, effective_user_id)
    require_user_view_access(current_user, user)
    return compute_credit_score(user)


@router.get("/markets/", response_model=schemas.MarketResponse)
def get_markets(lat: float = 0.0, lon: float = 0.0):
    return fetch_markets(lat=lat, lon=lon)


@router.get('/markets/evolution/')
def get_market_evolution(days: int = 30, lat: float = 0.0, lon: float = 0.0):
    """Retourne l'évolution des prix pour les cultures (derniers `days` jours)."""
    market = fetch_markets(lat=lat, lon=lon)
    current_prices = getattr(market, 'crop_prices', {}) if hasattr(market, '__dict__') else market.get('crop_prices', {})
    # si current_prices est un pydantic model, il sera dict-like
    if not current_prices:
        return { 'evolution': {} }
    evolution = generate_price_evolution(current_prices, days=days)
    return { 'evolution': evolution }


@router.get("/satellite/", response_model=schemas.SatelliteResponse)
def get_satellite(lat: float = 0.0, lon: float = 0.0):
    return fetch_satellite(lat=lat, lon=lon)


@router.post("/virtualfarm/field", response_model=schemas.FieldResponse)
def create_virtual_farm_field(field_data: schemas.FieldCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    field_kwargs = field_data.dict(exclude_none=True)
    field = models.Field(**field_kwargs, owner_id=current_user.id)
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/virtualfarm/field", response_model=schemas.FieldResponse)
def get_virtual_farm_field(field_id: Optional[int] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if field_id is not None:
        field = db.query(models.Field).filter(models.Field.id == field_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Parcelle introuvable")
        if field.owner_id != current_user.id and current_user.effective_role != "admin":
            raise HTTPException(status_code=403, detail="Accès refusé")
        return field

    field = db.query(models.Field).filter(models.Field.owner_id == current_user.id).order_by(models.Field.id).first()
    if field:
        return field

    return schemas.FieldResponse(
        id=0,
        name="Parcelle AgroSmart - Ferme de démonstration",
        latitude=12.6392,
        longitude=-8.0029,
        area_ha=3.4,
        crop_rotation="Mil, Niébé, Arachide",
        soil_type="Sable limoneux",
        irrigation_system="Goutte-à-goutte local",
        satellite_texture=None,
        boundary_points=[
            {"lat": 12.6388, "lon": -8.0035},
            {"lat": 12.6398, "lon": -8.0035},
            {"lat": 12.6398, "lon": -8.0023},
            {"lat": 12.6388, "lon": -8.0023}
        ],
        notes="Visualisation virtuelle pour le pilotage des parcelles.",
        owner_id=current_user.id,
    )


@router.get("/virtualfarm/fields", response_model=List[schemas.FieldResponse])
def list_virtual_farm_fields(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    fields = db.query(models.Field).filter(models.Field.owner_id == current_user.id).order_by(models.Field.id).all()
    return fields


@router.patch("/virtualfarm/field/{field_id}", response_model=schemas.FieldResponse)
def update_virtual_farm_field(field_id: int, field_data: schemas.FieldUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    field = db.query(models.Field).filter(models.Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Parcelle introuvable")
    if field.owner_id != current_user.id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")

    update_data = field_data.dict(exclude_none=True)
    for key, value in update_data.items():
        setattr(field, key, value)

    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/virtualfarm/field/{field_id}")
def delete_virtual_farm_field(field_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    field = db.query(models.Field).filter(models.Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Parcelle introuvable")
    if field.owner_id != current_user.id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")

    db.delete(field)
    db.commit()
    return {"detail": "Parcelle supprimée"}


@router.get("/weather/", response_model=schemas.WeatherResponse)
def get_weather(lat: float, lon: float):
    data = fetch_weather_data(lat=lat, lon=lon)
    return schemas.WeatherResponse(
        location=data["location"],
        summary=data.get("summary", "Données météo récupérées"),
        temperature_celsius=data.get("temperature_celsius"),
        humidity=data.get("humidity"),
        wind_speed=data.get("wind_speed"),
        rainfall=data.get("rainfall"),
        soil_moisture=data.get("soil_moisture"),
        forecast=data.get("forecast", []),
        alert=data.get("alert"),
        source=data.get("source"),
    )


@router.get("/advisor/{user_id}", response_model=schemas.AdvisorResponse)
def get_advisor(user_id: int, lat: float = 0.0, lon: float = 0.0, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    effective_user_id = user_id if current_user.effective_role == "admin" or user_id == current_user.id else current_user.id
    user = get_user_or_404(db, effective_user_id)
    require_user_view_access(current_user, user)
    return get_advisor_recommendation(user, lat=lat, lon=lon)


@router.get("/assistant/summary", response_model=dict)
def get_assistant_summary(lat: float = 0.0, lon: float = 0.0, db: Session = Depends(get_db), current_user: Optional[models.User] = Depends(auth.get_current_user_optional)):
    advisor_result = get_advisor_recommendation(current_user, lat=lat, lon=lon)
    return {
        "status": "ok",
        "recommendation": advisor_result.recommendation,
        "details": advisor_result.details,
    }


@router.get("/dashboard/{user_id}", response_model=schemas.DashboardResponse)
def get_dashboard(user_id: int, lat: float = 0.0, lon: float = 0.0, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    effective_user_id = user_id if current_user.effective_role == "admin" or user_id == current_user.id else current_user.id
    user = get_user_or_404(db, effective_user_id)
    require_user_view_access(current_user, user)
    try:
        return build_dashboard_response(db, effective_user_id, lat=lat, lon=lon)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/dashboard/{user_id}", response_model=schemas.DashboardResponse)
def get_dashboard_alias(user_id: int, lat: float = 0.0, lon: float = 0.0, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return get_dashboard(user_id=user_id, lat=lat, lon=lon, db=db, current_user=current_user)


def _format_relative_date(event_date: datetime.datetime, reference: datetime.datetime) -> str:
    delta = event_date.date() - reference.date()
    if delta.days == 0:
        return "Aujourd'hui"
    if delta.days == 1:
        return 'Demain'
    if delta.days > 0:
        return f'Dans {delta.days}j'
    if delta.days == -1:
        return 'Hier'
    return f'Il y a {abs(delta.days)}j'


def _build_crop_calendar_events(crop: models.Crop, now: datetime.datetime) -> list:
    events = []
    crop_name = crop.name or 'culture'
    crop_key = crop_name.strip().lower()
    req = CROP_REQUIREMENTS.get(crop_key)
    if not req:
        return events

    planting_date = crop.planting_date
    days_to_mature = req.get('days_to_mature', 90)
    if planting_date:
        age_days = max(0, (now - planting_date).days)
        harvest_date = planting_date + datetime.timedelta(days=days_to_mature)

        if age_days <= 14:
            events.append({
                'date': planting_date.isoformat(),
                'title': f'Semis {crop_name}',
                'description': f'Planté le {planting_date.date().isoformat()} ({age_days} jours).',
                'type': 'planting',
                'relative': _format_relative_date(planting_date, now)
            })

        fertilizer_date = planting_date + datetime.timedelta(days=21)
        if fertilizer_date >= now - datetime.timedelta(days=7):
            events.append({
                'date': fertilizer_date.isoformat(),
                'title': f'Apport engrais {crop_name}',
                'description': 'Fertilisation recommandée après le semis.',
                'type': 'fertilization',
                'relative': _format_relative_date(fertilizer_date, now)
            })

        watering_date = now + datetime.timedelta(days=3)
        events.append({
            'date': watering_date.isoformat(),
            'title': f'Arrosage {crop_name}',
            'description': 'Vérifier l’humidité du sol et arroser si nécessaire.',
            'type': 'watering',
            'relative': _format_relative_date(watering_date, now)
        })

        if harvest_date >= now - datetime.timedelta(days=7):
            events.append({
                'date': harvest_date.isoformat(),
                'title': f'Récolte {crop_name}',
                'description': f'Prévue après {days_to_mature} jours depuis plantation.',
                'type': 'harvest',
                'relative': _format_relative_date(harvest_date, now)
            })
    else:
        next_plant_month = min(req['planting_months'], key=lambda m: ((m - now.month) % 12))
        year = now.year + (1 if next_plant_month < now.month else 0)
        planting_date = datetime.datetime(year, next_plant_month, min(10, now.day if now.day < 10 else 10))
        events.append({
            'date': planting_date.isoformat(),
            'title': f'Semis recommandé pour {crop_name}',
            'description': 'Planifiez la plantation pour la prochaine fenêtre optimale.',
            'type': 'planting',
            'relative': _format_relative_date(planting_date, now)
        })

    return events


@router.get('/farmer/calendar/')
def get_farmer_calendar(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    now = datetime.datetime.utcnow()
    events = []
    for crop in current_user.crops or []:
        events.extend(_build_crop_calendar_events(crop, now))

    if not events:
        return {
            'events': [
                {
                    'date': now.isoformat(),
                    'title': 'Aucun calendrier de culture disponible',
                    'description': 'Ajoutez une culture pour générer des tâches agricoles personnalisées.',
                    'type': 'info',
                    'relative': 'Aucun événement'
                }
            ]
        }

    events.sort(key=lambda item: item['date'])
    return {'events': events}
