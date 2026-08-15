from fastapi import APIRouter, Depends

import auth
import models
import schemas
from core.error_handling import ServiceError, raise_http_error
from routers.users import login_for_access_token
from routers.dashboard import get_weather, get_markets
from services.user_profile_service import UserProfileService

try:
    from services.vendor_proxy import get_chart_js
except Exception:
    get_chart_js = None

router = APIRouter(tags=["compatibility"])

# Legacy route aliases for older clients.
router.post("/token")(login_for_access_token)


@router.get("/me", response_model=schemas.UserResponse)
@router.get("/me/", response_model=schemas.UserResponse)
def get_current_user_me(current_user: models.User = Depends(auth.get_current_user)):
    try:
        profile = UserProfileService.get_profile(current_user)
    except ServiceError as exc:
        raise_http_error(exc)
    return profile


@router.get("/weather")
@router.get("/weather/")
def weather_compat_route(lat: float = 0.0, lon: float = 0.0):
    return get_weather(lat=lat, lon=lon)


@router.get("/markets")
@router.get("/markets/")
def markets_compat_route(lat: float = 0.0, lon: float = 0.0):
    return get_markets(lat=lat, lon=lon)


if get_chart_js is not None:
    @router.get("/vendor/chart.js")
    def vendor_chart_js():
        return get_chart_js()
