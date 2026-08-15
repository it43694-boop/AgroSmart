"""Payments API routes - Crypto payments, wallets, and transactions"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import datetime

from database import get_db
import models
import auth
from services.crypto_payment_service import CryptoPaymentService

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Initialize crypto payment service
crypto_service = CryptoPaymentService()


@router.post("/crypto/request/")
def request_crypto_payment(
    payment_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Request a crypto payment"""
    try:
        amount_usd = payment_data.get("amount_usd", 0)
        crypto_type = payment_data.get("crypto_type", "USDC")
        
        # Use crypto payment service
        payment_request = crypto_service.create_payment_request(
            user_id=current_user.id,
            amount_usd=amount_usd,
            crypto_type=crypto_type
        )
        
        return payment_request
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur demande paiement: {str(e)}")


@router.post("/crypto/process/")
def process_crypto_payment(
    payment_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Process a crypto payment"""
    try:
        transaction_hash = payment_data.get("transaction_hash")
        request_id = payment_data.get("request_id")
        
        # Use crypto payment service
        payment_result = crypto_service.process_payment(
            request_id=request_id,
            transaction_hash=transaction_hash
        )
        
        return payment_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur traitement paiement: {str(e)}")


@router.get("/wallet/{wallet_address}/balance/")
def get_wallet_balance(
    wallet_address: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get wallet balance"""
    try:
        balance = crypto_service.get_wallet_balance(wallet_address)
        return balance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur solde wallet: {str(e)}")


@router.get("/gas-estimate/")
def get_gas_estimate(
    crypto_type: str = "ETH",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get gas estimate for transactions"""
    try:
        gas_estimate = crypto_service.estimate_gas(crypto_type)
        return gas_estimate
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur estimation gas: {str(e)}")


@router.get("/stablecoins/")
def get_stablecoins(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get available stablecoins"""
    try:
        stablecoins = crypto_service.get_supported_stablecoins()
        return {"stablecoins": stablecoins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur stablecoins: {str(e)}")


@router.get("/history/{wallet_address}/")
def get_payment_history(
    wallet_address: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get payment history for a wallet"""
    try:
        history = crypto_service.get_transaction_history(wallet_address, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur historique: {str(e)}")
