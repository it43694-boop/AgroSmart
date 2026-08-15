"""
Endpoints Marketplace - Phase 2.3
À ajouter dans main.py
"""

import datetime
import logging
import os
import shutil
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Form, File, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])
logger = logging.getLogger("marketplace_endpoints")

# ==========================================
# MARKETPLACE ENDPOINTS - PHASE 2.3
# ==========================================

@router.post("/listings", response_model=Dict[str, Any])
def create_listing(
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form(...),
    product_type: str = Form(None),
    quantity: float = Form(...),
    unit: str = Form(...),
    price_per_unit: float = Form(...),
    location: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    images: List[UploadFile] = File(None),
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not product_type:
        product_type = category
    if not all([title, category, product_type, quantity, unit, price_per_unit]):
        raise HTTPException(status_code=400, detail="Champs obligatoires manquants pour créer un listing")

    if images is None:
        images = []

    if len(images) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 images autorisées.")

    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    uploaded_urls = []
    if images:
        upload_folder = os.path.join(os.path.dirname(__file__), "frontend", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        for upload in images:
            if upload.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Type de fichier non supporté: {upload.content_type}"
                )
            filename = os.path.basename(upload.filename or "")
            ext = os.path.splitext(filename)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Extension de fichier non supportée: {ext}"
                )

            upload.file.seek(0, os.SEEK_END)
            file_size = upload.file.tell()
            upload.file.seek(0)
            if file_size > 2 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"Taille de fichier trop élevée: {filename} ({file_size} octets). Maximum 2 Mo."
                )

            safe_name = f"{uuid.uuid4().hex}{ext}"
            destination_path = os.path.join(upload_folder, safe_name)
            try:
                with open(destination_path, "wb") as dest_file:
                    shutil.copyfileobj(upload.file, dest_file)
            finally:
                awaitable = getattr(upload.file, 'close', None)
                if callable(awaitable):
                    awaitable()
            uploaded_urls.append(f"/frontend/uploads/{safe_name}")

    try:
        images_str = ",".join(uploaded_urls) if uploaded_urls else None
        
        db_listing = models.MarketplaceListing(
            seller_id=current_user.id,
            title=title,
            description=description,
            category=category,
            product_type=product_type,
            quantity=quantity,
            unit=unit,
            price_per_unit=price_per_unit,
            location=location,
            latitude=latitude,
            longitude=longitude,
            images=images_str,
            currency="XOF",
            is_active=True,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        db.add(db_listing)
        db.commit()
        db.refresh(db_listing)

        logger.info(f"Listing créé: {db_listing.id} par vendeur {current_user.id}")

        return {
            "id": db_listing.id,
            "title": db_listing.title,
            "category": db_listing.category,
            "quantity": db_listing.quantity,
            "unit": db_listing.unit,
            "price_per_unit": db_listing.price_per_unit,
            "location": db_listing.location,
            "images": db_listing.images.split(',') if db_listing.images else [],
            "is_active": db_listing.is_active,
            "created_at": db_listing.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur création listing: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/listings", response_model=Dict[str, Any])
def list_marketplace_listings(
    category: str = Query(None),
    product_type: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lister les produits disponibles dans la marketplace.
    Endpoint pour les acheteurs avec filtrage.
    """
    try:
        query = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.is_active == True)

        if category:
            query = query.filter(models.MarketplaceListing.category == category)
        if product_type:
            query = query.filter(models.MarketplaceListing.product_type == product_type)

        total = query.count()
        listings = query.offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "listings": [
                {
                    "id": listing.id,
                    "title": listing.title,
                    "description": listing.description,
                    "category": listing.category,
                    "product_type": listing.product_type,
                    "quantity": listing.quantity,
                    "unit": listing.unit,
                    "price_per_unit": listing.price_per_unit,
                    "location": listing.location,
                    "seller_id": listing.seller_id,
                    "images": listing.images.split(",") if listing.images else [],
                    "is_verified": listing.is_verified,
                    "is_active": listing.is_active,
                    "created_at": listing.created_at.isoformat(),
                }
                for listing in listings
            ],
        }
    except Exception as e:
        logger.error(f"Erreur listing produits: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/seller/listings", response_model=Dict[str, Any])
def list_seller_listings(
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lister toutes les annonces du vendeur connecté (actives et inactives).
    """
    try:
        listings = db.query(models.MarketplaceListing).filter(
            models.MarketplaceListing.seller_id == current_user.id
        ).all()

        return {
            "total": len(listings),
            "listings": [
                {
                    "id": listing.id,
                    "title": listing.title,
                    "description": listing.description,
                    "category": listing.category,
                    "product_type": listing.product_type,
                    "quantity": listing.quantity,
                    "unit": listing.unit,
                    "price_per_unit": listing.price_per_unit,
                    "location": listing.location,
                    "seller_id": listing.seller_id,
                    "images": listing.images.split(',') if listing.images else [],
                    "is_verified": listing.is_verified,
                    "is_active": listing.is_active,
                    "created_at": listing.created_at.isoformat()
                }
                for listing in listings
            ]
        }
    except Exception as e:
        logger.error(f"Erreur listing produits: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.patch("/listings/{listing_id}/deactivate", response_model=Dict[str, Any])
def deactivate_listing(
    listing_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Désactiver une annonce (seul le vendeur peut désactiver son annonce).
    """
    try:
        listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing introuvable")
        
        logger.info(f"Tentative désactivation: listing_id={listing_id}, seller_id={listing.seller_id}, user_id={current_user.id}")
        
        if listing.seller_id != current_user.id:
            logger.error(f"Non autorisé: seller_id={listing.seller_id} != user_id={current_user.id}")
            raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à désactiver cette annonce")
        
        listing.is_active = False
        db.commit()
        db.refresh(listing)
        
        logger.info(f"Annonce désactivée: listing_id={listing_id}")
        return {
            "success": True,
            "message": "Annonce désactivée avec succès",
            "listing_id": listing.id,
            "is_active": listing.is_active
        }
    except Exception as e:
        logger.error(f"Erreur désactivation listing: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.patch("/listings/{listing_id}/activate", response_model=Dict[str, Any])
def activate_listing(
    listing_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Réactiver une annonce (seul le vendeur peut réactiver son annonce).
    """
    try:
        listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing introuvable")
        
        logger.info(f"Tentative réactivation: listing_id={listing_id}, seller_id={listing.seller_id}, user_id={current_user.id}")
        
        if listing.seller_id != current_user.id:
            logger.error(f"Non autorisé: seller_id={listing.seller_id} != user_id={current_user.id}")
            raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à réactiver cette annonce")
        
        listing.is_active = True
        db.commit()
        db.refresh(listing)
        
        logger.info(f"Annonce réactivée: listing_id={listing_id}")
        return {
            "success": True,
            "message": "Annonce réactivée avec succès",
            "listing_id": listing.id,
            "is_active": listing.is_active
        }
    except Exception as e:
        logger.error(f"Erreur réactivation listing: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.delete("/listings/{listing_id}", response_model=Dict[str, Any])
def delete_listing(
    listing_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer une annonce définitivement (seul le vendeur peut supprimer son annonce).
    """
    try:
        listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing introuvable")
        
        logger.info(f"Tentative suppression: listing_id={listing_id}, seller_id={listing.seller_id}, user_id={current_user.id}")
        
        if listing.seller_id != current_user.id:
            logger.error(f"Non autorisé: seller_id={listing.seller_id} != user_id={current_user.id}")
            raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à supprimer cette annonce")
        
        db.delete(listing)
        db.commit()
        
        logger.info(f"Annonce supprimée: listing_id={listing_id}")
        return {
            "success": True,
            "message": "Annonce supprimée avec succès",
            "listing_id": listing_id
        }
    except Exception as e:
        logger.error(f"Erreur suppression listing: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/listings/{listing_id}", response_model=Dict[str, Any])
def get_listing_details(
    listing_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer les détails d'un listing spécifique.
    Inclut l'historique des reviews et des commandes.
    """
    try:
        listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing introuvable")

        seller = db.query(models.User).filter(models.User.id == listing.seller_id).first()

        reviews = db.query(models.MarketplaceReview).filter(
            models.MarketplaceReview.listing_id == listing_id
        ).all()

        avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0

        return {
            "id": listing.id,
            "title": listing.title,
            "description": listing.description,
            "category": listing.category,
            "product_type": listing.product_type,
            "quantity": listing.quantity,
            "unit": listing.unit,
            "price_per_unit": listing.price_per_unit,
            "location": listing.location,
            "latitude": listing.latitude,
            "longitude": listing.longitude,
            "images": listing.images.split(',') if listing.images else [],
            "seller": {
                "id": seller.id,
                "username": seller.full_name,
                "email": seller.email
            } if seller else None,
            "is_verified": listing.is_verified,
            "quality_certified": listing.quality_certified,
            "organic_certified": listing.organic_certified,
            "reviews_count": len(reviews),
            "average_rating": round(avg_rating, 1),
            "created_at": listing.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération listing: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/orders", response_model=Dict[str, Any])
def create_order(
    payload: Dict[str, Any] = Body(...),
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing_id = payload.get("listing_id")
    quantity = payload.get("quantity")
    shipping_address = payload.get("shipping_address")
    payment_method = payload.get("payment_method")

    if listing_id is None or quantity is None or not shipping_address:
        raise HTTPException(status_code=400, detail="listing_id, quantity et shipping_address sont requis")
    """
    Créer une nouvelle commande.
    Endpoint pour les acheteurs.
    """
    try:
        listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing introuvable")

        if quantity > listing.quantity:
            raise HTTPException(status_code=400, detail="Quantité insuffisante disponible")

        total_price = quantity * listing.price_per_unit

        db_order = models.MarketplaceOrder(
            listing_id=listing_id,
            buyer_id=current_user.id,
            quantity=quantity,
            total_price=total_price,
            currency="XOF",
            payment_method=payment_method,
            status="pending",
            shipping_address=shipping_address,
            created_at=datetime.datetime.utcnow()
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        logger.info(f"Commande créée: {db_order.id} par acheteur {current_user.id}")

        return {
            "id": db_order.id,
            "listing_id": db_order.listing_id,
            "quantity": db_order.quantity,
            "total_price": db_order.total_price,
            "currency": db_order.currency,
            "status": db_order.status,
            "shipping_address": db_order.shipping_address,
            "created_at": db_order.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création commande: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/orders/{order_id}/pay", response_model=Dict[str, Any])
def pay_order(
    order_id: int,
    payload: Dict[str, Any] = Body(...),
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment_method = payload.get("payment_method")
    payment_provider = payload.get("payment_provider")
    transaction_id = payload.get("transaction_id")
    amount = payload.get("amount")

    if not payment_method or amount is None:
        raise HTTPException(status_code=400, detail="payment_method et amount sont requis")
    if not payment_provider:
        raise HTTPException(status_code=400, detail="payment_provider est requis")
    if payment_method != "cash_on_delivery" and not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id est requis pour ce mode de paiement")

    try:
        order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Commande introuvable")

        if order.buyer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Accès refusé")

        if order.status != "pending":
            raise HTTPException(status_code=400, detail="Commande déjà payée ou invalidée")

        if float(amount) != float(order.total_price):
            raise HTTPException(status_code=400, detail="Montant de paiement incorrect")

        payment = models.MarketplacePayment(
            order_id=order_id,
            amount=order.total_price,
            currency=order.currency,
            payment_method=payment_method,
            payment_provider=payment_provider,
            transaction_id=transaction_id,
            status="completed",
            blockchain_tx_hash=str(uuid.uuid4()),
            created_at=datetime.datetime.utcnow(),
            processed_at=datetime.datetime.utcnow()
        )

        db.add(payment)
        order.status = "paid"
        order.updated_at = datetime.datetime.utcnow()
        order.blockchain_hash = payment.blockchain_tx_hash
        db.commit()
        db.refresh(payment)

        return {
            "id": payment.id,
            "order_id": payment.order_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_provider": payment.payment_provider,
            "transaction_id": payment.transaction_id,
            "status": payment.status,
            "blockchain_tx_hash": payment.blockchain_tx_hash,
            "processed_at": payment.processed_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur paiement commande: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/orders/{order_id}", response_model=Dict[str, Any])
def get_order_details(
    order_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les détails d'une commande.
    Seulement accessible par l'acheteur ou le vendeur.
    """
    try:
        order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Commande introuvable")

        # Vérifier les permissions
        if order.buyer_id != current_user.id and order.listing.seller_id != current_user.id:
            raise HTTPException(status_code=403, detail="Accès refusé")

        listing = order.listing
        buyer = db.query(models.User).filter(models.User.id == order.buyer_id).first()
        seller = db.query(models.User).filter(models.User.id == listing.seller_id).first()
        payment = db.query(models.MarketplacePayment).filter(models.MarketplacePayment.order_id == order.id).order_by(models.MarketplacePayment.created_at.desc()).first()

        payment_data = None
        if payment:
            payment_data = {
                "id": payment.id,
                "amount": payment.amount,
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_provider": payment.payment_provider,
                "transaction_id": payment.transaction_id,
                "status": payment.status,
                "blockchain_tx_hash": payment.blockchain_tx_hash,
                "processed_at": payment.processed_at.isoformat() if payment.processed_at else None
            }

        return {
            "id": order.id,
            "listing": {
                "id": listing.id,
                "title": listing.title,
                "product_type": listing.product_type,
                "quantity_available": listing.quantity
            },
            "buyer": {
                "id": buyer.id,
                "username": buyer.full_name or buyer.email
            },
            "seller": {
                "id": seller.id,
                "username": seller.full_name or seller.email
            },
            "quantity": order.quantity,
            "total_price": order.total_price,
            "currency": order.currency,
            "status": order.status,
            "shipping_address": order.shipping_address,
            "payment_method": order.payment_method,
            "payment": payment_data,
            "created_at": order.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération commande: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/reviews", response_model=Dict[str, Any])
def create_review(
    payload: Dict[str, Any] = Body(...),
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing_id = payload.get("listing_id")
    order_id = payload.get("order_id")
    rating = payload.get("rating")
    comment = payload.get("comment")
    review_type = payload.get("review_type", "product")

    if rating is None or comment is None:
        raise HTTPException(status_code=400, detail="rating et comment sont requis")
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="rating doit être entre 1 et 5")
    """
    Créer une review pour un produit ou une commande.
    Seuls les acheteurs ayant acheté peuvent reviewer.
    """
    try:
        if not listing_id and not order_id:
            raise HTTPException(status_code=400, detail="listing_id ou order_id requis")

        # Vérifier que c'est un achat vérifié
        if order_id:
            order = db.query(models.MarketplaceOrder).filter(models.MarketplaceOrder.id == order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Commande introuvable")
            if order.buyer_id != current_user.id:
                raise HTTPException(status_code=403, detail="Accès refusé")
            listing_id = order.listing_id
            is_verified = order.status in ["delivered", "paid"]
        else:
            is_verified = False

        db_review = models.MarketplaceReview(
            listing_id=listing_id,
            order_id=order_id,
            reviewer_id=current_user.id,
            rating=rating,
            comment=comment,
            review_type=review_type,
            is_verified_purchase=is_verified,
            created_at=datetime.datetime.utcnow()
        )
        db.add(db_review)
        db.commit()
        db.refresh(db_review)

        logger.info(f"Review créée: {db_review.id} par {current_user.id}")

        return {
            "id": db_review.id,
            "listing_id": db_review.listing_id,
            "order_id": db_review.order_id,
            "rating": db_review.rating,
            "comment": db_review.comment,
            "review_type": db_review.review_type,
            "is_verified_purchase": db_review.is_verified_purchase,
            "created_at": db_review.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création review: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/listings/{listing_id}/reviews", response_model=List[Dict[str, Any]])
def get_listing_reviews(
    listing_id: int,
    db: Session = Depends(get_db)
):
    try:
        listing = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Annonce introuvable")

        reviews = db.query(models.MarketplaceReview).filter(
            models.MarketplaceReview.listing_id == listing_id
        ).order_by(models.MarketplaceReview.created_at.desc()).all()

        return [
            {
                "id": review.id,
                "listing_id": review.listing_id,
                "order_id": review.order_id,
                "rating": review.rating,
                "comment": review.comment,
                "review_type": review.review_type,
                "is_verified_purchase": review.is_verified_purchase,
                "reviewer_id": review.reviewer_id,
                "reviewer_name": review.reviewer.full_name if review.reviewer and getattr(review.reviewer, 'full_name', None) else getattr(review.reviewer, 'username', 'Anonyme'),
                "created_at": review.created_at.isoformat()
            }
            for review in reviews
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération avis listing: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/reviews/user", response_model=List[Dict[str, Any]])
def get_user_reviews(
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        reviews = db.query(models.MarketplaceReview).filter(
            models.MarketplaceReview.reviewer_id == current_user.id
        ).order_by(models.MarketplaceReview.created_at.desc()).all()

        return [
            {
                "id": review.id,
                "listing_id": review.listing_id,
                "listing_title": review.listing.title if review.listing else 'N/A',
                "seller_id": review.listing.seller_id if review.listing else None,
                "seller_name": review.listing.seller.full_name if review.listing and review.listing.seller else 'N/A',
                "order_id": review.order_id,
                "rating": review.rating,
                "comment": review.comment,
                "review_type": review.review_type,
                "is_verified_purchase": review.is_verified_purchase,
                "created_at": review.created_at.isoformat()
            }
            for review in reviews
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération avis utilisateur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/seller/{seller_id}/stats", response_model=Dict[str, Any])
def get_seller_stats(
    seller_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques d'un vendeur.
    Reputation score basé sur les reviews et les commandes.
    """
    try:
        seller = db.query(models.User).filter(models.User.id == seller_id).first()
        if not seller:
            raise HTTPException(status_code=404, detail="Vendeur introuvable")

        listings = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.seller_id == seller_id).all()
        total_listings = len(listings)

        orders = db.query(models.MarketplaceOrder).join(
            models.MarketplaceListing
        ).filter(models.MarketplaceListing.seller_id == seller_id).all()
        total_orders = len(orders)

        reviews = db.query(models.MarketplaceReview).filter(
            models.MarketplaceReview.listing_id.in_([l.id for l in listings])
        ).all()

        avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0

        # Reputation score = moyenne + facteurs (commandes, verified reviews)
        reputation_score = avg_rating * 20  # Base 0-100
        reputation_score += min(20, total_orders * 2)  # Bonus pour commandes
        reputation_score += len([r for r in reviews if r.is_verified_purchase]) * 0.5

        total_revenue = sum([o.total_price for o in orders if o.status in ["paid", "delivered"]])

        return {
            "seller_id": seller_id,
            "username": seller.full_name,
            "total_listings": total_listings,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_rating": round(avg_rating, 1),
            "total_reviews": len(reviews),
            "verified_reviews": len([r for r in reviews if r.is_verified_purchase]),
            "reputation_score": round(reputation_score, 1),
            "quality_certified": sum([1 for l in listings if l.quality_certified]),
            "organic_certified": sum([1 for l in listings if l.organic_certified])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur stats vendeur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/sellers/{seller_id}", response_model=Dict[str, Any])
def get_seller_profile(
    seller_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer le profil complet d'un vendeur avec réputation.
    """
    try:
        seller = db.query(models.User).filter(models.User.id == seller_id).first()
        if not seller:
            raise HTTPException(status_code=404, detail="Vendeur introuvable")

        listings = db.query(models.MarketplaceListing).filter(models.MarketplaceListing.seller_id == seller_id).all()
        orders = db.query(models.MarketplaceOrder).join(
            models.MarketplaceListing
        ).filter(models.MarketplaceListing.seller_id == seller_id).all()
        
        reviews = db.query(models.MarketplaceReview).filter(
            models.MarketplaceReview.listing_id.in_([l.id for l in listings])
        ).all()

        avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0
        reputation_score = avg_rating * 20 + min(20, len(orders) * 2) + len([r for r in reviews if r.is_verified_purchase]) * 0.5

        total_revenue = sum([o.total_price for o in orders if o.status in ["paid", "delivered"]])

        # Récupérer les avis récents du vendeur
        recent_reviews = sorted(reviews, key=lambda x: x.created_at, reverse=True)[:5]

        return {
            "id": seller.id,
            "full_name": seller.full_name,
            "email": seller.email,
            "region": seller.region,
            "total_listings": len(listings),
            "active_listings": len([l for l in listings if l.is_active]),
            "total_orders": len(orders),
            "completed_orders": len([o for o in orders if o.status == "delivered"]),
            "total_revenue": round(total_revenue, 2),
            "average_rating": round(avg_rating, 1),
            "total_reviews": len(reviews),
            "verified_reviews": len([r for r in reviews if r.is_verified_purchase]),
            "reputation_score": round(min(reputation_score, 100), 1),
            "quality_certified_products": len([l for l in listings if l.quality_certified]),
            "organic_certified_products": len([l for l in listings if l.organic_certified]),
            "member_since": seller.id,  # Placeholder
            "recent_reviews": [
                {
                    "id": r.id,
                    "rating": r.rating,
                    "comment": r.comment,
                    "reviewer_id": r.reviewer_id,
                    "created_at": r.created_at.isoformat()
                }
                for r in recent_reviews
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur profil vendeur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/sellers/{seller_id}/contact", response_model=Dict[str, Any])
def contact_seller(
    seller_id: int,
    payload: Dict[str, Any] = Body(...),
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Envoyer un message de contact au vendeur.
    """
    try:
        seller = db.query(models.User).filter(models.User.id == seller_id).first()
        if not seller:
            raise HTTPException(status_code=404, detail="Vendeur introuvable")

        message_text = payload.get("message")
        subject = payload.get("subject", "Demande d'information")

        if not message_text or len(message_text) < 10:
            raise HTTPException(status_code=400, detail="Le message doit contenir au moins 10 caractères")

        logger.info(f"Message de contact: {current_user.id} -> {seller_id}: {subject}")

        return {
            "status": "success",
            "message": "Votre message a été envoyé au vendeur. Il vous contactera sous peu.",
            "seller_email": seller.email,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur envoi message vendeur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
