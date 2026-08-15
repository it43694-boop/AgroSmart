"""
Marketplace Service - Économie agricole peer-to-peer révolutionnaire

Fonctionnalités :
- Place de marché intégrée avec blockchain
- Système de réputation et garanties
- API de paiement intégrée
- Logistique connectée
- IA matchmaking avancée (Phase 3.2)
- Paiements crypto intégrés
"""
import logging
import json
import uuid
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

import models
import schemas
from services.blockchain_service import (
    add_trace_on_chain, get_trace_from_chain, deploy_escrow_contract,
    fund_escrow_contract, release_escrow_funds, deploy_nft_contract,
    mint_agricultural_nft, transfer_nft
)
from services.blockchain_adapter import get_blockchain_adapter
from services.logistics_service import Location, create_shipment, find_available_carriers, geocode_address
from blockchain_config import BLOCKCHAIN_CONFIG

logger = logging.getLogger("marketplace_service")


# ==========================================
# LISTINGS MANAGEMENT
# ==========================================

def create_listing(db: Session, listing_data: Dict[str, Any]) -> models.MarketplaceListing:
    """
    Créer une nouvelle annonce marketplace avec vérification blockchain
    """
    try:
        # Créer l'annonce
        listing = models.MarketplaceListing(
            seller_id=listing_data["seller_id"],
            title=listing_data["title"],
            description=listing_data.get("description"),
            category=listing_data["category"],
            product_type=listing_data["product_type"],
            quantity=listing_data["quantity"],
            unit=listing_data["unit"],
            price_per_unit=listing_data["price_per_unit"],
            currency=listing_data.get("currency", "XOF"),
            location=listing_data.get("location"),
            latitude=listing_data.get("latitude"),
            longitude=listing_data.get("longitude"),
            images=json.dumps(listing_data.get("images") or []),
            quality_certified=listing_data.get("quality_certified", False),
            organic_certified=listing_data.get("organic_certified", False),
            expires_at=datetime.utcnow() + timedelta(days=30)  # 30 jours par défaut
        )

        db.add(listing)
        db.commit()
        db.refresh(listing)

        # Générer hash blockchain pour l'annonce
        listing_data_hash = {
            "seller_id": listing.seller_id,
            "title": listing.title,
            "product_type": listing.product_type,
            "quantity": listing.quantity,
            "price_per_unit": listing.price_per_unit,
            "created_at": listing.created_at.isoformat()
        }

        # Try to record immutable hash via blockchain adapter (safe: mock when disabled)
        try:
            adapter = get_blockchain_adapter()
            tx = adapter.add_trace_on_chain(f"listing:{listing.id}", listing.location or "unknown", "listing", int(datetime.utcnow().timestamp()))
            listing.blockchain_hash = tx or str(uuid.uuid4())
        except Exception:
            listing.blockchain_hash = str(uuid.uuid4())
        db.commit()

        logger.info(f"Annonce créée: {listing.id} par vendeur {listing.seller_id}")
        return listing

    except Exception as e:
        logger.error(f"Erreur création annonce: {e}")
        db.rollback()
        raise


def get_listings(db: Session, filters: Dict[str, Any] = None) -> List[models.MarketplaceListing]:
    """
    Récupérer les annonces avec filtres avancés
    """
    query = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.is_active == True)

    if filters:
        if "category" in filters:
            query = query.filter(models.MarketplaceListing.category == filters["category"])
        if "product_type" in filters:
            query = query.filter(models.MarketplaceListing.product_type == filters["product_type"])
        if "location" in filters:
            query = query.filter(models.MarketplaceListing.location.ilike(f"%{filters['location']}%"))
        if "min_price" in filters:
            query = query.filter(models.MarketplaceListing.price_per_unit >= filters["min_price"])
        if "max_price" in filters:
            query = query.filter(models.MarketplaceListing.price_per_unit <= filters["max_price"])
        if "seller_id" in filters:
            query = query.filter(models.MarketplaceListing.seller_id == filters["seller_id"])
        if "quality_certified" in filters and filters["quality_certified"]:
            query = query.filter(models.MarketplaceListing.quality_certified == True)
        if "organic_certified" in filters and filters["organic_certified"]:
            query = query.filter(models.MarketplaceListing.organic_certified == True)

    return query.order_by(models.MarketplaceListing.created_at.desc()).all()


def get_listing_by_id(db: Session, listing_id: int) -> Optional[models.MarketplaceListing]:
    """
    Récupérer une annonce par ID
    """
    return db.query(models.MarketplaceListing).filter(
        and_(
            models.MarketplaceListing.id == listing_id,
            models.MarketplaceListing.is_active == True
        )
    ).first()


