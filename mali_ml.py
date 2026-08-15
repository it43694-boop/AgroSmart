import numpy as np
import os
import pickle
from mali_data import MALI_REGIONS, CROP_REQUIREMENTS, get_region_by_coords, get_suitable_crops

HAS_SKLEARN = True
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
except ImportError:
    HAS_SKLEARN = False

MODEL_VERSION = "1.0.0"  # Versioning pour le suivi des modèles

# ML Models for Mali Agriculture
class MaliAgricultureML:
    def __init__(self):
        self.crop_model = None
        self.price_model = None
        self.alert_model = None
        self.scaler = StandardScaler() if HAS_SKLEARN else None
        self.version = MODEL_VERSION
        self.load_or_train_models()
    
    def load_or_train_models(self):
        """Load existing models or train new ones"""
        if not HAS_SKLEARN:
            self.crop_model = None
            self.price_model = None
            self.alert_model = None
            return

        if os.path.exists("crop_model.pkl"):
            try:
                with open("crop_model.pkl", "rb") as f:
                    self.crop_model = pickle.load(f)
            except Exception as e:
                print(f"[WARN] Erreur chargement crop_model: {e}. Réentraînement...")
                self.train_crop_model()
        else:
            self.train_crop_model()
        
        if os.path.exists("price_model.pkl"):
            try:
                with open("price_model.pkl", "rb") as f:
                    self.price_model = pickle.load(f)
            except Exception as e:
                print(f"[WARN] Erreur chargement price_model: {e}. Réentraînement...")
                self.train_price_model()
        else:
            self.train_price_model()
    
    def train_crop_model(self):
        """Train model for crop recommendations"""
        if not HAS_SKLEARN:
            return

        # Generate synthetic training data for Mali regions
        X = []
        y = []
        
        # All possible crops across Mali
        crops_list = ["mil", "sorgho", "maïs", "riz", "arachide", "coton"]
        crop_to_id = {crop: i for i, crop in enumerate(crops_list)}
        
        for region, data in MALI_REGIONS.items():
            for crop in data["main_crops"]:
                # Skip if crop not in main list (e.g., "légumes")
                if crop not in crop_to_id:
                    continue
                    
                for _ in range(10):  # Generate 10 samples per crop per region
                    temp = np.random.uniform(15, 35)
                    rainfall = np.random.uniform(data["rainfall_min"], data["rainfall_max"])
                    soil_moisture = np.random.uniform(0.3, 0.8)
                    region_id = list(MALI_REGIONS.keys()).index(region)
                    
                    X.append([temp, rainfall, soil_moisture, region_id])
                    y.append(crop_to_id[crop])
        
        X = np.array(X)
        y = np.array(y)
        
        self.crop_model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.crop_model.fit(X, y)
        
        with open("crop_model.pkl", "wb") as f:
            pickle.dump(self.crop_model, f)
    
    def train_price_model(self):
        """Train model for price predictions"""
        if not HAS_SKLEARN:
            return

        # Generate synthetic training data for Mali commodity prices
        X = []
        y = []
        
        for month in range(1, 13):
            for region_id in range(len(MALI_REGIONS)):
                for _ in range(5):
                    rainfall = np.random.uniform(100, 800)
                    temp = np.random.uniform(15, 35)
                    # Price inversely correlated with supply (high rainfall = lower prices)
                    price = 300 - (rainfall * 0.2) + np.random.uniform(-50, 50)
                    
                    X.append([month, region_id, rainfall, temp])
                    y.append(max(100, price))  # Minimum price
        
        X = np.array(X)
        y = np.array(y)
        
        self.price_model = GradientBoostingRegressor(n_estimators=50, random_state=42)
        self.price_model.fit(X, y)
        
        with open("price_model.pkl", "wb") as f:
            pickle.dump(self.price_model, f)
    
    def recommend_crop(self, temperature, rainfall, soil_moisture, lat, lon):
        """ML-based crop recommendation"""
        region = get_region_by_coords(lat, lon)
        suitable = get_suitable_crops(region, temperature, rainfall)
        if HAS_SKLEARN and self.crop_model is not None:
            try:
                region_id = list(MALI_REGIONS.keys()).index(region)
                features = np.array([[temperature, rainfall, soil_moisture, region_id]])
                pred = self.crop_model.predict(features)[0]
                crops_list = ["mil", "sorgho", "maïs", "riz", "arachide", "coton"]
                return crops_list[pred]
            except Exception:
                pass
        return suitable[0] if suitable else "mil"
    
    def predict_price(self, month, lat, lon, rainfall, temperature):
        """ML-based price prediction"""
        region = get_region_by_coords(lat, lon)
        season_factor = 1.0
        if month in [6, 7, 8]:
            season_factor = 0.95
        elif month in [10, 11, 12]:
            season_factor = 1.05
        base_price = 250.0 + (rainfall - 300) * -0.1 + (temperature - 25) * 1.5
        base_price = max(120.0, min(900.0, base_price * season_factor))

        if HAS_SKLEARN and self.price_model is not None:
            try:
                region_id = list(MALI_REGIONS.keys()).index(region)
                features = np.array([[month, region_id, rainfall, temperature]])
                price = float(self.price_model.predict(features)[0])
                return max(120.0, price)
            except Exception:
                pass
        return base_price
    
    def detect_weather_alert(self, temperature, rainfall, soil_moisture):
        """Detect weather alerts based on ML analysis"""
        alerts = []
        
        if temperature > 40:
            alerts.append({
                "level": "critical",
                "message": "Chaleur extrême : risque de stress hydrique sévère",
                "action": "Augmenter l'irrigation immédiatement"
            })
        elif temperature > 35:
            alerts.append({
                "level": "warning",
                "message": "Température élevée détectée",
                "action": "Surveiller l'irrigation et l'humidité du sol"
            })
        
        if rainfall > 100:
            alerts.append({
                "level": "warning",
                "message": "Pluies torrentielles prévues",
                "action": "Protéger les cultures et améliorer le drainage"
            })
        elif rainfall < 10 and soil_moisture < 0.3:
            alerts.append({
                "level": "critical",
                "message": "Sécheresse détectée",
                "action": "Irrigation urgente requise"
            })
        
        if soil_moisture > 0.85:
            alerts.append({
                "level": "warning",
                "message": "Humidité du sol trop élevée",
                "action": "Risque de pourrissement racinaire"
            })
        
        return alerts

