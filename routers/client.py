"""Client API routes - Orders, requests, and client-specific data."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import auth

router = APIRouter(prefix="/api/client", tags=["client"])


@router.get("/orders/")
def list_client_orders(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get all orders for current user (marketplace orders)."""
    orders = db.query(models.MarketplaceOrder).filter(
        models.MarketplaceOrder.buyer_id == current_user.id
    ).all()
    return [
        {
            "id": order.id,
            "listing_id": order.listing_id,
            "quantity": order.quantity,
            "total_price": order.total_price,
            "currency": order.currency,
            "status": order.status,
            "shipping_address": order.shipping_address,
            "recipient_name": order.recipient_name,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }
        for order in orders
    ]


@router.get("/requests/")
def list_client_requests(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get all pending loan and insurance requests for current user."""
    loans = db.query(models.Loan).filter(
        models.Loan.owner_id == current_user.id
    ).all()
    insurances = db.query(models.Insurance).filter(
        models.Insurance.owner_id == current_user.id
    ).all()
    
    return {
        "loan_requests": [
            {
                "id": loan.id,
                "amount": loan.amount,
                "status": loan.status,
                "requested_date": loan.requested_date.isoformat() if loan.requested_date else None,
                "approved_date": loan.approved_date.isoformat() if loan.approved_date else None,
            }
            for loan in loans
        ],
        "insurance_requests": [
            {
                "id": insurance.id,
                "type": insurance.type,
                "premium": insurance.premium,
                "coverage": insurance.coverage,
                "status": insurance.status,
                "requested_date": insurance.requested_date.isoformat() if insurance.requested_date else None,
                "approved_date": insurance.approved_date.isoformat() if insurance.approved_date else None,
            }
            for insurance in insurances
        ]
    }
