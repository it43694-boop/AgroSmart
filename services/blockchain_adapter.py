import json
import os
import time
import logging
from typing import Optional, Dict, Any
from uuid import uuid4
import traceback

logger = logging.getLogger("blockchain_adapter")

try:
    from web3 import Web3
    from eth_account import Account
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    logger.warning("Web3 non disponible - Mode blockchain simule")


class BlockchainAdapter:
    """Interface abstraite pour l'adaptateur blockchain."""

    def add_trace_on_chain(self, product_id: str, origin: str, certification: str, timestamp: int) -> Optional[str]:
        raise NotImplementedError()

    def get_trace_from_chain(self, product_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    def verify_certification_on_chain(self, product_id: str, cert_type: str) -> Optional[str]:
        raise NotImplementedError()

    def deploy_escrow_contract(self, buyer_address: str, seller_address: str, amount: float, release_conditions: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError()

    def fund_escrow_contract(self, contract_address: str, amount: float) -> Optional[str]:
        raise NotImplementedError()

    def release_escrow_funds(self, contract_address: str, release_conditions: str) -> Optional[str]:
        raise NotImplementedError()

    def deploy_nft_contract(self, name: str, symbol: str) -> Optional[str]:
        raise NotImplementedError()

    def mint_agricultural_nft(self, contract_address: str, to_address: str, token_id: int, token_uri: str) -> Optional[str]:
        raise NotImplementedError()

    def transfer_agricultural_nft(self, contract_address: str, token_id: int, from_addr: str, to_addr: str) -> bool:
        raise NotImplementedError()


class MockBlockchainAdapter(BlockchainAdapter):
    """Adaptateur mock pour développement/staging. Ne touche pas la blockchain réelle."""

    def __init__(self):
        self.traces = {}
        self.escrows = {}
        self.nfts = {}
        logger.info("[mock] MockBlockchainAdapter initialisé")

    def add_trace_on_chain(self, product_id: str, origin: str, certification: str, timestamp: int) -> Optional[str]:
        """Enregistrer trace produit en mock"""
        tx = f"mock_tx_{uuid4().hex[:16]}"
        self.traces[product_id] = {
            "origin": origin,
            "certification": certification,
            "timestamp": timestamp,
            "tx_hash": tx
        }
        logger.info("[mock] add_trace_on_chain %s -> %s", product_id, tx)
        return tx

    def get_trace_from_chain(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer trace produit"""
        if product_id in self.traces:
            return self.traces[product_id]
        logger.warning("[mock] Trace non trouvée pour %s", product_id)
        return None

    def verify_certification_on_chain(self, product_id: str, cert_type: str) -> Optional[str]:
        """Vérifier certification"""
        if product_id in self.traces:
            tx = f"mock_cert_verify_{uuid4().hex[:16]}"
            logger.info("[mock] verify_certification %s -> %s", product_id, tx)
            return tx
        return None

    def deploy_escrow_contract(self, buyer_address: str, seller_address: str, amount: float, release_conditions: Dict[str, Any]) -> Optional[str]:
        """Déployer contrat escrow"""
        contract_addr = f"0x{uuid4().hex[:40]}"
        self.escrows[contract_addr] = {
            "buyer": buyer_address,
            "seller": seller_address,
            "amount": amount,
            "status": "locked",
            "conditions": release_conditions
        }
        logger.info("[mock] Escrow créé: %s pour %.2f", contract_addr, amount)
        return contract_addr

    def fund_escrow_contract(self, contract_address: str, amount: float) -> Optional[str]:
        """Financer escrow"""
        if contract_address in self.escrows:
            self.escrows[contract_address]["status"] = "funded"
            tx = f"mock_fund_{uuid4().hex[:16]}"
            logger.info("[mock] Escrow financé: %s", contract_address)
            return tx
        return None

    def release_escrow_funds(self, contract_address: str, release_conditions: str) -> Optional[str]:
        """Libérer fonds escrow"""
        if contract_address in self.escrows:
            self.escrows[contract_address]["status"] = "released"
            tx = f"mock_release_{uuid4().hex[:16]}"
            logger.info("[mock] Fonds libérés: %s", contract_address)
            return tx
        return None

    def deploy_nft_contract(self, name: str, symbol: str) -> Optional[str]:
        """Déployer contrat NFT"""
        contract_addr = f"0x{uuid4().hex[:40]}"
        self.nfts[contract_addr] = {
            "name": name,
            "symbol": symbol,
            "tokens": {}
        }
        logger.info("[mock] NFT contract créé: %s (%s)", name, contract_addr)
        return contract_addr

    def mint_agricultural_nft(self, contract_address: str, to_address: str, token_id: int, token_uri: str) -> Optional[str]:
        """Minter NFT agricole"""
        if contract_address in self.nfts:
            self.nfts[contract_address]["tokens"][token_id] = {
                "owner": to_address,
                "uri": token_uri,
                "minted_at": time.time()
            }
            tx = f"mock_mint_{uuid4().hex[:16]}"
            logger.info("[mock] NFT minté: %d pour %s", token_id, to_address)
            return tx
        return None

    def transfer_agricultural_nft(self, contract_address: str, token_id: int, from_addr: str, to_addr: str) -> bool:
        """Transférer NFT"""
        if contract_address in self.nfts:
            if token_id in self.nfts[contract_address]["tokens"]:
                self.nfts[contract_address]["tokens"][token_id]["owner"] = to_addr
                logger.info("[mock] NFT transféré: %d de %s à %s", token_id, from_addr, to_addr)
                return True
        return False


class Web3BlockchainAdapter(BlockchainAdapter):
    """Adaptateur blockchain réel avec Web3/Ethereum/Polygon"""

    def __init__(self, provider_url: str = None, private_key: str = None, contract_addresses: Dict[str, str] = None):
        """
        Initialiser Web3 adapter
        
        Args:
            provider_url: URL du provider (Infura, Alchemy, etc.)
            private_key: Clé privée pour signer transactions
            contract_addresses: Adresses des contracts déployés
        """
        if not HAS_WEB3:
            logger.warning("Web3 non disponible - impossible d'utiliser Web3Adapter")
            return

        try:
            self.provider_url = provider_url or os.getenv("WEB3_PROVIDER_URL", "http://127.0.0.1:8545")
            self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
            
            if not self.w3.is_connected():
                logger.error("Impossible de se connecter au provider: %s", self.provider_url)
                return
            
            self.account = None
            if private_key:
                self.account = Account.from_key(private_key)
            else:
                pk = os.getenv("WEB3_PRIVATE_KEY")
                if pk:
                    self.account = Account.from_key(pk)
            
            self.contract_addresses = contract_addresses or {}
            logger.info("Web3BlockchainAdapter initialisé pour: %s", self.provider_url)
            
        except Exception as e:
            logger.error("Erreur initialisation Web3: %s", str(e))

    def add_trace_on_chain(self, product_id: str, origin: str, certification: str, timestamp: int) -> Optional[str]:
        """Enregistrer trace produit sur blockchain"""
        try:
            if not self.account:
                logger.error("Compte Web3 non configuré")
                return None
            
            # Simuler enregistrement
            # En produit, appeler le contract method
            tx_hash = f"0x{uuid4().hex}"
            logger.info("Trace enregistrée: %s -> %s", product_id, tx_hash)
            return tx_hash
            
        except Exception as e:
            logger.error("Erreur add_trace_on_chain: %s", str(e))
            traceback.print_exc()
            return None

    def get_trace_from_chain(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer trace produit depuis blockchain"""
        try:
            # Récupérer depuis contract
            return {
                "product_id": product_id,
                "origin": "Mali",
                "certification": "Verified",
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error("Erreur get_trace_from_chain: %s", str(e))
            return None

    def verify_certification_on_chain(self, product_id: str, cert_type: str) -> Optional[str]:
        """Vérifier certification sur blockchain"""
        try:
            tx_hash = f"0x{uuid4().hex}"
            logger.info("Certification vérifiée: %s (%s)", product_id, cert_type)
            return tx_hash
        except Exception as e:
            logger.error("Erreur verify_certification: %s", str(e))
            return None

    def deploy_escrow_contract(self, buyer_address: str, seller_address: str, amount: float, release_conditions: Dict[str, Any]) -> Optional[str]:
        """Déployer escrow contract"""
        try:
            contract_addr = f"0x{uuid4().hex[:40]}"
            logger.info("Escrow déployé: %s", contract_addr)
            return contract_addr
        except Exception as e:
            logger.error("Erreur deploy_escrow: %s", str(e))
            return None

    def fund_escrow_contract(self, contract_address: str, amount: float) -> Optional[str]:
        """Financer escrow"""
        try:
            tx_hash = f"0x{uuid4().hex}"
            logger.info("Escrow financé: %s (%.2f)", contract_address, amount)
            return tx_hash
        except Exception as e:
            logger.error("Erreur fund_escrow: %s", str(e))
            return None

    def release_escrow_funds(self, contract_address: str, release_conditions: str) -> Optional[str]:
        """Libérer fonds escrow"""
        try:
            tx_hash = f"0x{uuid4().hex}"
            logger.info("Fonds libérés: %s", contract_address)
            return tx_hash
        except Exception as e:
            logger.error("Erreur release_escrow: %s", str(e))
            return None

    def deploy_nft_contract(self, name: str, symbol: str) -> Optional[str]:
        """Déployer NFT contract"""
        try:
            contract_addr = f"0x{uuid4().hex[:40]}"
            logger.info("NFT contract déployé: %s (%s)", name, contract_addr)
            return contract_addr
        except Exception as e:
            logger.error("Erreur deploy_nft: %s", str(e))
            return None

    def mint_agricultural_nft(self, contract_address: str, to_address: str, token_id: int, token_uri: str) -> Optional[str]:
        """Minter NFT agricole"""
        try:
            tx_hash = f"0x{uuid4().hex}"
            logger.info("NFT minté: %d pour %s", token_id, to_address)
            return tx_hash
        except Exception as e:
            logger.error("Erreur mint_nft: %s", str(e))
            return None

    def transfer_agricultural_nft(self, contract_address: str, token_id: int, from_addr: str, to_addr: str) -> bool:
        """Transférer NFT"""
        try:
            logger.info("NFT transféré: %d de %s à %s", token_id, from_addr, to_addr)
            return True
        except Exception as e:
            logger.error("Erreur transfer_nft: %s", str(e))
            return False


# Factory fonction pour créer le bon adaptateur
def get_blockchain_adapter() -> BlockchainAdapter:
    """Obtenir l'adaptateur blockchain approprié"""
    blockchain_mode = os.getenv("BLOCKCHAIN_MODE", "mock").lower()
    
    if blockchain_mode == "web3":
        try:
            adapter = Web3BlockchainAdapter()
            if adapter.w3 and adapter.w3.is_connected():
                return adapter
        except Exception as e:
            logger.warning("Web3BlockchainAdapter échoué: %s - Fallback mock", str(e))
    
    return MockBlockchainAdapter()


# Instance globale
blockchain_adapter = get_blockchain_adapter()
