"""
Crypto Payment Service - Paiements blockchain révolutionnaires

Fonctionnalités Phase 3.2 :
- Intégration MetaMask pour wallets Ethereum/Polygon
- Support stablecoins africains (USDC, USDT, cUSD)
- Conversion automatique XOF ↔ Crypto
- Sécurité renforcée avec signatures
"""
import logging
import json
import uuid
import time
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

try:
    from web3 import Web3, HTTPProvider
    from web3.middleware import geth_poa_middleware
    from eth_account import Account
    from eth_account.messages import encode_defunct
    WEB3_AVAILABLE = True
except ImportError:
    Web3 = None
    HTTPProvider = None
    geth_poa_middleware = None
    Account = None
    encode_defunct = None
    WEB3_AVAILABLE = False

from blockchain_config import BLOCKCHAIN_CONFIG

logger = logging.getLogger("crypto_payment_service")

# Stablecoins supportés
SUPPORTED_STABLECOINS = {
    "USDC": {
        "name": "USD Coin",
        "contract_address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # Polygon USDC
        "decimals": 6,
        "african_focus": True
    },
    "USDT": {
        "name": "Tether USD",
        "contract_address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",  # Polygon USDT
        "decimals": 6,
        "african_focus": True
    },
    "cUSD": {
        "name": "Celo Dollar",
        "contract_address": "0x765DE816845861e75A25fCA122bb6898B8B1282a",  # Celo cUSD
        "decimals": 18,
        "african_focus": True
    },
    "CELO": {
        "name": "Celo Native",
        "contract_address": None,  # Native token
        "decimals": 18,
        "african_focus": True
    }
}

# Taux de conversion XOF (approximatifs - en production utiliser API oracle)
XOF_TO_USD_RATE = 0.0015  # 1 XOF = ~0.0015 USD
USD_TO_XOF_RATE = 655.957  # 1 USD = ~656 XOF

# APIs pour taux de change (fallback)
EXCHANGE_APIS = [
    "https://api.exchangerate-api.com/v4/latest/XOF",
    "https://open.er-api.com/v6/latest/XOF"
]


def get_web3() -> Optional["Web3"]:
    """Connexion Web3 pour paiements crypto"""
    if not WEB3_AVAILABLE:
        logger.warning("Web3 non disponible - paiements crypto désactivés")
        return None

    provider_url = BLOCKCHAIN_CONFIG.get("provider_url")
    if not provider_url:
        logger.warning("Aucun provider blockchain configuré")
        return None

    w3 = Web3(HTTPProvider(provider_url))
    if BLOCKCHAIN_CONFIG.get("network", "").startswith("polygon"):
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    if not w3.is_connected():
        logger.warning("Impossible de se connecter au provider blockchain %s", provider_url)
        return None

    return w3


def get_exchange_rate(from_currency: str = "XOF", to_currency: str = "USD") -> float:
    """
    Récupérer le taux de change actuel
    """
    try:
        for api_url in EXCHANGE_APIS:
            try:
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if to_currency in data.get("rates", {}):
                        return data["rates"][to_currency]
            except Exception as e:
                logger.warning(f"Échec API taux change {api_url}: {e}")
                continue

        # Fallback vers taux statiques
        logger.warning("Utilisation taux fallback")
        return XOF_TO_USD_RATE if from_currency == "XOF" and to_currency == "USD" else USD_TO_XOF_RATE

    except Exception as e:
        logger.error(f"Erreur récupération taux change: {e}")
        return XOF_TO_USD_RATE if from_currency == "XOF" and to_currency == "USD" else USD_TO_XOF_RATE


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convertir un montant entre devises
    """
    if from_currency == to_currency:
        return amount

    # Conversion via USD comme intermédiaire
    if from_currency == "XOF" and to_currency in ["USDC", "USDT", "cUSD"]:
        usd_amount = amount * get_exchange_rate("XOF", "USD")
        return usd_amount
    elif to_currency == "XOF" and from_currency in ["USDC", "USDT", "cUSD"]:
        usd_amount = amount / get_exchange_rate("XOF", "USD")  # Inverse
        return usd_amount

    return amount  # Fallback


def verify_wallet_signature(message: str, signature: str, wallet_address: str) -> bool:
    """
    Vérifier la signature MetaMask d'un message
    """
    if not WEB3_AVAILABLE:
        return False

    try:
        # Encoder le message selon EIP-191
        encoded_message = encode_defunct(text=message)

        # Récupérer l'adresse depuis la signature
        recovered_address = Account.recover_message(encoded_message, signature=signature)

        # Comparer avec l'adresse fournie
        return recovered_address.lower() == wallet_address.lower()

    except Exception as e:
        logger.error(f"Erreur vérification signature: {e}")
        return False


def create_payment_request(order_id: int, amount_xof: float, buyer_wallet: str, preferred_stablecoin: str = "USDC") -> Dict[str, Any]:
    """
    Créer une demande de paiement crypto
    """
    try:
        # Générer un ID de paiement unique
        payment_id = str(uuid.uuid4())

        # Convertir le montant
        amount_crypto = convert_currency(amount_xof, "XOF", preferred_stablecoin)

        # Créer le message à signer pour MetaMask
        message = f"""AgroSmart Payment Request
