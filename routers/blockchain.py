import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from services.blockchain_service import (
    get_blockchain_status,
    add_trace_on_chain,
    get_trace_from_chain,
    verify_certification_on_chain,
)
from services.sustainability_service import (
    create_traceability_record,
    get_traceability_record,
    mint_certification_nft,
    create_resource_exchange,
    list_resource_exchanges,
    create_recycling_record,
    get_recycling_history,
)
from services.community_tokens_service import (
    calculate_sustainability_score,
    get_token_balance,
    get_token_history,
    redeem_community_tokens,
    get_community_leaderboard,
    get_token_statistics,
)
from services.impact_tracking_service import generate_impact_report

router = APIRouter(prefix="/api", tags=["blockchain"])

BLOCKCHAIN_TRACES: list[dict] = []
BLOCKCHAIN_CERTIFICATION_LOG: list[dict] = []


@router.get("/blockchain/status/")
def blockchain_status():
    status = get_blockchain_status()
    return {
        "service": "AgroSmart Blockchain Traceability",
        "version": "1.0",
        "status": "operational",
        "provider_url": status.get("provider_url"),
        "network": status.get("network"),
        "chain_id": status.get("chain_id"),
        "provider_connected": status.get("provider_connected"),
        "contract_configured": status.get("contract_configured"),
        "private_key_configured": status.get("private_key_configured"),
        "errors": status.get("errors", []),
    }


