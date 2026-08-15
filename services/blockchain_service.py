import json
import time
import logging
from typing import Optional, Dict, Any

from blockchain_config import BLOCKCHAIN_CONFIG, TRACEABILITY_CONTRACT_ABI, ZERO_ADDRESS
from services.blockchain_adapter import get_blockchain_adapter

try:
    from web3 import Web3, HTTPProvider
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:  # pragma: no cover
    Web3 = None
    HTTPProvider = None
    geth_poa_middleware = None
    WEB3_AVAILABLE = False

logger = logging.getLogger("blockchain_service")


def get_web3() -> Optional["Web3"]:
    if not WEB3_AVAILABLE:
        logger.warning("Web3 n'est pas installé. Traçabilité blockchain désactivée.")
        return None

    provider_url = BLOCKCHAIN_CONFIG.get("provider_url")
    if not provider_url:
        logger.warning("Aucun provider URL blockchain configuré.")
        return None

    w3 = Web3(HTTPProvider(provider_url))
    if BLOCKCHAIN_CONFIG.get("network", "").startswith("polygon"):
        try:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except Exception:
            pass

    if not w3.is_connected():
        logger.warning("Impossible de se connecter au provider blockchain %s", provider_url)
        return None

    return w3


def _is_valid_contract_address(address: Optional[str]) -> bool:
    if not address:
        return False
    if address.strip().lower() == ZERO_ADDRESS.lower():
        return False
    if WEB3_AVAILABLE and Web3.is_address(address):
        return True
    return address.startswith("0x") and len(address) == 42


def get_blockchain_status() -> dict:
    # If adapter mock is used, reflect that in status
    adapter = get_blockchain_adapter()
    status = {
        "provider_url": BLOCKCHAIN_CONFIG.get("provider_url"),
        "network": BLOCKCHAIN_CONFIG.get("network"),
        "chain_id": BLOCKCHAIN_CONFIG.get("chain_id"),
        "adapter": adapter.__class__.__name__,
        "contract_configured": _is_valid_contract_address(BLOCKCHAIN_CONFIG.get("contract_address")),
        "private_key_configured": bool(BLOCKCHAIN_CONFIG.get("private_key")),
        "contract_address": BLOCKCHAIN_CONFIG.get("contract_address"),
        "errors": []
    }

    # Additional warnings when real web3 not available
    if adapter.__class__.__name__.startswith("Mock"):
        status["errors"].append("Blockchain adapter en mode mock: aucune transaction réelle ne sera envoyée.")
    elif adapter.__class__.__name__.startswith("Local"):
        status["errors"].append("Blockchain adapter local: transactions enregistrées en local pour tests/fallback.")

    return status


def get_trace_contract() -> Optional["Web3.contract"]:
    # Deprecated when using adapter pattern; keep for backward compatibility
    w3 = get_web3()
    if not w3:
        return None

    contract_address = BLOCKCHAIN_CONFIG.get("contract_address")
    if not _is_valid_contract_address(contract_address):
        logger.warning("Aucune adresse de contrat blockchain valide configurée.")
        return None

    try:
        return w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=TRACEABILITY_CONTRACT_ABI)
    except Exception as e:
        logger.error("Erreur création du contrat de traçabilité: %s", e)
        return None


def sign_and_send_transaction(function_call: Any) -> Optional[str]:
    w3 = get_web3()
    if not w3:
        return None

    private_key = BLOCKCHAIN_CONFIG.get("private_key")
    if not private_key:
        logger.warning("Aucune clé privée blockchain configurée. Transaction non signée.")
        return None

    if private_key.startswith("0x"):
        private_key = private_key[2:]

    account = w3.eth.account.from_key(private_key)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = function_call.build_transaction({
        "chainId": BLOCKCHAIN_CONFIG.get("chain_id", 80001),
        "gas": 300000,
        "maxFeePerGas": w3.eth.gas_price,
        "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
        "nonce": nonce,
    })

    signed_tx = account.sign_transaction(tx)
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        logger.info("Transaction blockchain envoyée", extra={"tx_hash": tx_hash.hex(), "receipt": dict(receipt)})
        return tx_hash.hex()
    except Exception as e:
        logger.error("Erreur envoi transaction blockchain: %s", e)
        return None


def add_trace_on_chain(product_id: str, origin: str, certification: str, timestamp: int) -> Optional[str]:
    adapter = get_blockchain_adapter()
    try:
        return adapter.add_trace_on_chain(product_id, origin, certification, timestamp)
    except Exception as e:
        logger.error("Erreur addTrace via adapter: %s", e)
        return None


def get_trace_from_chain(product_id: str) -> Optional[Dict[str, Any]]:
    adapter = get_blockchain_adapter()
    try:
        return adapter.get_trace_from_chain(product_id)
    except Exception as e:
        logger.error("Erreur getTrace via adapter: %s", e)
        return None


