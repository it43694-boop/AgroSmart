import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

import models
from services.blockchain_service import add_trace_on_chain, get_trace_from_chain, verify_certification_on_chain

logger = logging.getLogger("sustainability_service")


def _estimate_carbon_score(certification: Optional[str], product_type: Optional[str], origin: str) -> float:
    base = 1.0
    if certification:
        if "organic" in certification.lower() or "bio" in certification.lower():
            base += 1.5
        if "durable" in certification.lower() or "sustainable" in certification.lower():
            base += 1.2
        if "zero" in certification.lower() or "net zero" in certification.lower():
            base += 2.0
    if product_type:
        if "wood" in product_type.lower() or "livestock" in product_type.lower():
            base += 0.8
        if "fruit" in product_type.lower() or "vegetable" in product_type.lower():
            base += 0.5
    if origin and origin.lower() != "mali":
        base += 0.2
    return round(base * 10.0, 2)


def _generate_durability_label(carbon_score: float, certification: Optional[str]) -> str:
    if carbon_score >= 25 or (certification and "organic" in certification.lower()):
        return "Durable Plus"
    if carbon_score >= 15:
        return "Durable"
    if carbon_score >= 8:
        return "Standard Durable"
    return "Baseline"


def _build_qr_code_payload(product_id: str, origin: str, certification: Optional[str], durability_label: str) -> str:
    payload = {
        "product_id": product_id,
        "origin": origin,
        "certification": certification,
        "durability_label": durability_label,
        "timestamp": datetime.utcnow().isoformat(),
    }
    json_payload = json.dumps(payload, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_payload.encode("utf-8")).decode("utf-8")