@router.post("/blockchain/trace/")
def create_blockchain_trace(payload: schemas.BlockchainTraceCreate, current_user: models.User = Depends(auth.get_current_user)):
    product_id = payload.product_id or payload.batch_id or f"BATCH_{int(datetime.datetime.utcnow().timestamp())}"
    origin = payload.origin or payload.location or "Mali"
    certification = payload.certification

    description = payload.description or ""
    if not certification:
        if payload.organic or payload.bio or "bio" in description.lower() or "organique" in description.lower():
            certification = "bio"
        elif payload.sustainable or payload.durable or "durable" in description.lower():
            certification = "durable"
        else:
            certification = payload.origin_certification or "origine"

    timestamp = int(payload.timestamp or datetime.datetime.utcnow().timestamp())

    if not product_id:
        raise HTTPException(status_code=400, detail="product_id est requis")

    tx_hash = add_trace_on_chain(product_id, origin, certification, timestamp)
    trace_record = {
        "product_id": product_id,
        "origin": origin,
        "certification": certification,
        "timestamp": timestamp,
        "recorded_by": current_user.email,
        "verification_source": "blockchain" if tx_hash else "local_fallback",
        "tx_hash": tx_hash,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    BLOCKCHAIN_TRACES.append(trace_record)
    return {
        "success": True,
        "trace": trace_record,
        "tx_hash": tx_hash,
        "fallback": tx_hash is None,
    }


@router.get("/blockchain/traces/")
def list_blockchain_traces():
    from database import SessionLocal
    from models import BlockchainTrace

    try:
        with SessionLocal() as db:
            traces = db.query(BlockchainTrace).order_by(BlockchainTrace.created_at.desc()).all()
            return [
                {
                    "product_id": trace.product_id,
                    "origin": trace.origin,
                    "certification": trace.certification_type,
                    "timestamp": int(trace.created_at.timestamp()) if trace.created_at else None,
                    "recorded_by": None,
                    "verification_source": "blockchain" if trace.verified else "local_fallback",
                    "tx_hash": trace.tx_hash,
                    "created_at": trace.created_at.isoformat() if trace.created_at else None,
                }
                for trace in traces
            ]
    except Exception as exc:
        return []


@router.get("/api/blockchain/trace/{product_id}/")
def get_blockchain_trace(product_id: str, current_user: models.User = Depends(auth.get_current_user)):
    trace = get_trace_from_chain(product_id)
    if trace:
        return {
            "product_id": product_id,
            "origin": trace.get("origin"),
            "certification": trace.get("certification_type"),
            "timestamp": trace.get("timestamp"),
            "verified": trace.get("verified"),
            "source": "blockchain",
        }

    local_trace = next((t for t in BLOCKCHAIN_TRACES if t["product_id"] == product_id), None)
    if local_trace:
        return {
            "product_id": local_trace["product_id"],
            "origin": local_trace["origin"],
            "certification": local_trace["certification"],
            "timestamp": local_trace["timestamp"],
            "verified": local_trace.get("verification_source") == "blockchain",
            "source": "local_fallback",
            "tx_hash": local_trace.get("tx_hash"),
        }

    raise HTTPException(status_code=404, detail="Trace introuvable")


@router.post("/api/blockchain/verify-certification/")
def blockchain_verify_certification(payload: schemas.BlockchainCertificationRequest, current_user: models.User = Depends(auth.get_current_user)):
    if not payload.product_id or not payload.certification_type:
        raise HTTPException(status_code=400, detail="product_id et certification_type sont requis")

    tx_hash = verify_certification_on_chain(payload.product_id, payload.certification_type)
    verification_record = {
        "product_id": payload.product_id,
        "certification_type": payload.certification_type,
        "verified_by": current_user.email,
        "tx_hash": tx_hash,
        "verified_at": datetime.datetime.utcnow().isoformat(),
        "source": "blockchain" if tx_hash else "local_fallback",
    }
    return {
        "success": True,
        "verification": verification_record,
        "fallback": tx_hash is None,
    }


@router.post("/api/traceability/record/", response_model=schemas.TraceabilityResponse)
def create_traceability(payload: schemas.TraceabilityCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    trace = create_traceability_record(db, current_user.id, payload.model_dump())
    if not trace.get("success"):
        raise HTTPException(status_code=500, detail="Impossible de créer la trace")
    return {
        "product_id": trace["product_id"],
        "origin": trace["origin"],
        "certification": trace["certification"],
        "product_type": trace["product_type"],
        "origin_info": trace["origin_info"],
        "carbon_score": trace["carbon_score"],
        "durability_label": trace["durability_label"],
        "qr_code_data": trace["qr_code_data"],
        "verified": trace["verified"],
        "tx_hash": trace["tx_hash"],
        "source": "blockchain" if trace["verified"] else "local_fallback",
    }


@router.get("/api/traceability/{product_id}/", response_model=schemas.TraceabilityResponse)
def read_traceability(product_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    trace = get_traceability_record(db, product_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace introuvable")
    return {
        "product_id": trace.get("product_id"),
        "origin": trace.get("origin"),
        "certification": trace.get("certification"),
        "product_type": trace.get("product_type"),
        "origin_info": trace.get("origin_info"),
        "carbon_score": trace.get("carbon_score"),
        "durability_label": trace.get("durability_label"),
        "qr_code_data": trace.get("qr_code_data"),
        "verified": trace.get("verified", False),
        "tx_hash": trace.get("tx_hash"),
        "source": trace.get("source", "database"),
    }


@router.post("/traceability/mint-nft/")
def mint_certification(payload: schemas.MintCertificationRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = mint_certification_nft(db, current_user.id, payload.product_id, payload.certification_type)
    return result


@router.get("/sustainability/score/{user_id}/", response_model=schemas.SustainabilityScoreResponse)
def sustainability_score(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    score = calculate_sustainability_score(user_id, db)
    if score.get("error"):
        raise HTTPException(status_code=500, detail=score["error"])
    return score


@router.get("/sustainability/report/")
def sustainability_report(
    report_type: str = "comprehensive",
    period_months: int = 12,
    stakeholder: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    report = generate_impact_report(db, report_type, period_months, stakeholder)
    if stakeholder:
        report["stakeholder_focus"] = stakeholder
    return report

@router.get("/community/tokens/balance/{user_id}/")
def community_token_balance(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return {"user_id": user_id, "balance": get_token_balance(user_id, db)}

@router.get("/community/tokens/history/{user_id}/")
def community_token_history(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return {"user_id": user_id, "history": get_token_history(user_id, 50, db)}

@router.post("/community/tokens/redeem/")
def community_token_redeem(payload: schemas.TokenRedemptionRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.id != payload.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    result = redeem_community_tokens(payload.user_id, payload.item_type, payload.quantity, db)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/community/tokens/leaderboard/")
def community_token_leaderboard(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return {"leaderboard": get_community_leaderboard(db, 20)}

@router.get("/community/tokens/stats/")
def community_token_statistics(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return get_token_statistics(db)