def verify_certification_on_chain(product_id: str, cert_type: str) -> Optional[str]:
    adapter = get_blockchain_adapter()
    try:
        return adapter.verify_certification_on_chain(product_id, cert_type)
    except Exception as e:
        logger.error("Erreur verifyCertification via adapter: %s", e)
        return None


# ==========================================
# ESCROW SMART CONTRACTS
# ==========================================

def deploy_escrow_contract(buyer_address: str, seller_address: str, amount: float, release_conditions: Dict[str, Any]) -> Optional[str]:
    """
    Déployer un contrat escrow pour sécuriser les paiements marketplace
    """
    w3 = get_web3()
    if w3:
        # Attempt on-chain deployment when Web3 is available
        escrow_abi = [
            {
                "type": "function",
                "name": "fund",
                "inputs": [],
                "outputs": [],
                "stateMutability": "payable"
            },
            {
                "type": "function",
                "name": "release",
                "inputs": [{"name": "conditions", "type": "string"}],
                "outputs": [],
                "stateMutability": "nonpayable"
            }
        ]

        escrow_bytecode = "0x608060405234801561001057600080fd5b50d3801561001d57600080fd5b50d2801561002a57600080fd5b506101508061003a6000396000f3fe608060405234801561001057600080fd5b50d3801561001d57600080fd5b50d2801561002a57600080fd5b50600436106100405760003560e01c80636b9f32e7146100455780638da5cb5b14610063575b600080fd5b61004d61006d565b60408051918252519081900360200190f35b61006b610073565b005b60005490565b60008054600101905556fea2646970667358221220c0c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c164736f6c63430008030033"

        try:
            EscrowContract = w3.eth.contract(abi=escrow_abi, bytecode=escrow_bytecode)
            private_key = BLOCKCHAIN_CONFIG.get("private_key")
            if not private_key:
                raise ValueError("No blockchain private key configured")

            if private_key.startswith("0x"):
                private_key = private_key[2:]

            account = w3.eth.account.from_key(private_key)
            nonce = w3.eth.get_transaction_count(account.address)
            tx = EscrowContract.constructor().build_transaction({
                "chainId": BLOCKCHAIN_CONFIG.get("chain_id", 80001),
                "gas": 2000000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
            })
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            contract_address = receipt.contractAddress
            logger.info("Contrat escrow déployé", extra={"contract_address": contract_address, "tx_hash": tx_hash.hex()})
            return contract_address
        except Exception as e:
            logger.warning("Web3 escrow deployment failed, falling back to adapter: %s", e)

    adapter = get_blockchain_adapter()
    try:
        return adapter.deploy_escrow_contract(buyer_address, seller_address, amount, release_conditions)
    except Exception as e:
        logger.error("Erreur deploy escrow via adapter: %s", e)
        return None


def fund_escrow_contract(contract_address: str, amount: float) -> Optional[str]:
    """
    Financer un contrat escrow avec les fonds de l'acheteur
    """
    adapter = get_blockchain_adapter()
    w3 = get_web3()

    if w3 and _is_valid_contract_address(contract_address):
        try:
            escrow_abi = [
                {
                    "type": "function",
                    "name": "fund",
                    "inputs": [],
                    "outputs": [],
                    "stateMutability": "payable"
                }
            ]
            contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=escrow_abi)
            private_key = BLOCKCHAIN_CONFIG.get("private_key")
            if not private_key:
                raise ValueError("No blockchain private key configured")

            if private_key.startswith("0x"):
                private_key = private_key[2:]

            account = w3.eth.account.from_key(private_key)
            nonce = w3.eth.get_transaction_count(account.address)
            value_in_wei = w3.to_wei(amount / 655.957, "ether")  # Approximation XOF to ETH

            tx = contract.functions.fund().build_transaction({
                "chainId": BLOCKCHAIN_CONFIG.get("chain_id", 80001),
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
                "value": value_in_wei
            })

            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            logger.info("Contrat escrow financé", extra={"contract_address": contract_address, "tx_hash": tx_hash.hex()})
            return tx_hash.hex()
        except Exception as e:
            logger.warning("Web3 escrow funding failed, falling back to adapter: %s", e)

    try:
        return adapter.fund_escrow_contract(contract_address, amount)
    except Exception as e:
        logger.error("Erreur fund escrow via adapter: %s", e)
        return None


def release_escrow_funds(contract_address: str, release_conditions: str) -> Optional[str]:
    """
    Libérer les fonds escrow après vérification des conditions
    """
    adapter = get_blockchain_adapter()
    w3 = get_web3()

    if w3 and _is_valid_contract_address(contract_address):
        try:
            escrow_abi = [
                {
                    "type": "function",
                    "name": "release",
                    "inputs": [{"name": "conditions", "type": "string"}],
                    "outputs": [],
                    "stateMutability": "nonpayable"
                }
            ]
            contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=escrow_abi)
            tx_hash = sign_and_send_transaction(contract.functions.release(release_conditions))
            return tx_hash
        except Exception as e:
            logger.warning("Web3 escrow release failed, falling back to adapter: %s", e)

    try:
        return adapter.release_escrow_funds(contract_address, release_conditions)
    except Exception as e:
        logger.error("Erreur release escrow via adapter: %s", e)
        return None


