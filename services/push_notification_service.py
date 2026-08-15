"""
Service de Notifications Push pour AgroSmart
Utilise Firebase Cloud Messaging (FCM) pour les notifications push
"""

import os
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger("push_notification_service")

try:
    from firebase_admin import credentials, messaging, initialize_app
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase Admin SDK non disponible. pip install firebase-admin")

class PushNotificationService:
    def __init__(self):
        self.app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialise Firebase Admin SDK"""
        if not FIREBASE_AVAILABLE:
            return
        
        try:
            firebase_key_path = os.getenv("FIREBASE_KEY_PATH")
            if firebase_key_path and os.path.exists(firebase_key_path):
                cred = credentials.Certificate(firebase_key_path)
                self.app = initialize_app(cred)
                logger.info("Firebase initialisé avec succès")
            else:
                firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
                if firebase_key_json:
                    cred_dict = json.loads(firebase_key_json)
                    cred = credentials.Certificate(cred_dict)
                    self.app = initialize_app(cred)
                    logger.info("Firebase initialisé avec clé JSON")
        except Exception as e:
            logger.error(f"Erreur initialisation Firebase: {e}")
    
    async def send_notification(self, token: str, title: str, body: str, data: Optional[Dict] = None) -> Dict:
        """Envoie une notification push à un appareil"""
        if not FIREBASE_AVAILABLE:
            return {"success": False, "error": "Firebase non disponible"}
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                token=token,
                data=data or {}
            )
            
            response = messaging.send(message)
            return {
                "success": True,
                "message_id": response
            }
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_multicast_notification(self, tokens: List[str], title: str, body: str, data: Optional[Dict] = None) -> Dict:
        """Envoie une notification push à plusieurs appareils"""
        if not FIREBASE_AVAILABLE:
            return {"success": False, "error": "Firebase non disponible"}
        
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                tokens=tokens,
                data=data or {}
            )
            
            response = messaging.send_multicast(message)
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "responses": response-responses
            }
        except Exception as e:
            logger.error(f"Erreur envoi multicast: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_to_topic(self, topic: str, title: str, body: str, data: Optional[Dict] = None) -> Dict:
        """Envoie une notification push à un topic"""
        if not FIREBASE_AVAILABLE:
            return {"success": False, "error": "Firebase non disponible"}
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                topic=topic,
                data=data or {}
            )
            
            response = messaging.send(message)
            return {
                "success": True,
                "message_id": response
            }
        except Exception as e:
            logger.error(f"Erreur envoi topic: {e}")
            return {"success": False, "error": str(e)}
    
    async def subscribe_to_topic(self, tokens: List[str], topic: str) -> Dict:
        """Abonne des tokens à un topic"""
        if not FIREBASE_AVAILABLE:
            return {"success": False, "error": "Firebase non disponible"}
        
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }
        except Exception as e:
            logger.error(f"Erreur abonnement topic: {e}")
            return {"success": False, "error": str(e)}
    
    async def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> Dict:
        """Désabonne des tokens d'un topic"""
        if not FIREBASE_AVAILABLE:
            return {"success": False, "error": "Firebase non disponible"}
        
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }
        except Exception as e:
            logger.error(f"Erreur désabonnement topic: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_order_notification(self, token: str, order_id: int, status: str) -> Dict:
        """Envoie une notification de commande"""
        messages = {
            "confirmed": "Commande confirmée",
            "shipped": "Commande expédiée",
            "delivered": "Commande livrée",
            "cancelled": "Commande annulée"
        }
        
        title = "Mise à jour de commande"
        body = messages.get(status, f"Commande #{order_id}: {status}")
        
        return await self.send_notification(token, title, body, {"order_id": str(order_id), "status": status})
    
    async def send_weather_alert(self, token: str, region: str, alert_type: str) -> Dict:
        """Envoie une alerte météo"""
        title = "Alerte Météo"
        body = f"Alerte {alert_type} pour la région {region}"
        
        return await self.send_notification(token, title, body, {"region": region, "alert_type": alert_type})
    
    async def send_loan_notification(self, token: str, loan_id: int, status: str) -> Dict:
        """Envoie une notification de prêt"""
        messages = {
            "approved": "Prêt approuvé",
            "rejected": "Prêt refusé",
            "pending": "Prêt en attente"
        }
        
        title = "Mise à jour de prêt"
        body = messages.get(status, f"Prêt #{loan_id}: {status}")
        
        return await self.send_notification(token, title, body, {"loan_id": str(loan_id), "status": status})

push_notification_service = PushNotificationService()
