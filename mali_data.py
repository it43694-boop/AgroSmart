import math
import re
import unicodedata


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFD", name.strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalized.strip()

# Mali Geographic Data with 7 Regions and their Cercles
MALI_REGIONS = {
    "Kayes": {
        "region_id": 1,
        "lat": 13.9, "lon": -11.4,
        "cercles": ["Kayes", "Yelimané", "Kéniéba", "Kita", "Niono", "Kolokani"],
        "main_crops": ["mil", "arachide", "maïs", "coton"],
        "rainfall_min": 400,
        "rainfall_max": 800,
        "elevation": 50,
        "population": "2.0M"
    },
    "Koulikoro": {
        "region_id": 2,
        "lat": 12.65, "lon": -8.0,
        "cercles": ["Koulikoro", "Kangaba", "Kéniéba", "Kolokani", "Niono", "Ségou"],
        "main_crops": ["mil", "riz", "maïs", "coton"],
        "rainfall_min": 600,
        "rainfall_max": 1000,
        "elevation": 150,
        "population": "2.4M"
    },
    "Bamako": {
        "region_id": 3,
        "lat": 12.65, "lon": -8.0,
        "cercles": ["Bamako"],
        "main_crops": ["légumes", "riz", "maïs"],
        "rainfall_min": 700,
        "rainfall_max": 1100,
        "elevation": 380,
        "population": "2.8M"
    },
    "Ségou": {
        "region_id": 4,
        "lat": 13.45, "lon": -6.27,
        "cercles": ["Ségou", "Markala", "Niono", "San", "Tominian"],
        "main_crops": ["riz", "mil", "coton", "arachide"],
        "rainfall_min": 500,
        "rainfall_max": 900,
        "elevation": 280,
        "population": "2.3M"
    },
    "Mopti": {
        "region_id": 5,
        "lat": 14.27, "lon": -4.18,
        "cercles": ["Mopti", "Timbuctou", "Douentza", "Youwarou", "Djenné", "Bandiagara"],
        "main_crops": ["riz", "mil", "sorgho", "coton"],
        "rainfall_min": 300,
        "rainfall_max": 700,
        "elevation": 130,
        "population": "2.7M"
    },
    "Tombouctou": {
        "region_id": 6,
        "lat": 16.77, "lon": -3.00,
        "cercles": ["Timbuctou", "Araouane", "Gourma-Rharous", "Niafounké", "Bandiagara"],
        "main_crops": ["riz", "mil", "sorgho"],
        "rainfall_min": 100,
        "rainfall_max": 350,
        "elevation": 115,
        "population": "0.7M"
    },
    "Gao": {
        "region_id": 7,
        "lat": 16.25, "lon": -0.05,
        "cercles": ["Gao", "Ansongo", "Ménaka", "Araouane"],
        "main_crops": ["mil", "sorgho"],
        "rainfall_min": 50,
        "rainfall_max": 300,
        "elevation": 250,
        "population": "0.6M"
    }
}