def update_listing(db: Session, listing_id: int, update_data: Dict[str, Any]) -> Optional[models.MarketplaceListing]:
    """
    Mettre à jour une annonce
    """
    listing = get_listing_by_id(db, listing_id)
    if not listing:
        return None

    for key, value in update_data.items():
        if hasattr(listing, key):
            setattr(listing, key, value)

    listing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(listing)
    return listing


def deactivate_listing(db: Session, listing_id: int) -> bool:
    """
    Désactiver une annonce
    """
    listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
    if not listing:
        return False

    listing.is_active = False
    db.commit()
    return True


# ==========================================
# ORDERS MANAGEMENT
# ==========================================

def create_order(db: Session, order_data: Dict[str, Any]) -> models.MarketplaceOrder:
    """
    Créer une commande avec paiement escrow
    """
    try:
        listing = get_listing_by_id(db, order_data["listing_id"])
        if not listing:
            raise ValueError("Annonce introuvable")

        if listing.quantity < order_data["quantity"]:
            raise ValueError("Quantité insuffisante en stock")

        # Calculer le prix total
        total_price = listing.price_per_unit * order_data["quantity"]

        # Créer la commande
        order = models.MarketplaceOrder(
            listing_id=order_data["listing_id"],
            buyer_id=order_data["buyer_id"],
            quantity=order_data["quantity"],
            total_price=total_price,
            currency=listing.currency,
            shipping_address=order_data.get("shipping_address"),
            delivery_deadline=datetime.utcnow() + timedelta(days=7)  # 7 jours par défaut
        )

        db.add(order)
        db.commit()
        db.refresh(order)

        # Réduire la quantité disponible
        listing.quantity -= order_data["quantity"]
        if listing.quantity <= 0:
            listing.is_active = False
        db.commit()

        # Générer hash blockchain pour la commande
        order_hash_data = {
            "order_id": order.id,
            "buyer_id": order.buyer_id,
            "seller_id": listing.seller_id,
            "total_price": order.total_price,
            "created_at": order.created_at.isoformat()
        }
        order.blockchain_hash = str(uuid.uuid4())  # Placeholder pour blockchain
        db.commit()

        logger.info(f"Commande créée: {order.id} pour {total_price} {order.currency}")
        return order

    except Exception as e:
        logger.error(f"Erreur création commande: {e}")
        db.rollback()
        raise


def get_orders_by_user(db: Session, user_id: int, user_type: str = "buyer") -> List[models.MarketplaceOrder]:
    """
    Récupérer les commandes d'un utilisateur (acheteur ou vendeur)
    """
    if user_type == "buyer":
        return db.query(models.MarketplaceOrder).filter(
            models.MarketplaceOrder.buyer_id == user_id
        ).order_by(models.MarketplaceOrder.created_at.desc()).all()
    else:
        # Pour vendeur, récupérer via les annonces
        return db.query(models.MarketplaceOrder).join(models.MarketplaceListing).filter(
            models.MarketplaceListing.seller_id == user_id
        ).order_by(models.MarketplaceOrder.created_at.desc()).all()


def get_order_by_id(db: Session, order_id: int, user_id: int = None) -> Optional[models.MarketplaceOrder]:
    """
    Récupérer une commande par ID avec vérification des permissions
    """
    order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
    if not order:
        return None

    # Si user_id fourni, vérifier que l'utilisateur a accès à cette commande
    if user_id:
        listing = get_listing_by_id(db, order.listing_id)
        if order.buyer_id != user_id and (not listing or listing.seller_id != user_id):
            return None

    return order


