"""
Service SMS/USSD pour zones hors-ligne
Permet l'accès à AgroSmart via SMS et USSD pour les zones sans internet
"""

import os
import logging
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from models import User
import json

logger = logging.getLogger("sms_ussd_service")

class SMSService:
    def __init__(self):
        self.sms_provider = os.getenv("SMS_PROVIDER", "twilio")
        self.sms_api_key = os.getenv("SMS_API_KEY", "")
        self.sms_api_secret = os.getenv("SMS_API_SECRET", "")
        self.sms_sender_id = os.getenv("SMS_SENDER_ID", "AgroSmart")
    
    def send_sms(self, phone_number: str, message: str) -> Dict:
        """Envoie un SMS"""
        if self.sms_provider == "twilio":
            return self._send_twilio_sms(phone_number, message)
        elif self.sms_provider == "africastalking":
            return self._send_africastalking_sms(phone_number, message)
        else:
            return self._send_mock_sms(phone_number, message)
    
    def _send_twilio_sms(self, phone_number: str, message: str) -> Dict:
        """Envoie SMS via Twilio"""
        try:
            from twilio.rest import Client
            client = Client(self.sms_api_key, self.sms_api_secret)
            
            message_obj = client.messages.create(
                body=message,
                from_=self.sms_sender_id,
                to=phone_number
            )
            
            return {
                "success": True,
                "message_id": message_obj.sid,
                "provider": "twilio"
            }
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_africastalking_sms(self, phone_number: str, message: str) -> Dict:
        """Envoie SMS via Africa's Talking"""
        try:
            import africastalking
            
            africastalking.initialize(
                username=self.sms_api_key,
                api_key=self.sms_api_secret
            )
            
            sms = africastalking.SMS
            response = sms.send(message, [phone_number], sender_id=self.sms_sender_id)
            
            return {
                "success": True,
                "message_id": response.get("SMSMessageData", {}).get("Recipients", [{}])[0].get("messageId"),
                "provider": "africastalking"
            }
        except Exception as e:
            logger.error(f"Africa's Talking SMS failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_mock_sms(self, phone_number: str, message: str) -> Dict:
        """Simulation SMS pour développement"""
        logger.info(f"[MOCK SMS] To: {phone_number}, Message: {message}")
        return {
            "success": True,
            "message_id": f"mock_{hash(message)}",
            "provider": "mock"
        }

class USSDService:
    def __init__(self):
        self.ussd_code = os.getenv("USSD_CODE", "*123#")
        self.session_timeout = 120
    
    def process_ussd_request(self, session_id: str, phone_number: str, user_input: str, db: Session) -> Dict:
        """Traite une requête USSD"""
        session = self._get_session(session_id)
        
        if not session:
            session = self._create_session(session_id, phone_number)
            return self._handle_main_menu(session)
        
        if user_input == "":
            return self._handle_main_menu(session)
        
        current_screen = session.get("screen", "main")
        
        if current_screen == "main":
            return self._handle_main_menu_selection(session, user_input, db)
        elif current_screen == "marketplace":
            return self._handle_marketplace(session, user_input, db)
        elif current_screen == "weather":
            return self._handle_weather(session, user_input, db)
        elif current_screen == "orders":
            return self._handle_orders(session, user_input, db)
        elif current_screen == "balance":
            return self._handle_balance(session, user_input, db)
        
        return self._handle_main_menu(session)
    
    def _handle_main_menu(self, session: Dict) -> Dict:
        """Affiche le menu principal USSD"""
        session["screen"] = "main"
        
        response = f"CON AgroSmart\n"
        response += "1. Marketplace\n"
        response += "2. Météo\n"
        response += "3. Mes Commandes\n"
        response += "4. Solde\n"
        response += "5. Aide"
        
        return {"response": response, "session": session}
    
    def _handle_main_menu_selection(self, session: Dict, user_input: str, db: Session) -> Dict:
        """Traite la sélection du menu principal"""
        if user_input == "1":
            session["screen"] = "marketplace"
            return self._handle_marketplace(session, "", db)
        elif user_input == "2":
            session["screen"] = "weather"
            return self._handle_weather(session, "", db)
        elif user_input == "3":
            session["screen"] = "orders"
            return self._handle_orders(session, "", db)
        elif user_input == "4":
            session["screen"] = "balance"
            return self._handle_balance(session, "", db)
        elif user_input == "5":
            return {"response": "END Appelez le support: +221 77 123 45 67", "session": session}
        else:
            return self._handle_main_menu(session)
    
    def _handle_marketplace(self, session: Dict, user_input: str, db: Session) -> Dict:
        """Gère la section marketplace"""
        if user_input == "":
            response = "CON Marketplace\n"
            response += "1. Rechercher produit\n"
            response += "2. Mes annonces\n"
            response += "3. Retour"
            return {"response": response, "session": session}
        elif user_input == "1":
            response = "CON Entrez le nom du produit:"
            session["screen"] = "marketplace_search"
            return {"response": response, "session": session}
        elif user_input == "3":
            return self._handle_main_menu(session)
        else:
            return self._handle_marketplace(session, "", db)
    
    def _handle_weather(self, session: Dict, user_input: str, db: Session) -> Dict:
        """Gère la section météo"""
        if user_input == "":
            response = "CON Météo\n"
            response += "Entrez votre région (ex: Dakar, Bamako):"
            session["screen"] = "weather_region"
            return {"response": response, "session": session}
        else:
            region = user_input
            weather_data = self._get_weather_for_region(region)
            response = f"END Météo {region}:\n{weather_data}"
            return {"response": response, "session": session}
    
    def _handle_orders(self, session: Dict, user_input: str, db: Session) -> Dict:
        """Gère la section commandes"""
        phone_number = session.get("phone_number")
        user = db.query(User).filter(User.phone == phone_number).first()
        
        if not user:
            response = "END Utilisateur non trouvé. Contactez le support."
            return {"response": response, "session": session}
        
        orders_count = len(user.marketplace_transactions)
        response = f"END Vous avez {orders_count} commandes.\nDétails sur l'app."
        
        return {"response": response, "session": session}
    
    def _handle_balance(self, session: Dict, user_input: str, db: Session) -> Dict:
        """Gère la section solde"""
        phone_number = session.get("phone_number")
        user = db.query(User).filter(User.phone == phone_number).first()
        
        if not user:
            response = "END Utilisateur non trouvé."
            return {"response": response, "session": session}
        
        total_revenue = sum(record.revenue for record in user.finance_records)
        total_cost = sum(record.cost for record in user.finance_records)
        balance = total_revenue - total_cost
        
        response = f"END Solde: {balance:.2f} XOF"
        return {"response": response, "session": session}
    
    def _get_weather_for_region(self, region: str) -> str:
        """Récupère les données météo pour une région"""
        try:
            import requests
            weather_url = "https://api.open-meteo.com/v1/forecast"
            
            coords = self._get_region_coordinates(region)
            if not coords:
                return "Données non disponibles pour cette région."
            
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "current_weather": "true"
            }
            
            response = requests.get(weather_url, params=params, timeout=5)
            if response.ok:
                data = response.json()
                temp = data.get("current_weather", {}).get("temperature", "N/A")
                return f"Température: {temp}°C"
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
        
        return "Données météo indisponibles."
    
    def _get_region_coordinates(self, region: str) -> Optional[Dict]:
        """Retourne les coordonnées approximatives d'une région"""
        region_coords = {
            "dakar": {"lat": 14.7167, "lon": -17.4677},
            "bamako": {"lat": 12.6392, "lon": -8.0029},
            "abidjan": {"lat": 5.3600, "lon": -4.0083},
            "ouagadougou": {"lat": 12.3582, "lon": -1.5351},
            "lome": {"lat": 6.1319, "lon": 1.2228},
            "accra": {"lat": 5.6037, "lon": -0.1870},
            "kinshasa": {"lat": -4.4419, "lon": 15.2663}
        }
        
        return region_coords.get(region.lower())
    
    def _get_session(self, session_id: str) -> Optional[Dict]:
        """Récupère une session USSD"""
        return None
    
    def _create_session(self, session_id: str, phone_number: str) -> Dict:
        """Crée une nouvelle session USSD"""
        return {
            "session_id": session_id,
            "phone_number": phone_number,
            "screen": "main",
            "created_at": None
        }