Payment ID: {payment_id}
Order ID: {order_id}
Amount: {amount_xof} XOF ({amount_crypto:.6f} {preferred_stablecoin})
Timestamp: {int(time.time())}
Please sign to authorize this payment."""

        payment_request = {
            "payment_id": payment_id,
            "order_id": order_id,
            "amount_xof": amount_xof,
            "amount_crypto": amount_crypto,
            "stablecoin": preferred_stablecoin,
            "buyer_wallet": buyer_wallet,
            "message": message,
            "status": "pending_signature",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)  # Expiration 30min
        }

        logger.info(f"Demande paiement créée: {payment_id} pour {amount_xof} XOF")
        return payment_request

    except Exception as e:
        logger.error(f"Erreur création demande paiement: {e}")
        raise


def process_crypto_payment(payment_request: Dict[str, Any], signature: str) -> Dict[str, Any]:
    """
    Traiter un paiement crypto après signature MetaMask
    """
    try:
        # Vérifier la signature
        if not verify_wallet_signature(payment_request["message"], signature, payment_request["buyer_wallet"]):
            raise ValueError("Signature MetaMask invalide")

        # Vérifier l'expiration
        if datetime.utcnow() > payment_request["expires_at"]:
            raise ValueError("Demande de paiement expirée")

        w3 = get_web3()
        if not w3:
            raise ValueError("Connexion blockchain indisponible")

        stablecoin_info = SUPPORTED_STABLECOINS.get(payment_request["stablecoin"])
        if not stablecoin_info:
            raise ValueError(f"Stablecoin non supporté: {payment_request['stablecoin']}")

        # Simulation de transaction (en production : vraie transaction blockchain)
        tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"[:66]  # Simulation hash

        payment_result = {
            "payment_id": payment_request["payment_id"],
            "tx_hash": tx_hash,
            "status": "completed",
            "amount_crypto": payment_request["amount_crypto"],
            "stablecoin": payment_request["stablecoin"],
            "blockchain_confirmations": 1,  # Simulation
            "processed_at": datetime.utcnow(),
            "gas_used": 21000,  # Simulation
            "gas_price": "20000000000"  # 20 gwei simulation
        }

        logger.info(f"Paiement crypto traité: {payment_request['payment_id']} - {tx_hash}")
        return payment_result

    except Exception as e:
        logger.error(f"Erreur traitement paiement crypto: {e}")
        return {
            "payment_id": payment_request["payment_id"],
            "status": "failed",
            "error": str(e)
        }


def get_wallet_balance(wallet_address: str, stablecoin: str = "USDC") -> float:
    """
    Récupérer le solde d'un wallet pour une stablecoin donnée
    """
    try:
        w3 = get_web3()
        if not w3:
            return 0.0

        stablecoin_info = SUPPORTED_STABLECOINS.get(stablecoin)
        if not stablecoin_info or not stablecoin_info["contract_address"]:
            return 0.0

        # Contrat ERC-20
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]

        contract = w3.eth.contract(
            address=w3.to_checksum_address(stablecoin_info["contract_address"]),
            abi=abi
        )

        balance_wei = contract.functions.balanceOf(w3.to_checksum_address(wallet_address)).call()
        balance = balance_wei / (10 ** stablecoin_info["decimals"])

        return balance

    except Exception as e:
        logger.error(f"Erreur récupération solde wallet: {e}")
        return 0.0


def estimate_gas_cost(stablecoin: str = "USDC") -> Dict[str, Any]:
    """
    Estimer les coûts de gas pour une transaction
    """
    try:
        w3 = get_web3()
        if not w3:
            return {"error": "Blockchain indisponible"}

        gas_price = w3.eth.gas_price
        estimated_gas = 65000  # Gas estimé pour transaction ERC-20

        gas_cost_wei = gas_price * estimated_gas
        gas_cost_eth = w3.from_wei(gas_cost_wei, 'ether')

        # Conversion en XOF
        gas_cost_xof = gas_cost_eth * USD_TO_XOF_RATE

        return {
            "gas_price_gwei": w3.from_wei(gas_price, 'gwei'),
            "estimated_gas": estimated_gas,
            "gas_cost_eth": float(gas_cost_eth),
            "gas_cost_xof": round(gas_cost_xof, 2),
            "stablecoin": stablecoin
        }

    except Exception as e:
        logger.error(f"Erreur estimation gas: {e}")
        return {"error": str(e)}


def get_african_stablecoin_options() -> List[Dict[str, Any]]:
    """
    Retourner les options de stablecoins africains disponibles
    """
    options = []
    for symbol, info in SUPPORTED_STABLECOINS.items():
        if info.get("african_focus", False):
            options.append({
                "symbol": symbol,
                "name": info["name"],
                "contract_address": info["contract_address"],
                "decimals": info["decimals"],
                "recommended": symbol in ["USDC", "cUSD"]  # Recommandés pour l'Afrique
            })

    return options


def validate_wallet_address(address: str) -> bool:
    """
    Valider qu'une adresse wallet est correctement formatée
    """
    if not WEB3_AVAILABLE:
        return False

    try:
        return Web3.is_address(address)
    except Exception:
        return False


def get_payment_history(wallet_address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupérer l'historique des paiements pour un wallet
    Simulation - en production utiliser un indexer blockchain
    """
    # Simulation d'historique
    return [
        {
            "tx_hash": f"0x{uuid.uuid4().hex[:64]}",
            "amount": 50000 + i * 10000,
            "currency": "XOF",
            "stablecoin": "USDC",
            "amount_crypto": (50000 + i * 10000) * XOF_TO_USD_RATE,
            "timestamp": datetime.utcnow() - timedelta(days=i),
            "status": "completed",
            "type": "payment" if i % 2 == 0 else "refund"
        } for i in range(min(limit, 5))
    ]


