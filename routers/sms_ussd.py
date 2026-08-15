from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from services.sms_ussd_service import sms_ussd_service
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["sms_ussd"])

class SMSRequest(BaseModel):
    phone_number: str
    message: str

class USSDRequest(BaseModel):
    session_id: str
    phone_number: str
    user_input: str

@router.post("/sms/send")
async def send_sms(request: SMSRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = sms_ussd_service.sms_service.send_sms(request.phone_number, request.message)
    return result

@router.post("/ussd/process")
async def process_ussd(request: USSDRequest, db: Session = Depends(get_db)):
    result = sms_ussd_service.ussd_service.process_ussd_request(
        request.session_id, request.phone_number, request.user_input, db
    )
    return result

@router.post("/offline/sync/{user_id}")
async def sync_offline_data(user_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    result = sms_ussd_service.sync_offline_data(user_id, db)
    return result

@router.get("/offline/sync/me")
async def sync_my_offline_data(
    current_user: models.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        result = sms_ussd_service.sync_offline_data(current_user.id, db)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/sms/weather-alert")
async def send_weather_sms(phone_number: str, region: str, alert_type: str, current_user: models.User = Depends(auth.get_current_user)):
    message = f"ALERTE METEO {alert_type.upper()} pour {region}. Prenez les precautions necessaires."
    result = sms_ussd_service.sms_service.send_sms(phone_number, message)
    return result

@router.post("/sms/order-update")
async def send_order_sms(phone_number: str, order_id: int, status: str, current_user: models.User = Depends(auth.get_current_user)):
    status_messages = {
        "confirmed": "Commande confirmee",
        "shipped": "Commande expediee",
        "delivered": "Commande livree",
        "cancelled": "Commande annulee"
    }
    message = f"AgroSmart: Commande #{order_id} - {status_messages.get(status, status)}"
    result = sms_ussd_service.sms_service.send_sms(phone_number, message)
    return result
