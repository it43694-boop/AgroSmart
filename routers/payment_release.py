from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from services.payment_release_service import payment_release_service
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["payment_release"])

class DeliveryConfirmation(BaseModel):
    order_id: int

@router.post("/payment-release/confirm-delivery")
async def confirm_delivery(
    confirmation: DeliveryConfirmation,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Confirme la livraison d'une commande et libère le paiement au vendeur"""
    result = payment_release_service.confirm_delivery(db, confirmation.order_id, current_user.id)
    return result

@router.post("/payment-release/release/{order_id}")
async def release_payment(
    order_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Libère manuellement le paiement au vendeur (admin ou vendeur)"""
    order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    
    if current_user.id != order.listing.seller_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    result = payment_release_service.release_payment_to_seller(db, order_id)
    return result

@router.get("/payment-release/seller-balance")
async def get_seller_balance(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère le solde du vendeur"""
    # Autoriser tous les utilisateurs à voir leur solde s'ils ont des transactions
    result = payment_release_service.get_seller_balance(db, current_user.id)
    return result

@router.get("/payment-release/seller-history")
async def get_seller_history(
    limit: int = 20,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'historique des paiements du vendeur"""
    if current_user.role not in ["farmer", "admin"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux vendeurs")
    
    result = payment_release_service.get_seller_payment_history(db, current_user.id, limit)
    return result
