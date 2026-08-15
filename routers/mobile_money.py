from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from services.mobile_money_service import mobile_money_service
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api", tags=["mobile_money"])

class MobileMoneyRequest(BaseModel):
    provider: str
    phone_number: str
    amount: float
    currency: str = "XOF"
    reference: Optional[str] = None

class PaymentVerificationRequest(BaseModel):
    provider: str
    transaction_id: str

@router.post("/mobile-money/create-payment")
async def create_payment(request: MobileMoneyRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    result = mobile_money_service.create_payment(
        request.provider,
        request.phone_number,
        request.amount,
        request.currency,
        request.reference,
        current_user.id,
        db
    )
    return result

@router.post("/mobile-money/verify-payment")
async def verify_payment(request: PaymentVerificationRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = mobile_money_service.verify_payment(request.provider, request.transaction_id)
    return result

@router.get("/mobile-money/providers")
async def get_available_providers(current_user: models.User = Depends(auth.get_current_user)):
    providers = ["orange_money", "wave", "mtn_money", "moov_money"]
    return {"providers": providers}

@router.post("/mobile-money/callback/{provider}")
async def payment_callback(provider: str, callback_data: dict, db: Session = Depends(get_db)):
    result = mobile_money_service.handle_callback(provider, callback_data, db)
    return result

@router.get("/mobile-money/transaction/{transaction_id}")
async def get_transaction_status(transaction_id: str, current_user: models.User = Depends(auth.get_current_user)):
    result = mobile_money_service.get_transaction_status(transaction_id)
    return result

@router.post("/mobile-money/refund/{transaction_id}")
async def refund_transaction(transaction_id: str, current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    result = mobile_money_service.refund_transaction(transaction_id)
    return result