# Crop requirements for Mali agriculture
CROP_REQUIREMENTS = {
    "mil": {
        "min_temp": 20,
        "max_temp": 32,
        "min_rainfall": 300,
        "max_rainfall": 900,
        "planting_months": [4, 5, 6],  # April-June
        "harvest_months": [9, 10],  # September-October
        "soil_moisture_min": 0.3,
        "days_to_mature": 120,
        "yield_per_ha": 1.2,  # tons
        "irrigation_needed": False,
        "common_regions": ["Kayes", "Ségou", "Mopti", "Tombouctou", "Gao"]
    },
    "riz": {
        "min_temp": 25,
        "max_temp": 35,
        "min_rainfall": 600,
        "max_rainfall": 1500,
        "planting_months": [5, 6, 7],  # May-July
        "harvest_months": [10, 11],  # October-November
        "soil_moisture_min": 0.7,
        "days_to_mature": 135,
        "yield_per_ha": 2.5,  # tons
        "irrigation_needed": True,
        "common_regions": ["Koulikoro", "Ségou", "Mopti"]
    },
    "maïs": {
        "min_temp": 15,
        "max_temp": 30,
        "min_rainfall": 400,
        "max_rainfall": 1000,
        "planting_months": [4, 5],  # April-May
        "harvest_months": [9, 10],  # September-October
        "soil_moisture_min": 0.4,
        "days_to_mature": 110,
        "yield_per_ha": 2.0,  # tons
        "irrigation_needed": False,
        "common_regions": ["Kayes", "Koulikoro", "Ségou"]
    },
    "arachide": {
        "min_temp": 20,
        "max_temp": 30,
        "min_rainfall": 350,
        "max_rainfall": 800,
        "planting_months": [5, 6],  # May-June
        "harvest_months": [10, 11],  # October-November
        "soil_moisture_min": 0.35,
        "days_to_mature": 120,
        "yield_per_ha": 1.8,  # tons
        "irrigation_needed": False,
        "common_regions": ["Kayes", "Ségou"]
    },
    "coton": {
        "min_temp": 22,
        "max_temp": 32,
        "min_rainfall": 400,
        "max_rainfall": 1000,
        "planting_months": [4, 5, 6],  # April-June
        "harvest_months": [11, 12],  # November-December
        "soil_moisture_min": 0.4,
        "days_to_mature": 180,
        "yield_per_ha": 1.5,  # tons
        "irrigation_needed": False,
        "common_regions": ["Kayes", "Ségou", "Mopti"]
    },
    "sorgho": {
        "min_temp": 20,
        "max_temp": 33,
        "min_rainfall": 250,
        "max_rainfall": 700,
        "planting_months": [4, 5, 6],  # April-June
        "harvest_months": [9, 10],  # September-October
        "soil_moisture_min": 0.25,
        "days_to_mature": 130,
        "yield_per_ha": 1.5,  # tons
        "irrigation_needed": False,
        "common_regions": ["Tombouctou", "Gao", "Mopti"]
    }
}

# Mali cercles with coordinates
MALI_CERCLES = {
    "Kayes": [
        {"name": "Kayes", "lat": 14.16, "lon": -11.44},
        {"name": "Yelimané", "lat": 13.53, "lon": -12.79},
        {"name": "Kéniéba", "lat": 12.21, "lon": -10.00},
        {"name": "Kita", "lat": 12.04, "lon": -9.49},
    ],
    "Koulikoro": [
        {"name": "Koulikoro", "lat": 12.66, "lon": -8.01},
        {"name": "Kangaba", "lat": 11.92, "lon": -8.48},
        {"name": "Kolokani", "lat": 12.57, "lon": -7.94},
    ],
    "Bamako": [
        {"name": "Bamako", "lat": 12.65, "lon": -8.00},
    ],
    "Ségou": [
        {"name": "Ségou", "lat": 13.45, "lon": -6.27},
        {"name": "Markala", "lat": 13.75, "lon": -5.85},
        {"name": "Niono", "lat": 14.25, "lon": -5.99},
        {"name": "San", "lat": 13.30, "lon": -4.88},
        {"name": "Tominian", "lat": 13.79, "lon": -6.58},
    ],
    "Mopti": [
        {"name": "Mopti", "lat": 14.27, "lon": -4.18},
        {"name": "Djenné", "lat": 13.90, "lon": -4.33},
        {"name": "Bandiagara", "lat": 14.35, "lon": -3.63},
        {"name": "Douentza", "lat": 15.34, "lon": -2.48},
        {"name": "Youwarou", "lat": 14.92, "lon": -3.99},
    ],
    "Tombouctou": [
        {"name": "Timbuctou", "lat": 16.77, "lon": -3.00},
        {"name": "Araouane", "lat": 18.88, "lon": -3.53},
        {"name": "Gourma-Rharous", "lat": 16.84, "lon": -1.54},
        {"name": "Niafounké", "lat": 16.26, "lon": -5.24},
    ],
    "Gao": [
        {"name": "Gao", "lat": 16.27, "lon": -0.04},
        {"name": "Ansongo", "lat": 15.70, "lon": 0.50},
        {"name": "Ménaka", "lat": 16.45, "lon": 2.07},
    ]
}

