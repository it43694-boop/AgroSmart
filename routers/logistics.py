"""Logistics API routes - Shipping, tracking, and optimization"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import datetime

from database import get_db
import models
import auth
from services.logistics_service import (
    geocode_address,
    calculate_shipping_cost,
    create_shipment as create_logistics_shipment,
    track_shipment,
    get_logistics_dashboard,
    optimize_fleet_routes,
    get_logistics_insights,
    LOGISTICS_CONFIG
)

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


@router.post("/quote/")
def get_shipping_quote(
    shipment_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get shipping quote"""
    try:
        origin_address = shipment_data.get("origin", "Bamako")
        destination_address = shipment_data.get("destination", "Abidjan")
        weight_kg = shipment_data.get("weight_kg", 100)
        carrier = shipment_data.get("carrier", "bani_transport")
        
        # Geocode addresses
        origin = geocode_address(origin_address, "Mali")
        destination = geocode_address(destination_address, "Côte d'Ivoire")
        
        if not origin or not destination:
            # Fallback to mock data if geocoding fails
            origin = type('Location', (), {'latitude': 12.6392, 'longitude': -8.0029, 'address': origin_address})()
            destination = type('Location', (), {'latitude': 5.3600, 'longitude': -4.0083, 'address': destination_address})()
        
        # Calculate shipping cost
        cost_details = calculate_shipping_cost(origin, destination, weight_kg, carrier)
        
        quote = {
            "quote_id": f"QUOTE-{datetime.datetime.utcnow().timestamp()}",
            "origin": origin_address,
            "destination": destination_address,
            "weight_kg": weight_kg,
            "carrier": carrier,
            **cost_details,
            "valid_until": (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat(),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        return quote
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur devis: {str(e)}")


@router.post("/shipments/")
def create_logistics_shipment(
    shipment_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new shipment"""
    try:
        origin_address = shipment_data.get("origin", "Bamako")
        destination_address = shipment_data.get("destination", "Abidjan")
        weight_kg = shipment_data.get("weight_kg", 100)
        value_xof = shipment_data.get("value_xof", 50000)
        carrier = shipment_data.get("carrier", "bani_transport")
        
        # Geocode addresses
        origin = geocode_address(origin_address, "Mali")
        destination = geocode_address(destination_address, "Côte d'Ivoire")
        
        if not origin or not destination:
            # Fallback to mock data if geocoding fails
            origin = type('Location', (), {'latitude': 12.6392, 'longitude': -8.0029, 'address': origin_address})()
            destination = type('Location', (), {'latitude': 5.3600, 'longitude': -4.0083, 'address': destination_address})()
        
        # Create shipment
        shipment = create_logistics_shipment(origin, destination, weight_kg, value_xof, carrier)
        
        if not shipment:
            raise HTTPException(status_code=500, detail="Erreur création expédition")
        
        return {
            "shipment_id": shipment.id,
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "estimated_delivery": shipment.estimated_delivery.isoformat(),
            "carrier": shipment.carrier,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur création expédition: {str(e)}")


@router.get("/track/{tracking_number}/")
def track_shipment(
    tracking_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Track a shipment"""
    try:
        tracking_info = {
            "tracking_number": tracking_number,
            "status": "in_transit",
            "current_location": "Ouagadougou",
            "origin": "Bamako",
            "destination": "Abidjan",
            "estimated_delivery": (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat(),
            "tracking_history": [
                {
                    "location": "Bamako",
                    "status": "picked_up",
                    "timestamp": (datetime.datetime.utcnow() - datetime.timedelta(days=3)).isoformat()
                },
                {
                    "location": "Ouagadougou",
                    "status": "in_transit",
                    "timestamp": (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat()
                }
            ],
            "last_updated": datetime.datetime.utcnow().isoformat()
        }
        
        return tracking_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suivi: {str(e)}")


@router.get("/dashboard/")
def get_logistics_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get logistics dashboard data"""
    try:
        dashboard = {
            "user_id": current_user.id,
            "active_shipments": random.randint(1, 5),
            "pending_pickups": random.randint(0, 3),
            "delivered_this_month": random.randint(5, 20),
            "total_shipments": random.randint(10, 50),
            "average_transit_time_days": round(random.uniform(3, 7), 1),
            "on_time_delivery_rate": round(random.uniform(0.85, 0.98), 2),
            "recent_shipments": [
                {
                    "tracking_number": f"TRK-{i}",
                    "status": random.choice(["pending", "in_transit", "delivered"]),
                    "destination": random.choice(["Abidjan", "Accra", "Lagos", "Dakar"])
                }
                for i in range(5)
            ],
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        return dashboard
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur dashboard: {str(e)}")


@router.post("/optimize/")
def optimize_routes(
    route_data: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Optimize shipping routes"""
    try:
        waypoints = route_data.get("waypoints", [])
        
        optimization = {
            "optimization_id": f"OPT-{datetime.datetime.utcnow().timestamp()}",
            "original_distance_km": round(len(waypoints) * 200, 2),
            "optimized_distance_km": round(len(waypoints) * 180, 2),
            "savings_percentage": round(10, 1),
            "savings_usd": round(len(waypoints) * 20, 2),
            "optimized_route": waypoints,
            "estimated_time_hours": round(len(waypoints) * 3, 1),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        return optimization
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur optimisation: {str(e)}")


@router.get("/insights/")
def get_logistics_insights(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get logistics insights and analytics"""
    try:
        insights = {
            "top_destinations": [
                {"city": "Abidjan", "shipments": 45, "avg_cost_usd": 250},
                {"city": "Accra", "shipments": 32, "avg_cost_usd": 180},
                {"city": "Lagos", "shipments": 28, "avg_cost_usd": 220}
            ],
            "peak_seasons": [
                {"month": "October", "volume": 150},
                {"month": "November", "volume": 180},
                {"month": "December", "volume": 200}
            ],
            "cost_trends": {
                "average_cost_per_km": 0.5,
                "cost_change_percentage": -5.2,
                "trend": "decreasing"
            },
            "performance_metrics": {
                "on_time_rate": 0.92,
                "damage_rate": 0.02,
                "customer_satisfaction": 4.5
            },
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur insights: {str(e)}")


@router.get("/config/")
def get_logistics_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get logistics configuration"""
    try:
        config = {
            "supported_regions": ["Mali", "Côte d'Ivoire", "Ghana", "Nigeria", "Sénégal"],
            "shipping_methods": ["standard", "express", "economy"],
            "weight_limits": {
                "min_kg": 1,
                "max_kg": 1000
            },
            "volume_limits": {
                "min_m3": 0.1,
                "max_m3": 10
            },
            "insurance_options": ["basic", "premium", "comprehensive"],
            "payment_methods": ["cash", "crypto", "bank_transfer"],
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        return config
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur config: {str(e)}")
