"""Bank API routes - Loan management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import auth

router = APIRouter(prefix="/api/bank", tags=["bank"])


@router.get("/loans/")
def list_all_loans(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get all loans (for bank dashboard)."""
    if current_user.effective_role not in ("bank", "admin"):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    loans = db.query(models.Loan).all()
    return [
        {
            "id": loan.id,
            "owner_id": loan.owner_id,
            "amount": loan.amount,
            "status": loan.status,
            "requested_date": loan.requested_date.isoformat() if loan.requested_date else None,
            "approved_date": loan.approved_date.isoformat() if loan.approved_date else None,
        }
        for loan in loans
    ]


@router.get("/loan-requests/")
def list_pending_loan_requests(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get pending loan requests only."""
    if current_user.effective_role not in ("bank", "admin"):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    loans = db.query(models.Loan).filter(models.Loan.status == "pending").all()
    return [
        {
            "id": loan.id,
            "owner_id": loan.owner_id,
            "amount": loan.amount,
            "status": loan.status,
            "requested_date": loan.requested_date.isoformat() if loan.requested_date else None,
        }
        for loan in loans
    ]


@router.put("/loans/{loan_id}/approve/")
def approve_loan(loan_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Approve a loan request."""
    if current_user.effective_role not in ("bank", "admin"):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Prêt non trouvé")
    
    import datetime
    loan.status = "approved"
    loan.approved_date = datetime.datetime.utcnow()
    db.commit()
    db.refresh(loan)
    
    return {
        "id": loan.id,
        "status": loan.status,
        "approved_date": loan.approved_date.isoformat() if loan.approved_date else None,
    }


@router.put("/loans/{loan_id}/reject/")
def reject_loan(loan_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Reject a loan request."""
    if current_user.effective_role not in ("bank", "admin"):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Prêt non trouvé")
    
    loan.status = "rejected"
    db.commit()
    db.refresh(loan)
    
    return {
        "id": loan.id,
        "status": loan.status,
    }


@router.get("/loans/{loan_id}/")
def get_loan_details(loan_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get details of a specific loan."""
    if current_user.effective_role not in ("bank", "admin"):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Prêt non trouvé")
    
    return {
        "id": loan.id,
        "amount": loan.amount,
        "duration_months": loan.duration_months,
        "purpose": loan.purpose,
        "status": loan.status,
        "requested_date": loan.requested_date.isoformat() if loan.requested_date else None,
        "approved_date": loan.approved_date.isoformat() if loan.approved_date else None,
        "owner_id": loan.owner_id
    }