# Initialize global ML model
mali_ml = MaliAgricultureML()

def get_recommendation(temperature, rainfall, soil_moisture, days_since_planting, lat, lon, current_crop=None):
    """Get smart recommendation using ML"""
    region = get_region_by_coords(lat, lon)
    
    # Get ML-based crop recommendation
    recommended_crop = mali_ml.recommend_crop(temperature, rainfall, soil_moisture, lat, lon)
    
    # Get watering recommendation
    if soil_moisture < 0.3:
        watering = "Arrosage urgent recommandé"
    elif soil_moisture < 0.5:
        watering = "Arrosage conseillé dans les prochains jours"
    else:
        watering = "Sol suffisamment humide"
    
    # Get planting timing
    if temperature >= 20 and temperature <= 30 and rainfall > 50:
        planting = "Conditions favorables pour la plantation"
    elif temperature < 15:
        planting = "Température trop basse, attendre le réchauffement"
    elif rainfall < 20:
        planting = "Précipitations insuffisantes, planifier l'irrigation"
    else:
        planting = "Surveiller les conditions météorologiques"
    
    # Get weather alerts
    alerts = mali_ml.detect_weather_alert(temperature, rainfall, soil_moisture)
    
    recommendation = f"{planting}. {watering}"
    
    return {
        "recommendation": recommendation,
        "suggested_crop": recommended_crop,
        "region": region,
        "alerts": alerts,
        "details": [
            f"Région : {region}",
            f"Température : {temperature:.1f}°C",
            f"Pluie : {rainfall:.1f} mm",
            f"Humidité du sol : {soil_moisture:.2f}",
            f"Culture recommandée : {recommended_crop}",
            f"Jours depuis plantation : {days_since_planting}"
        ]
    }

def predict_revenue(crop_name, surface_ha, lat, lon, month=None):
    """Predict revenue using ML"""
    if month is None:
        month = 6  # Default to June
    
    try:
        # Get ML-predicted price
        base_price = mali_ml.predict_price(month, lat, lon, 400, 25)
        
        # Yield varies by crop
        yields = {
            "mil": 1.2, "sorgho": 1.5, "maïs": 2.0, 
            "riz": 2.5, "arachide": 1.8, "coton": 1.5
        }
        yield_per_ha = yields.get(crop_name, 1.5)
        
        revenue = surface_ha * yield_per_ha * base_price
        return float(revenue)
    except:
        return surface_ha * 1.5 * 250.0