def get_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def get_region_by_coords(lat, lon):
    """Find the Mali region by latitude/longitude coordinates"""
    min_distance = float('inf')
    closest_region = "Koulikoro"  # Default
    
    for region, data in MALI_REGIONS.items():
        dist = get_distance(lat, lon, data["lat"], data["lon"])
        if dist < min_distance:
            min_distance = dist
            closest_region = region
    
    return closest_region

def get_cercle_by_coords(lat, lon):
    """Find the Mali cercle by latitude/longitude coordinates"""
    min_distance = float('inf')
    closest_cercle = None
    closest_region = None
    
    for region, cercles in MALI_CERCLES.items():
        for cercle in cercles:
            dist = get_distance(lat, lon, cercle["lat"], cercle["lon"])
            if dist < min_distance:
                min_distance = dist
                closest_cercle = cercle["name"]
                closest_region = region
    
    return closest_cercle, closest_region


def get_region_coords(region_name: str):
    """Return latitude/longitude for a region or cercle name."""
    if not region_name:
        return None

    normalized = _normalize_name(region_name)
    for name, data in MALI_REGIONS.items():
        region_key = _normalize_name(name)
        if (
            normalized == region_key
            or normalized == region_key.rstrip('s')
            or region_key == normalized.rstrip('s')
            or normalized.startswith(region_key)
            or normalized.endswith(region_key)
            or region_key in normalized
        ):
            return data["lat"], data["lon"]

    for region, cercles in MALI_CERCLES.items():
        for cercle in cercles:
            cercle_key = _normalize_name(cercle["name"])
            if (
                normalized == cercle_key
                or normalized == cercle_key.rstrip('s')
                or cercle_key == normalized.rstrip('s')
                or normalized.startswith(cercle_key)
                or normalized.endswith(cercle_key)
                or cercle_key in normalized
            ):
                return cercle["lat"], cercle["lon"]

    return None


def get_suitable_crops(region, temperature, rainfall):
    """Get suitable crops for a region based on weather conditions"""
    suitable = []
    region_crops = MALI_REGIONS[region]["main_crops"]
    
    for crop in region_crops:
        if crop in CROP_REQUIREMENTS:
            req = CROP_REQUIREMENTS[crop]
            if (req["min_temp"] <= temperature <= req["max_temp"] and
                req["min_rainfall"] <= rainfall <= req["max_rainfall"]):
                suitable.append(crop)
    
    return suitable if suitable else region_crops

def get_watering_schedule(soil_moisture):
    """Get watering recommendation based on soil moisture"""
    if soil_moisture < 0.25:
        return "Arrosage urgent : Humidité critique"
    elif soil_moisture < 0.40:
        return "Arrosage recommandé : Humidité faible"
    elif soil_moisture < 0.60:
        return "Arrosage selon besoins de la culture"
    elif soil_moisture < 0.85:
        return "Humidité du sol adéquate"
    else:
        return "Arrosage non recommandé : Risque de saturation"

def get_crop_calendar(crop_name, month):
    """Get crop-specific advice for the current month"""
    if crop_name not in CROP_REQUIREMENTS:
        return "Informations de calendrier non disponibles"
    
    req = CROP_REQUIREMENTS[crop_name]
    
    if month in req["planting_months"]:
        return f"Période idéale pour planter {crop_name}"
    elif month in req["harvest_months"]:
        return f"Période de récolte pour {crop_name}"
    else:
        return f"Période d'entretien pour {crop_name}"