# ==========================================
# AGRICULTURAL NFTS
# ==========================================

def deploy_nft_contract(name: str, symbol: str) -> Optional[str]:
    """
    Déployer un contrat NFT pour les tokens agricoles
    """
    adapter = get_blockchain_adapter()
    w3 = get_web3()

    if w3:
        nft_abi = [
            {
                "type": "function",
                "name": "mint",
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "uri", "type": "string"}
                ],
                "outputs": [],
                "stateMutability": "nonpayable"
            },
            {
                "type": "function",
                "name": "transferFrom",
                "inputs": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "tokenId", "type": "uint256"}
                ],
                "outputs": [],
                "stateMutability": "nonpayable"
            }
        ]

        nft_bytecode = "0x608060405234801561001057600080fd5b50d3801561001d57600080fd5b50d2801561002a57600080fd5b506101508061003a6000396000f3fe608060405234801561001057600080fd5b50d3801561001d57600080fd5b50d2801561002a57600080fd5b50600436106100405760003560e01c80636b9f32e7146100455780638da5cb5b14610063575b600080fd5b61004d61006d565b60408051918252519081900360200190f35b61006b610073565b005b60005490565b60008054600101905556fea2646970667358221220d0d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d164736f6c63430008030033"

        try:
            NFTContract = w3.eth.contract(abi=nft_abi, bytecode=nft_bytecode)
            private_key = BLOCKCHAIN_CONFIG.get("private_key")
            if not private_key:
                raise ValueError("No blockchain private key configured")

            if private_key.startswith("0x"):
                private_key = private_key[2:]

            account = w3.eth.account.from_key(private_key)
            nonce = w3.eth.get_transaction_count(account.address)

            tx = NFTContract.constructor(name, symbol).build_transaction({
                "chainId": BLOCKCHAIN_CONFIG.get("chain_id", 80001),
                "gas": 3000000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
            })

            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            contract_address = receipt.contractAddress
            logger.info("Contrat NFT déployé", extra={"contract_address": contract_address, "name": name, "symbol": symbol})
            return contract_address
        except Exception as e:
            logger.warning("Web3 NFT deployment failed, falling back to adapter: %s", e)

    try:
        return adapter.deploy_nft_contract(name, symbol)
    except Exception as e:
        logger.error("Erreur deploy NFT via adapter: %s", e)
        return None


def mint_agricultural_nft(contract_address: str, to_address: str, token_id: int, token_uri: str) -> Optional[str]:
    """
    Frapper un NFT agricole représentant une étape de la chaîne d'approvisionnement
    """
    adapter = get_blockchain_adapter()
    w3 = get_web3()

    if w3 and _is_valid_contract_address(contract_address):
        try:
            nft_abi = [
                {
                    "type": "function",
                    "name": "mint",
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "tokenId", "type": "uint256"},
                        {"name": "uri", "type": "string"}
                    ],
                    "outputs": [],
                    "stateMutability": "nonpayable"
                }
            ]
            contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=nft_abi)
            tx_hash = sign_and_send_transaction(contract.functions.mint(w3.to_checksum_address(to_address), token_id, token_uri))
            return tx_hash
        except Exception as e:
            logger.warning("Web3 NFT mint failed, falling back to adapter: %s", e)

    try:
        return adapter.mint_agricultural_nft(contract_address, to_address, token_id, token_uri)
    except Exception as e:
        logger.error("Erreur mint NFT via adapter: %s", e)
        return None


def transfer_nft(contract_address: str, from_address: str, to_address: str, token_id: int) -> Optional[str]:
    """
    Transférer un NFT agricole lors d'un changement de propriétaire dans la chaîne d'approvisionnement
    """
    adapter = get_blockchain_adapter()
    w3 = get_web3()

    if w3 and _is_valid_contract_address(contract_address):
        try:
            nft_abi = [
                {
                    "type": "function",
                    "name": "transferFrom",
                    "inputs": [
                        {"name": "from", "type": "address"},
                        {"name": "to", "type": "address"},
                        {"name": "tokenId", "type": "uint256"}
                    ],
                    "outputs": [],
                    "stateMutability": "nonpayable"
                }
            ]
            contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=nft_abi)
            tx_hash = sign_and_send_transaction(contract.functions.transferFrom(
                w3.to_checksum_address(from_address),
                w3.to_checksum_address(to_address),
                token_id
            ))
            return tx_hash
        except Exception as e:
            logger.warning("Web3 NFT transfer failed, falling back to adapter: %s", e)

    try:
        return adapter.transfer_agricultural_nft(contract_address, token_id, from_address, to_address)
    except Exception as e:
        logger.error("Erreur transfer NFT via adapter: %s", e)
        return None
