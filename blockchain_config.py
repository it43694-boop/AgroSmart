"""
Configuration blockchain Ethereum/Polygon pour traçabilité agricole
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _normalize_env_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip()
    if normalized == "" or normalized.lower() == ZERO_ADDRESS.lower():
        return None
    return normalized


# Configuration Polygon (layer 2 pour coûts réduits)
BLOCKCHAIN_CONFIG = {
    "provider_url": _normalize_env_value(os.getenv(
        "POLYGON_RPC_URL", 
        "https://polygon-rpc.com/"  # Mainnet Polygon par défaut pour production
    )),
    "contract_address": _normalize_env_value(os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS", None)),
    "private_key": _normalize_env_value(os.getenv("BLOCKCHAIN_PRIVATE_KEY", None)),
    "chain_id": int(os.getenv("CHAIN_ID", 137)),  # 137 = Polygon Mainnet
    "network": os.getenv("BLOCKCHAIN_NETWORK", "polygon-mainnet")
}

# ABI du smart contract de traçabilité (simplifié)
TRACEABILITY_CONTRACT_ABI = [
    {
        "type": "function",
        "name": "addTrace",
        "inputs": [
            {"name": "productId", "type": "string"},
            {"name": "origin", "type": "string"},
            {"name": "certification", "type": "string"},
            {"name": "timestamp", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}]
    },
    {
        "type": "function",
        "name": "getTrace",
        "inputs": [{"name": "productId", "type": "string"}],
        "outputs": [
            {"name": "origin", "type": "string"},
            {"name": "certification", "type": "string"},
            {"name": "timestamp", "type": "uint256"},
            {"name": "verified", "type": "bool"}
        ]
    },
    {
        "type": "function",
        "name": "verifyCertification",
        "inputs": [
            {"name": "productId", "type": "string"},
            {"name": "certType", "type": "string"}
        ],
        "outputs": [{"name": "", "type": "bool"}]
    }
]

# Smart contract source (Solidity simplifié)
SMART_CONTRACT_SOURCE = """
pragma solidity ^0.8.0;

contract AgriculturalTraceability {
    struct ProductTrace {
        string origin;
        string certification;
        uint256 timestamp;
        bool verified;
        address recorder;
    }
    
    mapping(string => ProductTrace) public traces;
    mapping(string => bool) public certifications;
    
    event TraceAdded(string indexed productId, string origin, string certification);
    event CertificationVerified(string indexed productId, string certType);
    
    function addTrace(string memory productId, string memory origin, string memory certification, uint256 timestamp) public returns (bool) {
        traces[productId] = ProductTrace(origin, certification, timestamp, false, msg.sender);
        emit TraceAdded(productId, origin, certification);
        return true;
    }
    
    function getTrace(string memory productId) public view returns (string memory, string memory, uint256, bool) {
        ProductTrace memory t = traces[productId];
        return (t.origin, t.certification, t.timestamp, t.verified);
    }
    
    function verifyCertification(string memory productId, string memory certType) public returns (bool) {
        traces[productId].verified = true;
        certifications[certType] = true;
        emit CertificationVerified(productId, certType);
        return true;
    }
}
"""
