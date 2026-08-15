"""
Regional Expansion Service - Phase 4.2 : Expansion Régionale

Fonctionnalités :
- Interface multi-langues (français + langues locales africaines)
- Intégration API météo et données gouvernementales régionales
- Prêt cloud AWS/GCP pour scalabilité mondiale
- Métriques d'utilisateurs dans 5 pays africains
"""

import logging
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

import models

logger = logging.getLogger("regional_expansion_service")

SUPPORTED_COUNTRIES = [
    {"code": "MLI", "name": "Mali"},
    {"code": "SEN", "name": "Sénégal"},
    {"code": "GHA", "name": "Ghana"},
    {"code": "KEN", "name": "Kenya"},
    {"code": "CIV", "name": "Côte d'Ivoire"}
]

SUPPORTED_LANGUAGES = {
    "french": {"name": "Français", "native_name": "Français"},
    "bambara": {"name": "Bambara", "native_name": "Bamanankan"},
    "peul": {"name": "Peul", "native_name": "Fulfulde"},
    "soninke": {"name": "Soninké", "native_name": "Sarang"},
    "swahili": {"name": "Swahili", "native_name": "Kiswahili"},
    "wolof": {"name": "Wolof", "native_name": "Wolof"},
    "hausa": {"name": "Haoussa", "native_name": "Hausa"}
}

UI_TRANSLATIONS = {
    "french": {
        "welcome": "Bienvenue sur AgroSmart Nexus",
        "weather": "Météo locale",
        "government_news": "Données gouvernementales",
        "export": "Exportation conforme",
        "support": "Support local"
    },
    "bambara": {
        "welcome": "AgroSmart Nexus ye mita",
        "weather": "Sunu ji dɔn",
        "government_news": "Kɛlɛkɛya ka wulu",
        "export": "Ka taa fɔlɔra",
        "support": "Sariya kɔrɔ"
    },
    "peul": {
        "welcome": "AgroSmart Nexus e jam",
        "weather": "Enndam ngun",
        "government_news": "Holluɗe kawtal",
        "export": "Jokke tawa",
        "support": "Jokkondiral"
    },
    "soninke": {
        "welcome": "AgroSmart Nexus ka suuru",
        "weather": "Jeri ani nɛgɛn",
        "government_news": "Kosɛnna la",
        "export": "Sɛtu ka taa",
        "support": "Sariya"
    }
}

REGIONAL_WEATHER_PARTNERS = {
    "SEN": "https://api.open-meteo.com/v1/forecast",
    "GHA": "https://api.open-meteo.com/v1/forecast",
    "KEN": "https://api.open-meteo.com/v1/forecast",
    "CIV": "https://api.open-meteo.com/v1/forecast",
    "MLI": "https://api.open-meteo.com/v1/forecast"
}

GOVERNMENT_DATA_SOURCES = {
    "MLI": {
        "name": "Ministère de l'Agriculture du Mali",
        "endpoint": "https://api.gov.ml/agriculture/latest"
    },
    "SEN": {
        "name": "Ministère de l'Agriculture du Sénégal",
        "endpoint": "https://api.gouv.sn/agriculture/latest"
    },
    "GHA": {
        "name": "Ministry of Food and Agriculture Ghana",
        "endpoint": "https://api.mofa.gov.gh/agriculture/latest"
    },
    "KEN": {
        "name": "Ministry of Agriculture Kenya",
        "endpoint": "https://api.kilimo.go.ke/agriculture/latest"
    },
    "CIV": {
        "name": "Ministry of Agriculture Côte d'Ivoire",
        "endpoint": "https://api.gouv.ci/agriculture/latest"
    }
}

COUNTRY_FROM_REGION = {
    "Bamako": "Mali",
    "Sikasso": "Mali",
    "Mopti": "Mali",
    "Kayes": "Mali",
    "Tombouctou": "Mali",
    "Gao": "Mali",
    "Dakar": "Sénégal",
    "Thiès": "Sénégal",
    "Accra": "Ghana",
    "Nairobi": "Kenya",
    "Abidjan": "Côte d'Ivoire"
}

