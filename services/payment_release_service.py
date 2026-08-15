"""
Service de libération de paiement pour les vendeurs
Gère le transfert des fonds de l'escrow vers le vendeur après confirmation de livraison
"""

import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from models import User, MarketplaceOrder, MarketplaceTransaction, FinanceRecord
import datetime

logger = logging.getLogger("payment_release_service")

class PaymentReleaseService:
    def __init__(self):
        self.platform_fee_percentage = 0.05  # 5% de frais de plateforme
    
    def release_payment_to_seller(self, db: Session, order_id: int) -> Dict:
        """
        Libère le paiement au vendeur après confirmation de livraison
        """
        try:
            order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id).first()
            if not order:
                return {"success": False, "error": "Commande introuvable"}
            
            if order.status != "delivered":
                return {"success": False, "error": "La commande doit être livrée avant libération"}
            
            if order.payment_released:
                return {"success": False, "error": "Paiement déjà libéré"}
            
            # Calculer le montant après frais de plateforme
            platform_fee = order.total_price * self.platform_fee_percentage
            seller_amount = order.total_price - platform_fee
            
            # Créer la transaction marketplace
            transaction = MarketplaceTransaction(
                seller_id=order.listing.seller_id,
                buyer_id=order.buyer_id,
                amount=seller_amount,
                currency=order.currency,
                status="completed",
                description=f"Paiement pour commande #{order.id}",
                created_at=datetime.datetime.utcnow()
            )
            
            db.add(transaction)
            
            # Créer un enregistrement financier pour le vendeur
            finance_record = FinanceRecord(
                owner_id=order.listing.seller_id,
                revenue=seller_amount,
                cost=0,
                date=datetime.datetime.utcnow()
            )
            
            db.add(finance_record)
            
            # Marquer la commande comme paiement libéré
            order.payment_released = True
            order.payment_released_at = datetime.datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Paiement libéré: Order {order_id}, Seller {order.listing.seller_id}, Amount {seller_amount}")
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "seller_amount": seller_amount,
                "platform_fee": platform_fee,
                "total_amount": order.total_price
            }
            
        except Exception as e:
            logger.error(f"Erreur libération paiement: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    def confirm_delivery(self, db: Session, order_id: int, buyer_id: int) -> Dict:
        """
        Confirme la livraison d'une commande (par l'acheteur)
        """
        try:
            order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id).first()
            if not order:
                return {"success": False, "error": "Commande introuvable"}
            
            if order.buyer_id != buyer_id:
                return {"success": False, "error": "Seul l'acheteur peut confirmer la livraison"}
            
            if order.status != "shipped":
                return {"success": False, "error": "La commande doit être expédiée avant confirmation"}
            
            # Marquer comme livrée
            order.status = "delivered"
            order.delivered_at = datetime.datetime.utcnow()
            
            db.commit()
            
            # Libérer automatiquement le paiement
            release_result = self.release_payment_to_seller(db, order_id)
            
            return {
                "success": True,
                "order_status": order.status,
                "payment_released": release_result.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Erreur confirmation livraison: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    def get_seller_balance(self, db: Session, seller_id: int) -> Dict:
        """
        Calcule le solde disponible du vendeur
        """
        try:
            # Somme des revenus des transactions
            transactions = db.query(MarketplaceTransaction).filter(
                MarketplaceTransaction.seller_id == seller_id,
                MarketplaceTransaction.status == "completed"
            ).all()
            
            total_revenue = sum(t.amount for t in transactions)
            
            # Records financiers
            finance_records = db.query(FinanceRecord).filter(
                FinanceRecord.owner_id == seller_id
            ).all()
            
            total_finance_revenue = sum(r.revenue for r in finance_records)
            total_finance_cost = sum(r.cost for r in finance_records)
            
            return {
                "total_revenue": total_revenue,
                "transaction_count": len(transactions),
                "finance_revenue": total_finance_revenue,
                "finance_cost": total_finance_cost,
                "net_balance": total_finance_revenue - total_finance_cost
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul solde vendeur: {e}")
            return {"success": False, "error": str(e)}
    
    def get_seller_payment_history(self, db: Session, seller_id: int, limit: int = 20) -> Dict:
        """
        Récupère l'historique des paiements du vendeur
        """
        try:
            transactions = db.query(MarketplaceTransaction).filter(
                MarketplaceTransaction.seller_id == seller_id
            ).order_by(MarketplaceTransaction.created_at.desc()).limit(limit).all()
            
            history = []
            for t in transactions:
                history.append({
                    "id": t.id,
                    "amount": t.amount,
                    "currency": t.currency,
                    "status": t.status,
                    "description": t.description,
                    "created_at": t.created_at.isoformat()
                })
            
            return {
                "success": True,
                "transactions": history,
                "total": len(history)
            }
            
        except Exception as e:
            logger.error(f"Erreur historique paiements: {e}")
            return {"success": False, "error": str(e)}

payment_release_service = PaymentReleaseService()