class OfflineSyncService:
    def __init__(self):
        self.sms_service = SMSService()
        self.ussd_service = USSDService()
    
    def sync_offline_data(self, user_id: int, db: Session) -> Dict:
        """Synchronise les données hors-ligne"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "Utilisateur non trouvé"}
        
        if not user.phone:
            return {"error": "Numéro de téléphone non configuré"}
        
        summary = self._generate_user_summary(user)
        message = self._format_summary_message(summary)
        
        result = self.sms_service.send_sms(user.phone, message)
        
        return {
            "success": result.get("success", False),
            "message": "Résumé envoyé par SMS",
            "sms_result": result
        }
    
    def _generate_user_summary(self, user: User) -> Dict:
        """Génère un résumé des données utilisateur"""
        total_revenue = sum(record.revenue for record in user.finance_records)
        total_cost = sum(record.cost for record in user.finance_records)
        orders_count = len(user.marketplace_transactions)
        
        return {
            "balance": total_revenue - total_cost,
            "orders": orders_count,
            "crops": len(user.crops),
            "fields": len(user.fields)
        }
    
    def _format_summary_message(self, summary: Dict) -> str:
        """Formate le résumé en message SMS"""
        message = f"AgroSmart - Résumé\n"
        message += f"Solde: {summary['balance']:.2f} XOF\n"
        message += f"Commandes: {summary['orders']}\n"
        message += f"Cultures: {summary['crops']}\n"
        message += f"Champs: {summary['fields']}"
        
        return message

sms_ussd_service = OfflineSyncService()