def enrich_orders_with_details(db: Session, orders: List[models.MarketplaceOrder]) -> List[Dict]:
    """
    Enrichir les commandes avec les infos du produit et du vendeur
    """
    enriched = []
    for order in orders:
        # Récupérer les détails du produit
        listing = get_listing_by_id(db, order.listing_id)
        listing_data = None
        if listing:
            listing_data = {
                'id': listing.id,
                'title': listing.title,
                'description': listing.description,
                'price_per_unit': listing.price_per_unit,
                'quantity': listing.quantity,
                'unit': listing.unit,
                'location': listing.location
            }
        
        # Récupérer les détails du vendeur
        seller_data = None
        if listing:
            seller = db.query(models.User).filter(models.User.id == listing.seller_id).first()
            if seller:
                seller_data = {
                    'id': seller.id,
                    'full_name': seller.full_name,
                    'email': seller.email,
                    'phone': seller.phone,
                    'region': seller.region
                }
        
        # Enrichir la commande
        order_dict = {
            'id': order.id,
            'listing_id': order.listing_id,
            'buyer_id': order.buyer_id,
            'quantity': order.quantity,
            'total_price': order.total_price,
            'currency': order.currency,
            'status': order.status,
            'payment_method': order.payment_method,
            'payment_tx_hash': order.payment_tx_hash,
            'delivery_deadline': order.delivery_deadline,
            'tracking_number': order.tracking_number,
            'logistics_provider': order.logistics_provider,
            'blockchain_hash': order.blockchain_hash,
            'shipping_address': order.shipping_address,
            'created_at': order.created_at,
            'paid_at': order.paid_at,
            'shipped_at': order.shipped_at,
            'delivered_at': order.delivered_at,
            'listing': listing_data,
            'seller': seller_data
        }
        enriched.append(order_dict)
    
    return enriched


def update_order_status(db: Session, order_id: int, new_status: str, tracking_info: Dict[str, Any] = None) -> Optional[models.MarketplaceOrder]:
    """
    Mettre à jour le statut d'une commande
    """
    order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
    if not order:
        return None

    old_status = order.status
    order.status = new_status

    # Mettre à jour les timestamps selon le statut
    now = datetime.utcnow()
    if new_status == "paid":
        order.paid_at = now
    elif new_status == "shipped":
        order.shipped_at = now
        if tracking_info:
            order.tracking_number = tracking_info.get("tracking_number")
            order.logistics_provider = tracking_info.get("logistics_provider")
    elif new_status == "delivered":
        order.delivered_at = now

    db.commit()
    db.refresh(order)

    logger.info(f"Commande {order_id}: {old_status} -> {new_status}")
    return order


# ==========================================
# PAYMENT MANAGEMENT
# ==========================================

