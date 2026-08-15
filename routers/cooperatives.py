from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from services.cooperatives_service import (
    create_cooperative,
    join_cooperative,
    approve_cooperative_membership,
    record_cooperative_contribution,
    create_group_purchase,
    join_group_purchase,
    get_cooperative_dashboard,
    get_available_cooperatives,
    get_mali_cooperatives_templates,
    get_cooperative_statistics,
    list_cooperative_group_purchases,
)
from services.social_training_service import (
    create_cooperative_training,
    list_cooperative_trainings,
    join_cooperative_training,
)
from utils import _raise_service_error

router = APIRouter(prefix="/api", tags=["cooperatives"])


@router.post("/cooperative/trainings/", response_model=schemas.CooperativeTrainingResponse)
def create_cooperative_training_endpoint(training: schemas.CooperativeTrainingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_cooperative_training(current_user.id, training.dict(), db)
    if not result.get("training_id"):
        _raise_service_error(result if isinstance(result, dict) else {"error": "Création formation échouée"})
    return db.query(models.CooperativeTraining).filter(models.CooperativeTraining.id == result["training_id"]).first()


@router.get("/cooperative/trainings/", response_model=list[schemas.CooperativeTrainingResponse])
def get_cooperative_trainings(cooperative_id: Optional[int] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_cooperative_trainings(db, cooperative_id)


@router.post("/cooperative/trainings/{training_id}/join/")
def join_cooperative_training_endpoint(training_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = join_cooperative_training(current_user.id, training_id, db)
    _raise_service_error(result)
    return result


@router.post("/cooperatives/", response_model=schemas.CooperativeResponse)
def create_cooperative_endpoint(payload: schemas.CooperativeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_cooperative(payload.name, payload.region, payload.description or "", current_user.id, db)
    _raise_service_error(result)
    return db.query(models.Cooperative).filter(models.Cooperative.id == result["cooperative_id"]).first()


@router.get("/cooperatives/", response_model=list[schemas.CooperativeResponse])
def list_cooperatives_endpoint(region: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    cooperatives = get_available_cooperatives(region, db)
    if not cooperatives:
        return db.query(models.Cooperative).filter(models.Cooperative.status == "active").all()
    ids = [c["id"] for c in cooperatives if c.get("id")]
    if not ids:
        return []
    return db.query(models.Cooperative).filter(models.Cooperative.id.in_(ids)).all()


@router.post("/cooperatives/{cooperative_id}/join/")
def join_cooperative_endpoint(cooperative_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = join_cooperative(cooperative_id, current_user.id, db)
    _raise_service_error(result)
    return result


@router.post("/cooperatives/memberships/{membership_id}/approve/")
def approve_cooperative_membership_endpoint(membership_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = approve_cooperative_membership(membership_id, current_user.id, db)
    _raise_service_error(result)
    return result


@router.post("/cooperatives/contributions/")
def record_contribution_endpoint(payload: schemas.CooperativeContributionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = record_cooperative_contribution(
        payload.cooperative_id,
        current_user.id,
        payload.contribution_type,
        payload.amount,
        payload.description or "",
        db,
    )
    _raise_service_error(result)
    return result


@router.get("/cooperatives/templates/")
def cooperative_templates_endpoint(current_user: models.User = Depends(auth.get_current_user)):
    return get_mali_cooperatives_templates()


@router.get("/cooperatives/statistics/")
def cooperative_statistics_endpoint(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return get_cooperative_statistics(db)


@router.get("/cooperatives/{cooperative_id}/dashboard/")
def cooperative_dashboard_endpoint(cooperative_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = get_cooperative_dashboard(cooperative_id, db)
    _raise_service_error(result, status_code=404)
    return result
@router.get("/cooperatives/{cooperative_id}/purchases/", response_model=list[schemas.CooperativeGroupPurchaseResponse])
def list_cooperative_purchases_endpoint(cooperative_id: int, status: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_cooperative_group_purchases(cooperative_id, db, status)


@router.post("/cooperatives/purchases/", response_model=schemas.CooperativeGroupPurchaseResponse)
def create_group_purchase_endpoint(payload: schemas.CooperativeGroupPurchaseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_group_purchase(
        payload.cooperative_id,
        payload.product_name,
        payload.quantity_needed,
        payload.budget_max,
        current_user.id,
        db,
    )
    _raise_service_error(result)
    purchase = db.query(models.CooperativeGroupPurchase).filter(models.CooperativeGroupPurchase.id == result["purchase_id"]).first()
    committed = 0.0
    return {
        "id": purchase.id,
        "cooperative_id": purchase.cooperative_id,
        "product_name": purchase.product_name,
        "quantity_needed": purchase.quantity_needed,
        "quantity_committed": committed,
        "budget_max": purchase.budget_max,
        "organizer_id": purchase.organizer_id,
        "status": purchase.status,
        "created_at": purchase.created_at,
    }


@router.post("/cooperatives/purchases/{purchase_id}/join/")
def join_group_purchase_endpoint(purchase_id: int, payload: schemas.CooperativeJoinPurchase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = join_group_purchase(purchase_id, current_user.id, payload.quantity_committed, db)
    _raise_service_error(result)
    return result
