from fastapi import APIRouter, Depends, HTTPException
import datetime
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from utils import get_user_or_404

router = APIRouter(prefix="/api", tags=["finance"])


@router.post("/users/{user_id}/loans/", response_model=schemas.LoanResponse)
def request_loan(user_id: int, loan: schemas.LoanCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    db_loan = models.Loan(**loan.dict(), owner_id=user.id)
    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan


@router.get("/users/{user_id}/loans/", response_model=list[schemas.LoanResponse])
def list_user_loans(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return user.loans


@router.put("/loans/{loan_id}/approve/", response_model=schemas.LoanResponse)
def approve_loan(loan_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Prêt non trouvé")
    loan.status = "approved"
    loan.approved_date = datetime.datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan


@router.put("/loans/{loan_id}/reject/", response_model=schemas.LoanResponse)
def reject_loan(loan_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Prêt non trouvé")
    loan.status = "rejected"
    db.commit()
    db.refresh(loan)
    return loan


@router.post("/users/{user_id}/insurances/", response_model=schemas.InsuranceResponse)
def request_insurance(user_id: int, insurance: schemas.InsuranceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    db_insurance = models.Insurance(**insurance.dict(), owner_id=user.id)
    db.add(db_insurance)
    db.commit()
    db.refresh(db_insurance)
    return db_insurance


@router.get("/users/{user_id}/insurances/", response_model=list[schemas.InsuranceResponse])
def list_user_insurances(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return user.insurances


@router.put("/insurances/{insurance_id}/approve/", response_model=schemas.InsuranceResponse)
def approve_insurance(insurance_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not insurance:
        raise HTTPException(status_code=404, detail="Assurance non trouvée")
    insurance.status = "approved"
    insurance.approved_date = datetime.datetime.utcnow()
    db.commit()
    db.refresh(insurance)
    return insurance


@router.put("/insurances/{insurance_id}/reject/", response_model=schemas.InsuranceResponse)
def reject_insurance(insurance_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not insurance:
        raise HTTPException(status_code=404, detail="Assurance non trouvée")
    insurance.status = "rejected"
    db.commit()
    db.refresh(insurance)
    return insurance
