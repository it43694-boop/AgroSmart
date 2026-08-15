"""Module 5: Carbon Footprint + Reputation + Gamification"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from services.kafka_service import publish_event, EventType

logger = logging.getLogger(__name__)

class CarbonFootprintService:
    """Calculer et certifier carbon footprint"""

    @staticmethod
    def calculate_farm_carbon(farm_id: int, farm_data: Dict) -> Dict:
        """
        Calculer émissions CO2 equivalentes (Scope 1+2)
        """
        try:
            # Scope 1: Émissions directes
            fuel_liters = farm_data.get("fuel_consumption_liters", 0)
            fertilizer_kg = farm_data.get("fertilizer_kg", 0)
            livestock_count = farm_data.get("livestock_count", 0)

            scope1_kg_co2 = (
                fuel_liters * 2.3 +  # 2.3 kg CO2 per liter
                fertilizer_kg * 0.5 +  # 0.5 kg CO2 per kg N
                livestock_count * 100  # Avg livestock emissions
            )

            # Scope 2: Émissions indirectes (électricité)
            electricity_kwh = farm_data.get("electricity_kwh", 0)
            scope2_kg_co2 = electricity_kwh * 0.4  # 0.4 kg CO2 per kWh (Mali grid)

            # Total
            total_kg_co2 = scope1_kg_co2 + scope2_kg_co2
            total_tonnes_co2 = total_kg_co2 / 1000

            # Carbon intensity (per hectare)
            farm_size_ha = farm_data.get("farm_size_hectares", 1)
            carbon_intensity = total_tonnes_co2 / max(farm_size_ha, 1)

            result = {
                "farm_id": farm_id,
                "total_tonnes_co2": round(total_tonnes_co2, 3),
                "carbon_intensity_per_ha": round(carbon_intensity, 3),
                "scope1_kg": round(scope1_kg_co2, 2),
                "scope2_kg": round(scope2_kg_co2, 2),
                "sustainability_rating": "A" if carbon_intensity < 0.5 else "B" if carbon_intensity < 1.0 else "C",
                "reduction_potential": round((scope1_kg_co2 * 0.3) / 1000, 2),  # 30% potential
                "calculated_at": datetime.utcnow().isoformat()
            }

            publish_event(EventType.CARBON_CALCULATED, result)
            logger.info(f"✓ Carbon calculated: {farm_id} → {total_tonnes_co2}t CO2")
            return result

        except Exception as e:
            logger.error(f"✗ Carbon calculation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def mint_carbon_credits_nft(farm_id: int, tonnes_co2_offset: float) -> Dict:
        """
        Créer NFT vendables pour crédits carbones
        """
        try:
            nft_id = f"CARBON-NFT-{farm_id}-{datetime.utcnow().timestamp()}"

            carbon_nft = {
                "nft_id": nft_id,
                "farm_id": farm_id,
                "tonnes_co2_offset": tonnes_co2_offset,
                "nft_contract": "0x...",  # Ethereum/Polygon address
                "marketplace_price_usd": round(tonnes_co2_offset * 15, 2),  # $15/tonne
                "minted_at": datetime.utcnow().isoformat(),
                "expiry": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                "status": "listed",
                "blockchain": "polygon"
            }

            publish_event(EventType.TOKEN_MINTED, carbon_nft)
            logger.info(f"✓ Carbon NFT minted: {nft_id}")
            return carbon_nft

        except Exception as e:
            logger.error(f"✗ Carbon NFT minting failed: {e}")
            return {"error": str(e)}

class ReputationSystemService:
    """Système de réputation multi-critères"""

    @staticmethod
    def calculate_reputation_score(user_id: int, user_data: Dict) -> Dict:
        """
        Score agrégé: qualité + fiabilité + impact + transparence
        """
        try:
            # Critères individuels (0-100)
            quality_score = user_data.get("avg_product_rating", 4.0) * 20  # /5 → /100
            reliability_score = user_data.get("on_time_delivery_rate", 0.95) * 100
            impact_score = user_data.get("carbon_reduction_percentage", 0.20) * 100
            transparency_score = user_data.get("iot_verification_percentage", 0.85) * 100

            # Poids
            total_score = (
                quality_score * 0.25 +
                reliability_score * 0.30 +
                impact_score * 0.20 +
                transparency_score * 0.25
            )

            # Tier
            if total_score >= 85:
                tier = "Gold"
                badge = "🥇"
            elif total_score >= 70:
                tier = "Silver"
                badge = "🥈"
            elif total_score >= 50:
                tier = "Bronze"
                badge = "🥉"
            else:
                tier = "Standard"
                badge = "⭐"

            result = {
                "user_id": user_id,
                "overall_score": round(total_score, 2),
                "tier": tier,
                "badge": badge,
                "components": {
                    "quality": round(quality_score, 2),
                    "reliability": round(reliability_score, 2),
                    "impact": round(impact_score, 2),
                    "transparency": round(transparency_score, 2)
                },
                "breakdown": {
                    "transactions_completed": user_data.get("transaction_count", 0),
                    "avg_product_rating": user_data.get("avg_product_rating", 0),
                    "on_time_rate": user_data.get("on_time_delivery_rate", 0),
                    "carbon_reduction": user_data.get("carbon_reduction_percentage", 0)
                },
                "updated_at": datetime.utcnow().isoformat()
            }

            publish_event(EventType.REPUTATION_UPDATED, result)
            logger.info(f"✓ Reputation updated: {user_id} → {tier}")
            return result

        except Exception as e:
            logger.error(f"✗ Reputation calculation failed: {e}")
            return {"error": str(e)}

class GamificationService:
    """Badges, leaderboards, récompenses"""

    # Badge definitions
    BADGES = {
        "first_harvest": {
            "name": "First Harvest",
            "icon": "🌱",
            "requirement": "Complete 1st transaction",
            "points": 50
        },
        "carbon_neutral": {
            "name": "Carbon Neutral Farm",
            "icon": "🌍",
            "requirement": "Carbon intensity < 0.5t CO2/ha",
            "points": 500
        },
        "trusted_seller": {
            "name": "Trusted Seller",
            "icon": "⭐",
            "requirement": "100+ transactions, 4.5+ rating",
            "points": 250
        },
        "community_champion": {
            "name": "Community Champion",
            "icon": "👥",
            "requirement": "Join cooperative, 5+ group activities",
            "points": 300
        },
        "export_master": {
            "name": "Export Master",
            "icon": "🚢",
            "requirement": "5+ international transactions",
            "points": 400
        },
        "sustainable_hero": {
            "name": "Sustainable Hero",
            "icon": "🏆",
            "requirement": "Achieve A sustainability rating",
            "points": 600
        }
    }

    @staticmethod
    def award_badge(user_id: int, badge_key: str) -> Dict:
        """
        Attribuer badge et points
        """
        try:
            badge = GamificationService.BADGES.get(badge_key)

            if not badge:
                return {"error": f"Badge {badge_key} not found"}

            award = {
                "user_id": user_id,
                "badge_key": badge_key,
                "badge_name": badge["name"],
                "badge_icon": badge["icon"],
                "points_earned": badge["points"],
                "awarded_at": datetime.utcnow().isoformat(),
                "rarity": "rare" if badge["points"] > 300 else "common"
            }

            publish_event(EventType.BADGE_EARNED, award)
            logger.info(f"✓ Badge awarded: {user_id} → {badge['name']}")
            return award

        except Exception as e:
            logger.error(f"✗ Badge award failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_leaderboard(timeframe: str = "monthly") -> List[Dict]:
        """
        Top farmers par points, impact, reputation
        """
        try:
            # Mock leaderboard
            leaderboard = [
                {
                    "rank": 1,
                    "farmer_id": 5,
                    "name": "Malik",
                    "points": 2500,
                    "badges_count": 4,
                    "carbon_offset_tonnes": 5.2,
                    "transactions": 85
                },
                {
                    "rank": 2,
                    "farmer_id": 12,
                    "name": "Aïssatou",
                    "points": 2200,
                    "badges_count": 3,
                    "carbon_offset_tonnes": 4.1,
                    "transactions": 62
                },
                {
                    "rank": 3,
                    "farmer_id": 3,
                    "name": "Sekou",
                    "points": 1950,
                    "badges_count": 3,
                    "carbon_offset_tonnes": 3.8,
                    "transactions": 45
                }
            ]

            return leaderboard

        except Exception as e:
            logger.error(f"✗ Leaderboard fetch failed: {e}")
            return []

    @staticmethod
    def distribute_rewards(timeframe: str) -> Dict:
        """
        Distribuer récompenses (fin mois/trimestre)
        """
        rewards_pool = 10000  # $10k pool

        distribution = {
            "timeframe": timeframe,
            "total_pool_usd": rewards_pool,
            "distributions": [
                {"rank": 1, "amount_usd": 5000, "bonus_tokens": 100},
                {"rank": 2, "amount_usd": 3000, "bonus_tokens": 60},
                {"rank": 3, "amount_usd": 2000, "bonus_tokens": 40}
            ],
            "distributed_at": datetime.utcnow().isoformat()
        }

        logger.info(f"✓ Rewards distributed: ${rewards_pool}")
        return distribution

# Service instances
carbon_footprint = CarbonFootprintService()
reputation = ReputationSystemService()
gamification = GamificationService()