class RegionalExpansionService:
    """Service d'expansion régionale et internationalisation."""

    @staticmethod
    def get_supported_languages() -> List[Dict[str, Any]]:
        language_details = {
            "french": {
                "description": "Interface en Français pour l'administration et les agriculteurs francophones.",
                "vocabulary_examples": ["bonjour", "météo", "agriculture", "export"]
            },
            "bambara": {
                "description": "Interface vocale et textuelle pour les utilisateurs parlant Bambara.",
                "vocabulary_examples": ["sɛnɛ", "ka ji dɔn", "maïs", "riz"]
            },
            "peul": {
                "description": "Support local pour les utilisateurs Fulfulde / Peul.",
                "vocabulary_examples": ["demal", "jam ndiyam", "soodugo", "fuddirgal"]
            },
            "soninke": {
                "description": "Support en Soninké pour l'accès local et inclusif.",
                "vocabulary_examples": ["ala xere", "ka bo", "sabara", "jari"]
            },
            "swahili": {
                "description": "Interface Swahili pour l'Afrique de l'Est.",
                "vocabulary_examples": ["habari", "kilimo", "maji", "zao"]
            },
            "wolof": {
                "description": "Interface Wolof pour l'Afrique de l'Ouest.",
                "vocabulary_examples": ["nanga def", "bët", "taleem", "lépp"]
            },
            "hausa": {
                "description": "Interface Haoussa pour l'Afrique de l'Ouest.",
                "vocabulary_examples": ["sannu", "noma", "ruwan sama", "hatsi"]
            }
        }
        return [
            {
                "code": code,
                "name": info["name"],
                "native_name": info["native_name"],
                "supported": True,
                "description": language_details.get(code, {}).get("description", ""),
                "vocabulary_examples": language_details.get(code, {}).get("vocabulary_examples", [])
            }
            for code, info in SUPPORTED_LANGUAGES.items()
        ]

    @staticmethod
    def get_ui_translations(language_code: str) -> Dict[str, Any]:
        return UI_TRANSLATIONS.get(language_code, UI_TRANSLATIONS["french"])

    @staticmethod
    def fetch_partner_weather_data(lat: float, lon: float, country_code: str) -> Dict[str, Any]:
        url = REGIONAL_WEATHER_PARTNERS.get(country_code, REGIONAL_WEATHER_PARTNERS["MLI"])
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "temperature_2m,precipitation,relativehumidity_2m,weathercode",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": 7,
                "timezone": "Africa/Brazzaville"
            }
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()
            data = response.json()
            return {
                "source": "PartnerWeatherAPI",
                "country_code": country_code,
                "weather_data": data,
                "fetched_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.warning(f"Partner weather API failed for {country_code}: {e}")
            return {
                "source": "Fallback",
                "country_code": country_code,
                "weather_data": {},
                "error": str(e),
                "fetched_at": datetime.utcnow().isoformat()
            }

    @staticmethod
    def fetch_government_agriculture_updates(country_code: str) -> Dict[str, Any]:
        source = GOVERNMENT_DATA_SOURCES.get(country_code)
        if not source:
            return {
                "country_code": country_code,
                "source": "Unknown",
                "status": "unsupported",
                "updates": [],
                "message": "Pays non couvert pour l'instant"
            }

        try:
            response = requests.get(source["endpoint"], timeout=6)
            response.raise_for_status()
            data = response.json()
            return {
                "country_code": country_code,
                "source": source["name"],
                "status": "success",
                "updates": data,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.warning(f"Government updates failed for {country_code}: {e}")
            return {
                "country_code": country_code,
                "source": source["name"],
                "status": "fallback",
                "updates": [
                    {
                        "headline": "Données régionales indisponibles",
                        "detail": "Les données gouvernementales régionales ne sont pas accessibles actuellement."
                    }
                ],
                "error": str(e),
                "retrieved_at": datetime.utcnow().isoformat()
            }

    @staticmethod
    def get_expansion_metrics(db: Session) -> Dict[str, Any]:
        active_users = db.query(models.User).filter(models.User.is_active == True).all()
        country_counts: Dict[str, int] = {}

        for user in active_users:
            country = getattr(user, "country", None)
            if not country:
                country = COUNTRY_FROM_REGION.get(user.region, "Mali")
            country_counts[country] = country_counts.get(country, 0) + 1

        supported_counties = [c["name"] for c in SUPPORTED_COUNTRIES]
        supported_metrics = {country: country_counts.get(country, 0) for country in supported_counties}
        active_countries = len([count for count in supported_metrics.values() if count > 0])

        return {
            "supported_countries": supported_metrics,
            "active_countries": active_countries,
            "active_users_total": len(active_users),
            "target_countries": len(supported_counties),
            "goal_met": active_countries >= len(supported_counties),
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def assess_cloud_scalability() -> Dict[str, Any]:
        aws_ready = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
        gcp_ready = bool(os.getenv("GOOGLE_CLOUD_PROJECT") and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        docker_ready = bool(os.getenv("DOCKER_HOST") or os.getenv("DOCKER_TLS_VERIFY"))

        return {
            "cloud_infrastructure": {
                "aws": {
                    "ready": aws_ready,
                    "notes": "Prêt pour EKS, RDS et CloudWatch" if aws_ready else "Variables AWS manquantes"
                },
                "gcp": {
                    "ready": gcp_ready,
                    "notes": "Prêt pour GKE, Cloud SQL et Stackdriver" if gcp_ready else "Variables GCP manquantes"
                }
            },
            "docker_support": {
                "ready": docker_ready,
                "notes": "Prêt pour conteneurisation et déploiement multi-zone" if docker_ready else "Configuration Docker manquante"
            },
            "scalability_recommendations": [
                "Déployer sur AWS EKS ou GCP GKE pour la scalabilité mondiale",
                "Utiliser RDS / Cloud SQL pour la base de données relationnelle",
                "Activer le monitoring CloudWatch ou Stackdriver pour métriques" 
            ],
            "timestamp": datetime.utcnow().isoformat()
        }


# Fonctions utilitaires pour l'API

def get_supported_languages() -> List[Dict[str, Any]]:
    return RegionalExpansionService.get_supported_languages()


def get_ui_translations(language_code: str) -> Dict[str, Any]:
    return RegionalExpansionService.get_ui_translations(language_code)


def fetch_partner_weather_data(lat: float, lon: float, country_code: str) -> Dict[str, Any]:
    return RegionalExpansionService.fetch_partner_weather_data(lat, lon, country_code)


def fetch_government_agriculture_updates(country_code: str) -> Dict[str, Any]:
    return RegionalExpansionService.fetch_government_agriculture_updates(country_code)


def get_expansion_metrics(db: Session) -> Dict[str, Any]:
    return RegionalExpansionService.get_expansion_metrics(db)


def assess_cloud_scalability() -> Dict[str, Any]:
    return RegionalExpansionService.assess_cloud_scalability()
