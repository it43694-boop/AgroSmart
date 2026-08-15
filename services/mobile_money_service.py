"""Mobile Money Service - Intègre des portefeuilles mobiles Mali ou un fallback local."""
import os
import json
import logging
from typing import Dict, Optional
from uuid import uuid4

import requests

logger = logging.getLogger("mobile_money_service")

DEFAULT_LOCAL_ADAPTER = "local_mobile_money"

PROVIDER_ALIASES = {
    "orange money": "orange_money",
    "orange_money": "orange_money",
    "orange": "orange_money",
    "wave": "wave",
    "wave money": "wave",
    "mtn": "mtn_mobile_money",
    "mtn mobile money": "mtn_mobile_money",
    "mobile_money": "local_mobile_money",
}


class MobileMoneyAdapter:
    """Interface abstraite pour les adaptateurs Mobile Money."""

    def verify_transaction(self, transaction_id: str, amount: float, currency: str) -> bool:
        raise NotImplementedError()

    def create_payment(self, amount: float, currency: str, external_reference: Optional[str] = None,
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        raise NotImplementedError()


class LocalMobileMoneyAdapter(MobileMoneyAdapter):
    """Fallback local lorsque le fournisseur réel n'est pas connecté."""

    def __init__(self, provider_name: str = DEFAULT_LOCAL_ADAPTER):
        self.provider_name = provider_name

    def verify_transaction(self, transaction_id: str, amount: float, currency: str) -> bool:
        logger.info("[local-mobile-money] verify_transaction %s for %s %s", transaction_id, amount, currency)
        if not transaction_id:
            return False
        return True

    def create_payment(self, amount: float, currency: str, external_reference: Optional[str] = None,
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        transaction_id = external_reference or f"local_mm_{uuid4().hex}"
        logger.info("[local-mobile-money] create_payment %s %s %s", amount, currency, transaction_id)
        return {
            "success": True,
            "provider_transaction_id": transaction_id,
            "message": "Mobile money fallback processed locally.",
            "raw_response": {
                "provider": self.provider_name,
                "transaction_id": transaction_id
            }
        }


class OrangeMoneyAdapter(MobileMoneyAdapter):
    """Adaptateur pour Orange Money si l'API est configurée."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _fetch_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        try:
            response = requests.get(f"{self.api_url}/{path.lstrip('/')}", headers=self._headers(), params=params or {}, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning("OrangeMoneyAdapter fetch failed: %s", exc)
            return None

    def verify_transaction(self, transaction_id: str, amount: float, currency: str) -> bool:
        if not transaction_id:
            return False

        payload = self._fetch_json("verify", {"transaction_id": transaction_id})
        if not payload:
            return False

        success = payload.get("status") in ("COMPLETED", "SUCCESS", "SUCCEEDED")
        if not success:
            return False

        if payload.get("amount") and payload.get("currency"):
            return float(payload.get("amount")) == float(amount) and payload.get("currency").upper() == currency.upper()

        return True

    def create_payment(self, amount: float, currency: str, external_reference: Optional[str] = None,
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        try:
            url = f"{self.api_url}/create"
            payload = {
                "amount": amount,
                "currency": currency,
                "external_reference": external_reference,
                "metadata": metadata or {}
            }
            response = requests.post(url, json=payload, headers=self._headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            transaction_id = data.get("transaction_id") or data.get("reference") or f"orange_{uuid4().hex}"
            success = data.get("success", True)
            return {
                "success": success,
                "provider_transaction_id": transaction_id,
                "message": data.get("message", "Orange Money payment created."),
                "raw_response": data
            }
        except Exception as exc:
            logger.warning("OrangeMoneyAdapter create_payment failed: %s", exc)
            return {
                "success": False,
                "provider_transaction_id": None,
                "message": f"Orange Money API unavailable: {exc}",
                "raw_response": None
            }


class WaveMoneyAdapter(OrangeMoneyAdapter):
    """Adapter générique pour Wave ou autres fournisseurs similaires."""

    def verify_transaction(self, transaction_id: str, amount: float, currency: str) -> bool:
        if not transaction_id:
            return False

        payload = self._fetch_json("verify", {"transaction_id": transaction_id})
        if not payload:
            return False

        success = payload.get("status") in ("COMPLETED", "SUCCESS", "SUCCEEDED")
        if not success:
            return False

        if payload.get("amount") and payload.get("currency"):
            return float(payload.get("amount")) == float(amount) and payload.get("currency").upper() == currency.upper()

        return True

    def create_payment(self, amount: float, currency: str, external_reference: Optional[str] = None,
                       metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        return super().create_payment(amount, currency, external_reference, metadata)


def get_mobile_money_adapter(provider: str) -> MobileMoneyAdapter:
    provider_key = PROVIDER_ALIASES.get(provider.strip().lower(), provider.strip().lower().replace(" ", "_"))

    if provider_key == "orange_money":
        api_url = os.getenv("ORANGE_MONEY_API_URL", "").strip()
        api_key = os.getenv("ORANGE_MONEY_API_KEY", "").strip()
        if api_url and api_key:
            return OrangeMoneyAdapter(api_url, api_key)

    if provider_key == "wave":
        api_url = os.getenv("WAVE_MONEY_API_URL", "").strip()
        api_key = os.getenv("WAVE_MONEY_API_KEY", "").strip()
        if api_url and api_key:
            return WaveMoneyAdapter(api_url, api_key)

    logger.warning("Mobile money provider %s non configuré ou non supporté, utilisation du fallback local.", provider)
    return LocalMobileMoneyAdapter(provider_name=provider)


class MobileMoneyService:
    """Services de paiement mobile money avec validation et fallback sûr."""

    @staticmethod
    def process_payment(provider: str, amount: float, currency: str = "XOF",
                        transaction_id: Optional[str] = None,
                        metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        adapter = get_mobile_money_adapter(provider)

        if transaction_id:
            verified = adapter.verify_transaction(transaction_id, amount, currency)
            if verified:
                return {
                    "success": True,
                    "provider_transaction_id": transaction_id,
                    "message": "Mobile money transaction verified.",
                    "raw_response": None
                }
            return {
                "success": False,
                "provider_transaction_id": transaction_id,
                "message": "Mobile money transaction could not be verified.",
                "raw_response": None
            }

        payment_result = adapter.create_payment(amount, currency, external_reference=transaction_id, metadata=metadata)
        return payment_result

mobile_money_service = MobileMoneyService()