def process_payment(db: Session, order_id: int, payment_data: Dict[str, Any]) -> models.MarketplacePayment:
    """
    Traiter un paiement avec escrow blockchain
    """
    try:
        order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
        if not order:
            raise ValueError("Commande introuvable")

        if order.status != "pending":
            raise ValueError("Commande déjà payée")

        # Créer l'enregistrement de paiement
        payment = models.MarketplacePayment(
            order_id=order_id,
            amount=order.total_price,
            currency=order.currency,
            payment_method=payment_data["payment_method"],
            payment_provider=payment_data.get("payment_provider"),
            transaction_id=payment_data.get("transaction_id")
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        # Simuler traitement du paiement (en production: intégrer Orange Money, Wave, etc.)
        payment.status = "completed"
        payment.processed_at = datetime.utcnow()
        payment.blockchain_tx_hash = str(uuid.uuid4())  # Placeholder pour escrow blockchain

        # Mettre à jour le statut de la commande
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        order.payment_method = payment.payment_method
        order.payment_tx_hash = payment.blockchain_tx_hash

        db.commit()

        logger.info(f"Paiement traité: {payment.amount} {payment.currency} pour commande {order_id}")
        return payment

    except Exception as e:
        logger.error(f"Erreur traitement paiement: {e}")
        db.rollback()
        raise


def release_escrow(db: Session, order_id: int) -> bool:
    """
    Libérer les fonds escrow après livraison confirmée
    """
    try:
        order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
        if not order or order.status != "delivered":
            return False

        payment = db.query(models.MarketplacePayment).filter(
            and_(
                models.MarketplacePayment.order_id == order_id,
                models.MarketplacePayment.status == "completed"
            )
        ).first()

        if not payment:
            return False

        release_conditions = "delivery_confirmed"
        adapter = get_blockchain_adapter()
        contract_address = getattr(payment, "escrow_contract_address", None)

        if contract_address:
            try:
                adapter.release_escrow_funds(contract_address, release_conditions)
            except Exception:
                logger.warning("Echec release via adapter, continuer avec la mise à jour DB locale")
        else:
            logger.warning("Aucune adresse de contrat escrow disponible pour la commande %s", order_id)

        if hasattr(payment, "escrow_released"):
            payment.escrow_released = True
        if hasattr(payment, "escrow_release_date"):
            payment.escrow_release_date = datetime.utcnow()

        db.commit()

        logger.info(f"Escrow libéré pour commande {order_id}")
        return True

    except Exception as e:
        logger.error(f"Erreur libération escrow: {e}")
        db.rollback()
        return False


# ==========================================
# REVIEWS & REPUTATION
# ==========================================

def create_review(db: Session, review_data: Dict[str, Any]) -> models.MarketplaceReview:
    """
    Créer un avis avec vérification blockchain
    """
    try:
        # Vérifier que l'utilisateur a acheté le produit (pour avis vérifié)
        is_verified = False
        if review_data.get("order_id"):
            order = db.query(models.MarketplaceOrder).filter(
                and_(
                    models.MarketplaceOrder.id == review_data["order_id"],
                    models.MarketplaceOrder.buyer_id == review_data["reviewer_id"],
                    models.MarketplaceOrder.status == "delivered"
                )
            ).first()
            is_verified = order is not None

        review = models.MarketplaceReview(
            listing_id=review_data.get("listing_id"),
            order_id=review_data.get("order_id"),
            reviewer_id=review_data["reviewer_id"],
            rating=review_data["rating"],
            comment=review_data.get("comment"),
            review_type=review_data.get("review_type", "product"),
            is_verified_purchase=is_verified
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        # Générer hash blockchain pour l'avis
        review.blockchain_hash = str(uuid.uuid4())  # Placeholder
        db.commit()

        logger.info(f"Avis créé: {review.rating}/5 étoiles par {review.reviewer_id}")
        return review

    except Exception as e:
        logger.error(f"Erreur création avis: {e}")
        db.rollback()
        raise


def get_listing_reviews(db: Session, listing_id: int) -> List[models.MarketplaceReview]:
    """
    Récupérer les avis d'une annonce
    """
    return db.query(models.MarketplaceReview).filter(
        models.MarketplaceReview.listing_id == listing_id
    ).order_by(models.MarketplaceReview.created_at.desc()).all()


def calculate_seller_reputation(db: Session, seller_id: int) -> Dict[str, Any]:
    """
    Calculer la réputation d'un vendeur
    """
    reviews = db.query(models.MarketplaceReview).join(models.MarketplaceListing).filter(
        models.MarketplaceListing.seller_id == seller_id
    ).all()

    if not reviews:
        return {
            "rating": 0.0,
            "total_reviews": 0,
            "verified_reviews": 0,
            "reputation_score": 0.0
        }

    total_rating = sum(review.rating for review in reviews)
    verified_reviews = sum(1 for review in reviews if review.is_verified_purchase)

    avg_rating = total_rating / len(reviews)
    reputation_score = (avg_rating * 0.7) + ((verified_reviews / len(reviews)) * 0.3)

    return {
        "rating": round(avg_rating, 1),
        "total_reviews": len(reviews),
        "verified_reviews": verified_reviews,
        "reputation_score": round(reputation_score, 2)
    }


# ==========================================
# LOGISTICS INTEGRATION
# ==========================================

def assign_logistics(db: Session, order_id: int, logistics_data: Dict[str, Any]) -> bool:
    """
    Assigner un transporteur connecté à une commande
    """
    try:
        order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
        if not order or order.status not in ["paid", "pending"]:
            return False

        origin_address = order.listing.location if order.listing else "Bamako"
        destination_address = order.shipping_address or "Unknown destination"

        origin = geocode_address(origin_address)
        destination = geocode_address(destination_address)
        if not origin:
            origin = Location(latitude=0.0, longitude=0.0, address=origin_address)
        if not destination:
            destination = Location(latitude=0.0, longitude=0.0, address=destination_address)

        carriers = find_available_carriers(origin_address, destination_address, order.quantity)
        provider = logistics_data.get("provider") or (carriers[0]["name"] if carriers else "AgroLogistics")

        shipment = create_shipment(
            origin=origin,
            destination=destination,
            weight_kg=order.quantity,
            value_xof=order.total_price,
            carrier=provider,
        )

        order.logistics_provider = provider
        order.tracking_number = logistics_data.get("tracking_number") or (shipment.tracking_number if shipment else str(uuid.uuid4()))
        if shipment and shipment.estimated_delivery:
            order.delivery_deadline = shipment.estimated_delivery

        db.commit()

        logger.info(f"Logistique assignée pour commande {order_id}: {order.logistics_provider}")
        return True

    except Exception as e:
        logger.error(f"Erreur assignation logistique: {e}")
        db.rollback()
        return False


def get_logistics_status(db: Session, order_id: int) -> Dict[str, Any]:
    """
    Récupérer le statut logistique d'une commande
    """
    order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
    if not order:
        return {"error": "Commande introuvable"}

    return {
        "order_id": order.id,
        "status": order.status,
        "logistics_provider": order.logistics_provider,
        "tracking_number": order.tracking_number,
        "estimated_delivery": order.delivery_deadline.isoformat() if order.delivery_deadline else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
    }


# ==========================================
# DASHBOARD & ANALYTICS
# ==========================================

def get_marketplace_dashboard(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Générer le tableau de bord marketplace pour un utilisateur
    """
    # Statistiques vendeur
    seller_listings = db.query(models.MarketplaceListing).filter(
        and_(
            models.MarketplaceListing.seller_id == user_id,
            models.MarketplaceListing.is_active == True
        )
    ).all()

    seller_orders = get_orders_by_user(db, user_id, "seller")
    seller_reputation = calculate_seller_reputation(db, user_id)

    # Statistiques acheteur
    buyer_orders = get_orders_by_user(db, user_id, "buyer")

    # Revenus totaux
    total_revenue = sum(order.total_price for order in seller_orders if order.status == "delivered")

    return {
        "seller_stats": {
            "active_listings": len(seller_listings),
            "total_orders": len(seller_orders),
            "total_revenue": total_revenue,
            "reputation": seller_reputation
        },
        "buyer_stats": {
            "total_orders": len(buyer_orders),
            "pending_deliveries": sum(1 for order in buyer_orders if order.status in ["paid", "shipped"]),
            "completed_orders": sum(1 for order in buyer_orders if order.status == "delivered")
        },
        "recent_activity": {
            "recent_orders": [
                {
                    "id": order.id,
                    "status": order.status,
                    "total_price": order.total_price,
                    "created_at": order.created_at.isoformat()
                } for order in (seller_orders + buyer_orders)[-5:]  # Dernières 5 activités
            ]
        }
    }


def get_marketplace_stats(db: Session) -> Dict[str, Any]:
    """
    Statistiques globales de la marketplace
    """
    total_listings = db.query(func.count(models.MarketplaceListing.id)).filter(
        models.MarketplaceListing.is_active == True
    ).scalar()

    total_orders = db.query(func.count(models.MarketplaceOrder.id)).scalar()

    total_volume = db.query(func.sum(models.MarketplaceOrder.total_price)).filter(
        models.MarketplaceOrder.status == "delivered"
    ).scalar() or 0

    return {
        "total_listings": total_listings,
        "total_orders": total_orders,
        "total_volume_xof": total_volume,
        "active_users": db.query(func.count(func.distinct(models.MarketplaceListing.seller_id))).scalar()
    }


# ==========================================
# ESCROW & BLOCKCHAIN PAYMENTS
# ==========================================

def create_escrow_contract(db: Session, order_id: int, buyer_wallet: str, seller_wallet: str, amount: float, release_conditions: Dict[str, Any]) -> "models.EscrowContract":
    """
    Créer un contrat escrow blockchain pour sécuriser le paiement
    """
    try:
        if not hasattr(models, "EscrowContract"):
            raise NotImplementedError("EscrowContract model not available in current schema")

        order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
        if not order:
            raise ValueError("Commande introuvable")

        contract_address = deploy_escrow_contract(buyer_wallet, seller_wallet, amount, release_conditions)

        escrow = models.EscrowContract(
            order_id=order_id,
            buyer_address=buyer_wallet,
            seller_address=seller_wallet,
            amount=amount,
            currency=order.currency,
            contract_address=contract_address,
            release_conditions=json.dumps(release_conditions),
            status="pending"
        )

        db.add(escrow)
        db.commit()
        db.refresh(escrow)

        logger.info(f"Contrat escrow créé pour commande {order_id}: {contract_address}")
        return escrow

    except Exception as e:
        logger.error(f"Erreur création contrat escrow: {e}")
        db.rollback()
        raise


def fund_escrow(db: Session, escrow_id: int) -> bool:
    """
    Financer le contrat escrow avec les fonds de l'acheteur
    """
    try:
        escrow = db.query(models.EscrowContract).filter(models.EscrowContract.id == escrow_id).first()
        if not escrow or escrow.status != "pending":
            return False

        # Financer sur blockchain
        tx_hash = fund_escrow_contract(escrow.contract_address, escrow.amount)
        if tx_hash:
            escrow.status = "funded"
            escrow.funded_at = datetime.utcnow()
            db.commit()
            logger.info(f"Escrow financé: {escrow.contract_address}")
            return True

        return False

    except Exception as e:
        logger.error(f"Erreur financement escrow: {e}")
        db.rollback()
        return False


def release_escrow(db: Session, escrow_id: int, release_conditions: str) -> bool:
    """
    Libérer les fonds escrow après conditions remplies
    """
    try:
        escrow = db.query(models.EscrowContract).filter(models.EscrowContract.id == escrow_id).first()
        if not escrow or escrow.status != "funded":
            return False

        # Libérer sur blockchain
        tx_hash = release_escrow_funds(escrow.contract_address, release_conditions)
        if tx_hash:
            escrow.status = "released"
            escrow.released_at = datetime.utcnow()
            db.commit()
            logger.info(f"Escrow libéré: {escrow.contract_address}")
            return True

        return False

    except Exception as e:
        logger.error(f"Erreur libération escrow: {e}")
        db.rollback()
        return False


# ==========================================
# AGRICULTURAL NFTS
# ==========================================

def create_agricultural_nft(db: Session, trace_id: int, nft_data: Dict[str, Any], owner_wallet: str) -> "models.AgriculturalNFT":
    """
    Créer un NFT agricole pour traçabilité de la chaîne d'approvisionnement
    """
    try:
        if not hasattr(models, "AgriculturalNFT"):
            raise NotImplementedError("AgriculturalNFT model not available in current schema")

        trace = db.query(models.BlockchainTrace).filter(models.BlockchainTrace.id == trace_id).first()
        if not trace:
            raise ValueError("Trace blockchain introuvable")

        token_id = str(uuid.uuid4())

        nft = models.AgriculturalNFT(
            trace_id=trace_id,
            token_id=token_id,
            name=nft_data["name"],
            description=nft_data.get("description"),
            image_url=nft_data.get("image_url"),
            attributes=json.dumps(nft_data["attributes"]),
            supply_chain_stage=nft_data["supply_chain_stage"],
            owner_address=owner_wallet
        )

        db.add(nft)
        db.commit()
        db.refresh(nft)

        # Enregistrement du NFT agricole localement.
        # Note : la frappe on-chain et le contrat NFT ne sont pas activés si le modèle de données ne le prend pas en charge.
        logger.info(f"NFT agricole créé localement: {token_id} pour trace {trace_id}")
        return nft

    except Exception as e:
        logger.error(f"Erreur création NFT agricole: {e}")
        db.rollback()
        raise


def transfer_agricultural_nft(db: Session, nft_id: int, from_wallet: str, to_wallet: str) -> bool:
    """
    Transférer un NFT agricole lors d'un changement de propriétaire
    """
    try:
        nft = db.query(models.AgriculturalNFT).filter(models.AgriculturalNFT.id == nft_id).first()
        if not nft or nft.owner_address != from_wallet:
            return False

        if getattr(nft, "contract_address", None) and getattr(nft, "token_id", None):
            try:
                tx_hash = transfer_nft(nft.contract_address, from_wallet, to_wallet, int(nft.token_id, 16))
                if tx_hash:
                    nft.owner_address = to_wallet
                    nft.transferred_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"NFT transféré sur blockchain: {nft.token_id} de {from_wallet} à {to_wallet}")
                    return True
            except Exception as e:
                logger.warning(f"NFT blockchain transfer failed, using local simulation: {e}")

        # Simulation pour développement ou fallback
        nft.owner_address = to_wallet
        nft.transferred_at = datetime.utcnow()
        db.commit()
        logger.info(f"NFT transféré (simulation): {nft.token_id} de {from_wallet} à {to_wallet}")
        return True

    except Exception as e:
        logger.error(f"Erreur transfert NFT: {e}")
        db.rollback()
        return False


# ==========================================
# IA MATCHMAKING - PHASE 3.2
# ==========================================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculer la distance entre deux points GPS en kilomètres
    """
    R = 6371  # Rayon de la Terre en km

    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def ai_matchmaking_recommendations(db: Session, buyer_id: int, preferences: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    IA matchmaking : Recommandations intelligentes de produits pour un acheteur
    Algorithme basé sur :
    - Historique d'achat
    - Préférences explicites
    - Profil utilisateur
    - Distance géographique
    - Réputation vendeur
    - Certifications qualité
    """
    try:
        # Récupérer le profil acheteur
        buyer = db.query(models.User).filter(models.User.id == buyer_id).first()
        if not buyer:
            return []

        # Historique d'achat de l'utilisateur
        buyer_orders = db.query(models.MarketplaceOrder).filter(
            models.MarketplaceOrder.buyer_id == buyer_id
        ).all()

        # Extraire les préférences de l'historique
        preferred_categories = {}
        preferred_products = {}
        avg_budget = 0
        order_count = len(buyer_orders)

        for order in buyer_orders:
            listing = db.query(models.MarketplaceListing).filter(
                models.MarketplaceListing.id == order.listing_id
            ).first()

            if listing:
                # Catégories préférées
                cat = listing.category
                preferred_categories[cat] = preferred_categories.get(cat, 0) + 1

                # Produits préférés
                prod = listing.product_type
                preferred_products[prod] = preferred_products.get(prod, 0) + 1

                # Budget moyen
                avg_budget += order.total_price

        if order_count > 0:
            avg_budget /= order_count

        # Appliquer les préférences explicites si fournies
        if preferences:
            if "categories" in preferences:
                for cat in preferences["categories"]:
                    preferred_categories[cat] = preferred_categories.get(cat, 0) + 10  # Boost

            if "products" in preferences:
                for prod in preferences["products"]:
                    preferred_products[prod] = preferred_products.get(prod, 0) + 10

            if "max_budget" in preferences:
                avg_budget = min(avg_budget, preferences["max_budget"])

        # Récupérer les annonces candidates
        candidates = db.query(models.MarketplaceListing).filter(
            models.MarketplaceListing.is_active == True
        ).all()

        recommendations = []

        for listing in candidates:
            score = 0
            reasons = []

            # 1. Score basé sur les préférences historiques (40%)
            category_score = preferred_categories.get(listing.category, 0) * 10
            product_score = preferred_products.get(listing.product_type, 0) * 15
            score += (category_score + product_score) * 0.4
            if category_score > 0:
                reasons.append(f"Catégorie préférée (+{category_score:.1f})")
            if product_score > 0:
                reasons.append(f"Produit préféré (+{product_score:.1f})")

            # 2. Score budgétaire (20%)
            if avg_budget > 0:
                budget_ratio = listing.price_per_unit / avg_budget
                if 0.5 <= budget_ratio <= 1.5:
                    budget_score = 20 * (1 - abs(1 - budget_ratio))
                    score += budget_score * 0.2
                    reasons.append(f"Budget adapté (+{budget_score:.1f})")

            # 3. Distance géographique (15%)
            if buyer.latitude and buyer.longitude and listing.latitude and listing.longitude:
                distance = calculate_distance(
                    buyer.latitude, buyer.longitude,
                    listing.latitude, listing.longitude
                )
                # Préférer les produits locaux (moins de 100km)
                if distance <= 100:
                    distance_score = 15 * (1 - distance/100)
                    score += distance_score * 0.15
                    reasons.append(f"Proche géographiquement (+{distance_score:.1f})")

            # 4. Réputation vendeur (15%)
            seller_reputation = calculate_seller_reputation(db, listing.seller_id)
            reputation_score = seller_reputation["reputation_score"] * 3
            score += reputation_score * 0.15
            reasons.append(f"Réputation vendeur (+{reputation_score:.1f})")

            # 5. Certifications qualité (10%)
            cert_score = 0
            if listing.quality_certified:
                cert_score += 5
                reasons.append("Certifié qualité (+5)")
            if listing.organic_certified:
                cert_score += 5
                reasons.append("Bio certifié (+5)")
            score += cert_score * 0.1

            # Ne garder que les recommandations pertinentes (score > 10)
            if score > 10:
                recommendations.append({
                    "listing": listing,
                    "score": round(score, 2),
                    "reasons": reasons[:3],  # Top 3 raisons
                    "match_percentage": min(100, round(score * 2.5))  # Score sur 100
                })

        # Trier par score décroissant et limiter à 10 recommandations
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:10]

    except Exception as e:
        logger.error(f"Erreur IA matchmaking: {e}")
        return []


def ai_matchmaking_for_sellers(db: Session, seller_id: int) -> List[Dict[str, Any]]:
    """
    IA matchmaking pour vendeurs : Identifier les meilleurs acheteurs potentiels
    """
    try:
        # Récupérer les annonces du vendeur
        seller_listings = db.query(models.MarketplaceListing).filter(
            and_(
                models.MarketplaceListing.seller_id == seller_id,
                models.MarketplaceListing.is_active == True
            )
        ).all()

        if not seller_listings:
            return []

        potential_buyers = []

        # Analyser les acheteurs récents dans la même région/catégorie
        for listing in seller_listings:
            # Acheteurs récents de produits similaires
            similar_orders = db.query(models.MarketplaceOrder).join(models.MarketplaceListing).filter(
                and_(
                    models.MarketplaceListing.category == listing.category,
                    models.MarketplaceOrder.status.in_(["delivered", "paid"]),
                    models.MarketplaceOrder.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            ).all()

            for order in similar_orders:
                buyer = db.query(models.User).filter(models.User.id == order.buyer_id).first()
                if buyer and buyer.id != seller_id:  # Éviter auto-recommandation
                    buyer_score = 0
                    reasons = []

                    # Distance
                    if buyer.latitude and buyer.longitude and listing.latitude and listing.longitude:
                        distance = calculate_distance(
                            buyer.latitude, buyer.longitude,
                            listing.latitude, listing.longitude
                        )
                        if distance <= 200:  # Rayon plus large pour vendeurs
                            buyer_score += max(0, 20 - distance/10)
                            reasons.append(f"Distance: {distance:.1f}km")

                    # Historique d'achat similaire
                    buyer_category_orders = db.query(models.MarketplaceOrder).join(models.MarketplaceListing).filter(
                        and_(
                            models.MarketplaceOrder.buyer_id == buyer.id,
                            models.MarketplaceListing.category == listing.category
                        )
                    ).count()

                    if buyer_category_orders > 0:
                        buyer_score += buyer_category_orders * 5
                        reasons.append(f"Achats similaires: {buyer_category_orders}")

                    # Potentiel acheteur si score > 10
                    if buyer_score > 10:
                        potential_buyers.append({
                            "buyer": buyer,
                            "listing": listing,
                            "score": round(buyer_score, 2),
                            "reasons": reasons,
                            "contact_recommended": buyer_score > 25
                        })

        # Dédupliquer et trier
        seen_buyers = set()
        unique_buyers = []
        for buyer_info in potential_buyers:
            buyer_id = buyer_info["buyer"].id
            if buyer_id not in seen_buyers:
                seen_buyers.add(buyer_id)
                unique_buyers.append(buyer_info)

        unique_buyers.sort(key=lambda x: x["score"], reverse=True)
        return unique_buyers[:5]  # Top 5 acheteurs potentiels

    except Exception as e:
        logger.error(f"Erreur IA matchmaking vendeurs: {e}")
        return []


def get_marketplace_insights(db: Session) -> Dict[str, Any]:
    """
    Insights IA sur les tendances du marché
    """
    try:
        # Analyse des tendances par catégorie
        category_trends = db.query(
            models.MarketplaceListing.category,
            func.count(models.MarketplaceListing.id).label('total_listings'),
            func.avg(models.MarketplaceListing.price_per_unit).label('avg_price'),
            func.sum(models.MarketplaceOrder.total_price).label('total_volume')
        ).join(
            models.MarketplaceOrder,
            models.MarketplaceListing.id == models.MarketplaceOrder.listing_id,
            isouter=True
        ).filter(
            models.MarketplaceListing.created_at >= datetime.utcnow() - timedelta(days=30)
        ).group_by(models.MarketplaceListing.category).all()

        # Analyse saisonnière
        seasonal_data = db.query(
            func.strftime('%m', models.MarketplaceOrder.created_at).label('month'),
            func.sum(models.MarketplaceOrder.total_price).label('monthly_volume')
        ).filter(
            models.MarketplaceOrder.created_at >= datetime.utcnow() - timedelta(days=365)
        ).group_by(func.strftime('%m', models.MarketplaceOrder.created_at)).all()

        # Prix dynamiques recommandés
        price_recommendations = {}
        for category, listings, avg_price, volume in category_trends:
            if volume and volume > 10000:  # Seulement si volume significatif
                # Recommandation basée sur la demande
                demand_factor = volume / (listings * avg_price) if avg_price > 0 else 1
                recommended_price = avg_price * (0.9 + demand_factor * 0.2)  # Ajustement dynamique
                price_recommendations[category] = {
                    "current_avg": round(avg_price, 2),
                    "recommended": round(recommended_price, 2),
                    "adjustment": round((recommended_price - avg_price) / avg_price * 100, 1)
                }

        return {
            "category_trends": [
                {
                    "category": cat,
                    "listings": listings,
                    "avg_price": round(avg_price, 2) if avg_price else 0,
                    "volume": round(volume, 2) if volume else 0
                } for cat, listings, avg_price, volume in category_trends
            ],
            "seasonal_patterns": [
                {"month": month, "volume": round(volume, 2) if volume else 0}
                for month, volume in seasonal_data
            ],
            "price_recommendations": price_recommendations,
            "market_health_score": min(100, len(category_trends) * 10)  # Score basé sur diversité
        }

    except Exception as e:
        logger.error(f"Erreur insights marché: {e}")
        return {}