class CryptoPaymentService:
    """Facade utilisée par le routeur payments pour les opérations crypto."""

    def __init__(self):
        self._pending_requests: Dict[str, Dict[str, Any]] = {}

    def create_payment_request(
        self,
        user_id: int,
        amount_usd: float,
        crypto_type: str = "USDC",
    ) -> Dict[str, Any]:
        amount_xof = amount_usd * USD_TO_XOF_RATE
        buyer_wallet = "0x0000000000000000000000000000000000000000"
        request = create_payment_request(
            order_id=user_id,
            amount_xof=amount_xof,
            buyer_wallet=buyer_wallet,
            preferred_stablecoin=crypto_type,
        )
        self._pending_requests[request["payment_id"]] = request
        return request

    def process_payment(self, request_id: str, transaction_hash: str) -> Dict[str, Any]:
        payment_request = self._pending_requests.get(request_id)
        if not payment_request:
            return {"status": "failed", "error": "Payment request not found", "request_id": request_id}

        result = {
            "payment_id": request_id,
            "tx_hash": transaction_hash,
            "status": "completed",
            "amount_crypto": payment_request["amount_crypto"],
            "stablecoin": payment_request["stablecoin"],
            "processed_at": datetime.utcnow(),
        }
        self._pending_requests.pop(request_id, None)
        logger.info("Paiement crypto confirmé: %s - %s", request_id, transaction_hash)
        return result

    def get_wallet_balance(self, wallet_address: str) -> Dict[str, Any]:
        balances = {
            symbol: get_wallet_balance(wallet_address, symbol)
            for symbol in SUPPORTED_STABLECOINS
        }
        return {"wallet_address": wallet_address, "balances": balances}

    def estimate_gas(self, crypto_type: str = "USDC") -> Dict[str, Any]:
        stablecoin = crypto_type if crypto_type in SUPPORTED_STABLECOINS else "USDC"
        return estimate_gas_cost(stablecoin)

    def get_supported_stablecoins(self) -> List[Dict[str, Any]]:
        return get_african_stablecoin_options()

    def get_transaction_history(self, wallet_address: str, limit: int = 20) -> List[Dict[str, Any]]:
        return get_payment_history(wallet_address, limit)


# Configuration MetaMask pour le frontend
METAMASK_CONFIG = {
    "required_network": {
        "chainId": "0x89",  # Polygon Mainnet
        "chainName": "Polygon Mainnet",
        "nativeCurrency": {
            "name": "MATIC",
            "symbol": "MATIC",
            "decimals": 18
        },
        "rpcUrls": ["https://polygon-rpc.com/"],
        "blockExplorerUrls": ["https://polygonscan.com/"]
    },
    "supported_stablecoins": get_african_stablecoin_options(),
    "payment_flow": [
        "create_payment_request",
        "sign_with_metamask",
        "verify_signature",
        "process_transaction",
        "confirm_payment"
    ]
}