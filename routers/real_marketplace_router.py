"""Router Marketplace Réel - Intègre SAGA + Paiement Réel + Données Réelles"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from database import SessionLocal
from services.saga_orchestrator import execute_marketplace_order
from services.payment_service import process_real_payment
from services.real_data_service import (
    RealWeatherService,
    RealPriceService,
    RealIoTDataService,
    RealGovernmentDataService
)

logger = logging.getLogger(__name__)

real_marketplace_router = APIRouter(
    prefix="/api/marketplace-real",
    tags=["Marketplace (Real Integration)"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ DONNÉES RÉELLES ============

@real_marketplace_router.get("/weather/{latitude}/{longitude}")
def get_real_weather(latitude: float, longitude: float):
    """Récupérer météo RÉELLE (Open-Meteo API)"""
    weather = RealWeatherService.get_weather_for_location(latitude, longitude)
    return weather

@real_marketplace_router.get("/price/{crop_type}")
def get_real_crop_price(crop_type: str):
    """Récupérer prix RÉEL"""
    price = RealPriceService.get_crop_price(crop_type)
    return price

@real_marketplace_router.get("/price-forecast/{crop_type}")
def get_price_forecast(crop_type: str, weeks: int = 4):
    """Prévoir prix"""
    forecast = RealPriceService.get_market_forecast(crop_type, weeks_ahead=weeks)
    return forecast

@real_marketplace_router.get("/government/production/{region}/{crop}")
def get_gov_production_data(region: str, crop: str):
    """Récupérer données gouvernement Mali"""
    data = RealGovernmentDataService.get_crop_production_data(region, crop)
    return data

# ============ IoT RÉEL ============

@real_marketplace_router.post("/iot/sensor-reading")
def ingest_real_iot_reading(
    device_id: str,
    farm_id: int,
    sensor_type: str,
    value: float,
    unit: str
):
    """
    Ingérer données d'un VRAI capteur LoRaWAN

    Exemple:
    {
        "device_id": "LoRa-Farm5-01",
        "farm_id": 5,
        "sensor_type": "temperature",
        "value": 28.5,
        "unit": "°C"
    }
    """
    reading = RealIoTDataService.ingest_real_sensor_data(
        device_id=device_id,
        farm_id=farm_id,
        sensor_type=sensor_type,
        value=value,
        unit=unit
    )
    return reading

@real_marketplace_router.get("/iot/farm-summary/{farm_id}")
def get_farm_data_summary(farm_id: int):
    """Résumé données IoT réelles pour une ferme"""
    summary = RealIoTDataService.get_farm_real_data_summary(farm_id)
    return summary

# ============ COMMANDE COMPLÈTE AVEC SAGA ============

@real_marketplace_router.post("/order/complete-saga")
def create_order_with_complete_saga(
    order_data: dict,
    db: Session = Depends(get_db)
):
    """
    ⭐ FLUX COMPLET RÉEL: SAGA + Paiement + Données Réelles

    Exemple order_data:
    {
        "farmer_id": 5,
        "buyer_id": 10,
        "order_id": "ORD-20240518-001",
        "crop_type": "tomato",
        "quantity_kg": 500,
        "order_value": 100000,  # XOF
        "farm_id": 5,
        "farm_location": "Bamako",
        "latitude": 12.6552,
        "longitude": -8.0029,
        "iot_readings": {"temp": 28, "humidity": 65},
        "farm_data": {"fuel_liters": 50, "farm_size_hectares": 2.5},
        "payment_method_id": "pm_card_visa",  # Test card ou vraie carte
        "idempotency_key": "order-20240518-001"
    }

    Process:
    1. Récupérer données RÉELLES (météo, prix, données gov)
    2. Exécuter SAGA (7 étapes intégrées)
    3. Si SAGA OK → paiement RÉEL via Stripe
    4. Si paiement OK → publier Kafka events
    5. Si une étape échoue → compensation + refund
    """

    try:
        farmer_id = order_data.get("farmer_id")
        buyer_id = order_data.get("buyer_id")
        order_id = order_data.get("order_id")

        logger.info(f"🔵 Starting complete order SAGA: {order_id}")

        # STEP 0: Enrichir données avec données RÉELLES
        latitude = order_data.get("latitude", 12.6552)
        longitude = order_data.get("longitude", -8.0029)

        # Récupérer météo réelle
        weather = RealWeatherService.get_weather_for_location(latitude, longitude)
        order_data["real_weather"] = weather

        # Récupérer prix réel
        crop_type = order_data.get("crop_type", "tomato")
        price_data = RealPriceService.get_crop_price(crop_type)
        order_data["real_price"] = price_data

        # Récupérer données gouvernement
        gov_data = RealGovernmentDataService.get_crop_production_data("Bamako", crop_type)
        order_data["gov_data"] = gov_data

        logger.info(f"✓ Real data enriched: weather + price + gov data")

        # STEP 1: Exécuter SAGA complet (7 étapes: credit → insurance → escrow → payment → iot → carbon → reputation)
        saga_result = execute_marketplace_order(order_data, db)

        if saga_result.get("status") in ("compensated", "failed"):
            logger.error(f"SAGA failed: {saga_result}")
            raise HTTPException(status_code=400, detail=f"Order failed: {saga_result.get('error')}")

        payment_result = saga_result.get("results", {}).get("payment_processing")
        if not payment_result or payment_result.get("status") != "succeeded":
            logger.error(f"Payment result missing after SAGA completion: {payment_result}")
            raise HTTPException(status_code=500, detail="Payment result missing after saga completion")

        logger.info(f"✓ Payment succeeded: {payment_result.get('charge_id')}")

        # SUCCESS: Tout OK!
        final_result = {
            "status": "completed",
            "order_id": order_id,
            "saga_result": saga_result,
            "payment_result": payment_result,
            "real_data": {
                "weather": weather,
                "price": price_data,
                "government": gov_data
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"🟢 Order COMPLETED: {order_id}")
        logger.info(f"   Charge ID: {payment_result.get('charge_id')}")
        logger.info(f"   SAGA steps: {list(saga_result.get('results', {}).keys())}")

        return final_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔴 Order failed with exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ TEST ENDPOINTS ============

@real_marketplace_router.post("/test/order-successful")
def test_order_successful(db: Session = Depends(get_db)):
    """
    Test: Créer une commande COMPLÈTE avec succès
    (Utilise test card Stripe qui réussit toujours)
    """
    test_order = {
        "farmer_id": 5,
        "buyer_id": 10,
        "order_id": f"TEST-{datetime.utcnow().timestamp()}",
        "crop_type": "tomato",
        "quantity_kg": 500,
        "order_value": 100000,  # 100K XOF = ~167 USD
        "farm_id": 5,
        "farm_location": "Bamako",
        "latitude": 12.6552,
        "longitude": -8.0029,
        "iot_readings": {"temp": 28, "humidity": 65},
        "farm_data": {"fuel_liters": 50, "farm_size_hectares": 2.5},
        "payment_method_id": "pm_card_visa",  # Test card
        "user_data": {"avg_product_rating": 4.5}
    }

    return create_order_with_complete_saga(test_order, db)

@real_marketplace_router.post("/test/order-payment-declined")
def test_order_payment_declined(db: Session = Depends(get_db)):
    """
    Test: Créer commande, paiement ÉCHOUE
    (Utilise test card qui est toujours déclinée)
    """
    test_order = {
        "farmer_id": 5,
        "buyer_id": 10,
        "order_id": f"TEST-DECLINED-{datetime.utcnow().timestamp()}",
        "crop_type": "tomato",
        "quantity_kg": 500,
        "order_value": 100000,
        "farm_id": 5,
        "farm_location": "Bamako",
        "latitude": 12.6552,
        "longitude": -8.0029,
        "iot_readings": {"temp": 28, "humidity": 65},
        "farm_data": {"fuel_liters": 50},
        "payment_method_id": "pm_card_declined",  # ← Test card that FAILS
        "user_data": {"avg_product_rating": 3.0}
    }

    try:
        return create_order_with_complete_saga(test_order, db)
    except HTTPException as e:
        return {
            "status": "failed_as_expected",
            "error": str(e.detail),
            "explanation": "Payment declined - SAGA should have compensated"
        }

# ============ REAL DATA DEBUG ENDPOINTS ============

@real_marketplace_router.get("/debug/init-real-data")
def debug_init_real_data():
    """Debug: Initialiser tous les services de données réelles"""
    from services.real_data_service import initialize_real_data_services

    try:
        initialize_real_data_services()
        return {"status": "initialized", "message": "All real data services ready"}
    except Exception as e:
        return {"error": str(e)}

@real_marketplace_router.get("/debug/all-prices")
def debug_all_prices():
    """Debug: Récupérer tous les prix Mali"""
    crops = ["rice", "millet", "corn", "tomato", "groundnut"]
    prices = {}

    for crop in crops:
        prices[crop] = RealPriceService.get_crop_price(crop)

    return prices

@real_marketplace_router.get("/debug/market-intelligence")
def debug_market_intelligence():
    """Debug: Intelligence marché complète"""
    return {
        "current_prices": {
            "rice": RealPriceService.get_crop_price("rice"),
            "tomato": RealPriceService.get_crop_price("tomato"),
        },
        "price_forecasts": {
            "rice": RealPriceService.get_market_forecast("rice", weeks=4),
            "tomato": RealPriceService.get_market_forecast("tomato", weeks=4),
        },
        "weather_bamako": RealWeatherService.get_rainfall_forecast(12.6552, -8.0029),
        "government_data": RealGovernmentDataService.get_crop_production_data("Bamako", "tomato")
    }