def create_traceability_record(db: Session, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    product_id = payload.get("product_id") or payload.get("batch_id") or f"BATCH_{int(datetime.utcnow().timestamp())}"
    origin = payload.get("origin") or payload.get("location") or "Mali"
    certification = payload.get("certification") or payload.get("origin_certification")
    product_type = payload.get("product_type")
    origin_info = payload.get("origin_info") or payload.get("description")
    metadata = payload.get("metadata") or json.dumps({})
    carbon_score = _estimate_carbon_score(certification, product_type, origin)
    durability_label = _generate_durability_label(carbon_score, certification)
    qr_code_data = payload.get("qr_code_data") or _build_qr_code_payload(product_id, origin, certification, durability_label)
    timestamp = int(payload.get("timestamp", datetime.utcnow().timestamp()))

    tx_hash = None
    try:
        tx_hash = add_trace_on_chain(product_id, origin, certification or "origine", timestamp)
    except Exception as e:
        logger.warning("Impossible d'ajouter la trace sur la blockchain: %s", e)

    trace = models.BlockchainTrace(
        product_id=product_id,
        user_id=user_id,
        origin=origin,
        certification_type=certification,
        product_type=product_type,
        origin_info=origin_info,
        carbon_score=carbon_score,
        durability_label=durability_label,
        qr_code_data=qr_code_data,
        metadata_json=json.dumps(payload) if not isinstance(payload.get("metadata"), str) else payload.get("metadata"),
        verified=bool(tx_hash),
        tx_hash=tx_hash,
    )

    db.add(trace)
    db.commit()
    db.refresh(trace)

    return {
        "success": True,
        "trace_id": trace.id,
        "product_id": trace.product_id,
        "origin": trace.origin,
        "certification": trace.certification_type,
        "product_type": trace.product_type,
        "origin_info": trace.origin_info,
        "carbon_score": trace.carbon_score,
        "durability_label": trace.durability_label,
        "qr_code_data": trace.qr_code_data,
        "verified": trace.verified,
        "tx_hash": trace.tx_hash,
        "created_at": trace.created_at.isoformat(),
    }


def get_traceability_record(db: Session, product_id: str) -> Dict[str, Any]:
    trace = db.query(models.BlockchainTrace).filter(models.BlockchainTrace.product_id == product_id).order_by(models.BlockchainTrace.created_at.desc()).first()
    if trace:
        return {
            "product_id": trace.product_id,
            "origin": trace.origin,
            "certification": trace.certification_type,
            "product_type": trace.product_type,
            "origin_info": trace.origin_info,
            "carbon_score": trace.carbon_score,
            "durability_label": trace.durability_label,
            "qr_code_data": trace.qr_code_data,
            "verified": trace.verified,
            "tx_hash": trace.tx_hash,
            "source": "database",
            "created_at": trace.created_at.isoformat(),
        }

    chain_trace = get_trace_from_chain(product_id)
    if chain_trace:
        return {
            "product_id": chain_trace.get("product_id"),
            "origin": chain_trace.get("origin"),
            "certification": chain_trace.get("certification_type"),
            "verified": chain_trace.get("verified", False),
            "source": "blockchain",
        }

    return {}


def mint_certification_nft(db: Session, owner_id: int, product_id: str, certification_type: str) -> Dict[str, Any]:
    tx_hash = verify_certification_on_chain(product_id, certification_type)
    nft_record = models.BlockchainTrace(
        product_id=product_id,
        user_id=owner_id,
        certification_type=certification_type,
        origin="NFT Certification",
        verified=bool(tx_hash),
        tx_hash=tx_hash,
        metadata=json.dumps({"nft_certification": True, "product_id": product_id, "certification_type": certification_type}),
    )
    db.add(nft_record)
    db.commit()
    db.refresh(nft_record)

    return {
        "success": True,
        "product_id": product_id,
        "certification_type": certification_type,
        "tx_hash": tx_hash,
        "verified": bool(tx_hash),
        "trace_id": nft_record.id,
    }


def create_resource_exchange(db: Session, requester_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    exchange = models.ResourceExchange(
        requester_id=requester_id,
        resource_type=payload.get("resource_type", "resource"),
        description=payload.get("description"),
        quantity=payload.get("quantity", 0.0),
        unit=payload.get("unit", "unit"),
        status="open",
    )
    db.add(exchange)
    db.commit()
    db.refresh(exchange)
    return {
        "success": True,
        "exchange_id": exchange.id,
        "resource_type": exchange.resource_type,
        "description": exchange.description,
        "quantity": exchange.quantity,
        "unit": exchange.unit,
        "status": exchange.status,
        "created_at": exchange.created_at.isoformat(),
    }


def list_resource_exchanges(db: Session, status: Optional[str] = "open") -> List[Dict[str, Any]]:
    query = db.query(models.ResourceExchange)
    if status:
        query = query.filter(models.ResourceExchange.status == status)
    exchanges = query.order_by(models.ResourceExchange.created_at.desc()).all()
    return [
        {
            "id": item.id,
            "requester_id": item.requester_id,
            "resource_type": item.resource_type,
            "description": item.description,
            "quantity": item.quantity,
            "unit": item.unit,
            "status": item.status,
            "exchange_partner_id": item.exchange_partner_id,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in exchanges
    ]


def create_recycling_record(db: Session, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    record = models.RecyclingRecord(
        user_id=user_id,
        material_type=payload.get("material_type", "unknown"),
        quantity=payload.get("quantity", 0.0),
        unit=payload.get("unit", "kg"),
        outcome=payload.get("outcome"),
        collection_location=payload.get("collection_location"),
        reuse_plan=payload.get("reuse_plan"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "success": True,
        "record_id": record.id,
        "material_type": record.material_type,
        "quantity": record.quantity,
        "unit": record.unit,
        "outcome": record.outcome,
        "collection_location": record.collection_location,
        "reuse_plan": record.reuse_plan,
        "created_at": record.created_at.isoformat(),
    }


def get_recycling_history(db: Session, user_id: int) -> List[Dict[str, Any]]:
    records = db.query(models.RecyclingRecord).filter(models.RecyclingRecord.user_id == user_id).order_by(models.RecyclingRecord.created_at.desc()).all()
    return [
        {
            "id": record.id,
            "material_type": record.material_type,
            "quantity": record.quantity,
            "unit": record.unit,
            "outcome": record.outcome,
            "collection_location": record.collection_location,
            "reuse_plan": record.reuse_plan,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]
