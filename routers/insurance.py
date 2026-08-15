"""Insurance API routes for dashboard and policy management."""
from fastapi import APIRouter, Depends, HTTPException
import datetime
from sqlalchemy.orm import Session

from database import get_db
import models
import auth

router = APIRouter(prefix="/api/insurance", tags=["insurance"])


def _insurance_payload(insurance: models.Insurance) -> dict:
    return {
        "id": insurance.id,
        "owner_id": insurance.owner_id,
        "type": insurance.type,
        "premium": insurance.premium,
        "coverage": insurance.coverage,
        "status": insurance.status,
        "duration_months": getattr(insurance, "duration_months", None),
        "requested_date": insurance.requested_date.isoformat() if insurance.requested_date else None,
        "approved_date": insurance.approved_date.isoformat() if insurance.approved_date else None,
    }


@router.get("/policies/")
def list_insurance_policies(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_insurance)):
    insurances = db.query(models.Insurance).all()
    return [_insurance_payload(i) for i in insurances]


@router.get("/policy-requests/")
def list_pending_insurance_requests(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_insurance)):
    pending = db.query(models.Insurance).filter(models.Insurance.status == "pending").all()
    return [_insurance_payload(i) for i in pending]


@router.put("/{insurance_id}/approve/")
def approve_insurance(insurance_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_insurance)):
    insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not insurance:
        raise HTTPException(status_code=404, detail="Assurance non trouvée")
    insurance.status = "approved"
    insurance.approved_date = datetime.datetime.utcnow()
    db.commit()
    db.refresh(insurance)
    return _insurance_payload(insurance)


@router.put("/{insurance_id}/reject/")
def reject_insurance(insurance_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_insurance)):
    insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not insurance:
        raise HTTPException(status_code=404, detail="Assurance non trouvée")
    insurance.status = "rejected"
    db.commit()
    db.refresh(insurance)
    return _insurance_payload(insurance)


@router.get("/claims/")
def list_insurance_claims(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_insurance)):
    claims = []
    insurances = db.query(models.Insurance).all()
    for insurance in insurances:
        if insurance.status != "approved":
            continue
        claim = {
            "id": insurance.id * 1000,
            "insurance_id": insurance.id,
            "type": insurance.type or "crop",
            "status": "open",
            "severity": "medium",
            "region": "Bamako",
            "amount": insurance.coverage or 0,
            "description": f"Sinistre de couverture pour {insurance.type or 'assurance'}",
            "created_at": (insurance.approved_date or insurance.requested_date).isoformat() if (insurance.approved_date or insurance.requested_date) else None,
        }
        claims.append(claim)
    return claims
