"""
Admin Service - Logique métier pour l'administration
"""
from sqlalchemy.orm import Session
import models
import schemas


def get_admin_stats(db: Session) -> schemas.AdminStatsResponse:
    """Calcule les statistiques administratives"""
    total_users = db.query(models.User).count()
    validated_users = db.query(models.User).filter(models.User.is_validated == True).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    pending_loans = db.query(models.Loan).filter(models.Loan.status == "pending").count()
    approved_loans = db.query(models.Loan).filter(models.Loan.status == "approved").count()
    pending_insurances = db.query(models.Insurance).filter(models.Insurance.status == "pending").count()
    approved_insurances = db.query(models.Insurance).filter(models.Insurance.status == "approved").count()
    total_revenue = db.query(models.FinanceRecord).with_entities(models.FinanceRecord.revenue).all()
    total_revenue = sum(r[0] for r in total_revenue) if total_revenue else 0.0
    total_cost = db.query(models.FinanceRecord).with_entities(models.FinanceRecord.cost).all()
    total_cost = sum(c[0] for c in total_cost) if total_cost else 0.0
    total_loan_amount = db.query(models.Loan).with_entities(models.Loan.amount).all()
    total_loan_amount = sum(a[0] for a in total_loan_amount) if total_loan_amount else 0.0
    total_insurance_coverage = db.query(models.Insurance).with_entities(models.Insurance.coverage).all()
    total_insurance_coverage = sum(c[0] for c in total_insurance_coverage) if total_insurance_coverage else 0.0

    stats = schemas.AdminStatsResponse(
        total_users=total_users,
        validated_users=validated_users,
        active_users=active_users,
        pending_loans=pending_loans,
        approved_loans=approved_loans,
        pending_insurances=pending_insurances,
        approved_insurances=approved_insurances,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_loan_amount=total_loan_amount,
        total_insurance_coverage=total_insurance_coverage,
    )
    return stats


def get_admin_crops_summary(db: Session):
    """Résumé des cultures pour l'admin"""
    all_crops = db.query(models.Crop).all()
    crop_summary = {}
    for crop in all_crops:
        if crop.name not in crop_summary:
            crop_summary[crop.name] = {"count": 0, "total_surface": 0.0}
        crop_summary[crop.name]["count"] += 1
        crop_summary[crop.name]["total_surface"] += crop.surface

    return {
        "total_crops": len(all_crops),
        "crop_types": len(crop_summary),
        "summary": crop_summary,
        "data": [
            {"name": crop_type, "count": data["count"], "surface_ha": data["total_surface"]}
            for crop_type, data in crop_summary.items()
        ]
    }


def get_admin_finance_summary(db: Session):
    """Résumé financier pour l'admin"""
    all_records = db.query(models.FinanceRecord).all()
    total_revenue = sum(record.revenue for record in all_records)
    total_cost = sum(record.cost for record in all_records)
    net_gain = total_revenue - total_cost

    return {
        "total_records": len(all_records),
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "net_gain": net_gain,
        "average_revenue_per_record": total_revenue / len(all_records) if all_records else 0,
        "average_cost_per_record": total_cost / len(all_records) if all_records else 0,
    }