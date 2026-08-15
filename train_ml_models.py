#!/usr/bin/env python3
"""
Script d'entraînement des modèles IA pour AgroSmart Phase 2
Génère des données d'exemple et entraîne les modèles LSTM et Gradient Boosting
"""

import numpy as np
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# Vérifier si les bibliothèques ML sont disponibles
try:
    import tensorflow as tf
    from tensorflow import keras
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, r2_score
    HAS_ML = True
    print("✅ TensorFlow et scikit-learn disponibles")
except ImportError:
    HAS_ML = False
    print("⚠️ TensorFlow/scikit-learn non disponibles - Mode simulation")

class MLModelTrainer:
    """Classe pour entraîner les modèles IA d'AgroSmart"""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.weather_scaler = None
        self.crop_scaler = None

        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            print(f"📁 Répertoire modèles créé: {models_dir}")

    def generate_weather_data(self, num_samples: int = 1000) -> pd.DataFrame:
        """Génère des données météo synthétiques pour le Mali"""
        print(f"🌤️ Génération de {num_samples} échantillons de données météo...")

        # Période de 2 ans
        start_date = datetime(2022, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(num_samples)]

        # Coordonnées Mali (Bamako et régions environnantes)
        lats = np.random.uniform(10.0, 15.0, num_samples)
        lons = np.random.uniform(-12.0, -6.0, num_samples)

        # Températures saisonnières (Mali - climat sahélien)
        day_of_year = np.array([d.timetuple().tm_yday for d in dates])
        base_temp = 25 + 10 * np.sin(2 * np.pi * day_of_year / 365)  # Saisonnalité
        temperatures = base_temp + np.random.normal(0, 3, num_samples)

        # Précipitations (saison des pluies mai-octobre)
        rainfall_season = np.sin(2 * np.pi * (day_of_year - 121) / 365)  # Pic en mai
        rainfall_season = np.maximum(0, rainfall_season)
        rainfall = rainfall_season * np.random.exponential(5, num_samples)

        # Humidité
        humidity = 40 + 30 * rainfall_season + np.random.normal(0, 5, num_samples)
        humidity = np.clip(humidity, 10, 90)

        # Vent
        wind_speed = np.random.exponential(2, num_samples)

        # Créer DataFrame
        data = pd.DataFrame({
            'date': dates,
            'latitude': lats,
            'longitude': lons,
            'temperature_celsius': temperatures,
            'rainfall_mm': rainfall,
            'humidity_percent': humidity,
            'wind_speed_kmh': wind_speed
        })

        return data

    def generate_crop_data(self, num_samples: int = 1000) -> pd.DataFrame:
        """Génère des données de rendement des cultures"""
        print(f"🌾 Génération de {num_samples} échantillons de données de cultures...")

        # Cultures principales du Mali
        crops = ['mil', 'sorgho', 'mais', 'arachide', 'coton', 'riz', 'niebe']
        crop_data = []

        for _ in range(num_samples):
            crop = np.random.choice(crops)

            # Facteurs influençant le rendement
            lat = np.random.uniform(10.0, 15.0)
            lon = np.random.uniform(-12.0, -6.0)
            soil_type = np.random.choice(['sableux', 'argileux', 'fertile', 'limoneux'])
            rainfall = np.random.uniform(200, 1200)  # mm/an
            temperature = np.random.uniform(20, 35)  # °C moyenne
            humidity = np.random.uniform(30, 80)  # %

            # Rendement basé sur les conditions (simplifié)
            base_yield = {
                'mil': 800, 'sorgho': 750, 'mais': 2000, 'arachide': 900,
                'coton': 300, 'riz': 2500, 'niebe': 600
            }[crop]

            # Modificateurs
            soil_modifier = {'sableux': 0.7, 'argileux': 0.8, 'fertile': 1.2, 'limoneux': 1.0}[soil_type]
            rain_modifier = min(1.5, max(0.3, rainfall / 600))
            temp_modifier = 1.0 if 22 <= temperature <= 32 else 0.8

            yield_kg_ha = base_yield * soil_modifier * rain_modifier * temp_modifier
            yield_kg_ha += np.random.normal(0, yield_kg_ha * 0.1)  # Bruit
            yield_kg_ha = max(0, yield_kg_ha)

            crop_data.append({
                'crop': crop,
                'latitude': lat,
                'longitude': lon,
                'soil_type': soil_type,
                'rainfall_mm': rainfall,
                'temperature_celsius': temperature,
                'humidity_percent': humidity,
                'yield_kg_ha': yield_kg_ha
            })

        return pd.DataFrame(crop_data)

    def train_weather_lstm(self, data: pd.DataFrame) -> bool:
        """Entraîne un modèle LSTM pour la prédiction météo"""
        if not HAS_ML:
            print("⚠️ TensorFlow non disponible - Simulation de l'entraînement")
            return False

        print("🧠 Entraînement du modèle LSTM météo...")

        try:
            # Préparation des données
            features = ['temperature_celsius', 'rainfall_mm', 'humidity_percent', 'wind_speed_kmh']
            target = 'temperature_celsius'  # Prédire la température

            # Normalisation
            self.weather_scaler = StandardScaler()
            scaled_data = self.weather_scaler.fit_transform(data[features])

            # Créer séquences pour LSTM (7 jours d'historique)
            sequence_length = 7
            X, y = [], []

            for i in range(len(scaled_data) - sequence_length):
                X.append(scaled_data[i:i+sequence_length])
                y.append(scaled_data[i+sequence_length, 0])  # Prédire température

            X = np.array(X)
            y = np.array(y)

            # Split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Modèle LSTM
            model = keras.Sequential([
                keras.layers.LSTM(50, activation='relu', input_shape=(sequence_length, len(features))),
                keras.layers.Dense(25, activation='relu'),
                keras.layers.Dense(1)
            ])

            model.compile(optimizer='adam', loss='mse', metrics=['mae'])

            # Entraînement
            history = model.fit(
                X_train, y_train,
                epochs=20,
                batch_size=32,
                validation_split=0.2,
                verbose=1
            )

            # Évaluation
            loss, mae = model.evaluate(X_test, y_test, verbose=0)
            print(f"✅ Modèle météo entraîné - Loss: {loss:.2f}, MAE: {mae:.2f}")
            # Sauvegarde
            model_path = os.path.join(self.models_dir, 'weather_lstm_model.h5')
            model.save(model_path)
            print(f"💾 Modèle météo sauvegardé: {model_path}")

            # Sauvegarde du scaler
            scaler_path = os.path.join(self.models_dir, 'weather_scaler.pkl')
            import joblib
            joblib.dump(self.weather_scaler, scaler_path)

            return True

        except Exception as e:
            print(f"❌ Erreur entraînement météo: {e}")
            return False

    def train_crop_recommendation_model(self, data: pd.DataFrame) -> bool:
        """Entraîne un modèle de recommandation de cultures"""
        if not HAS_ML:
            print("⚠️ Scikit-learn non disponible - Simulation de l'entraînement")
            return False

        print("🌾 Entraînement du modèle de recommandation de cultures...")

        try:
            # Encoder les variables catégorielles
            data_encoded = data.copy()
            data_encoded['crop_code'] = data_encoded['crop'].astype('category').cat.codes
            data_encoded['soil_code'] = data_encoded['soil_type'].astype('category').cat.codes

            # Features
            features = ['latitude', 'longitude', 'soil_code', 'rainfall_mm', 'temperature_celsius', 'humidity_percent']
            X = data_encoded[features]
            y = data_encoded['yield_kg_ha']

            # Normalisation
            self.crop_scaler = StandardScaler()
            X_scaled = self.crop_scaler.fit_transform(X)

            # Split
            X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

            # Modèle Gradient Boosting
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )

            model.fit(X_train, y_train)

            # Évaluation
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            print(f"✅ Modèle cultures entraîné - MSE: {mse:.2f}, R²: {r2:.2f}")
            # Sauvegarde
            model_path = os.path.join(self.models_dir, 'crop_recommendation_model.pkl')
            import joblib
            joblib.dump(model, model_path)
            print(f"💾 Modèle cultures sauvegardé: {model_path}")

            # Sauvegarde du scaler
            scaler_path = os.path.join(self.models_dir, 'crop_scaler.pkl')
            joblib.dump(self.crop_scaler, scaler_path)

            return True

        except Exception as e:
            print(f"❌ Erreur entraînement cultures: {e}")
            return False

    def save_training_metadata(self) -> None:
        """Sauvegarde les métadonnées de l'entraînement"""
        metadata = {
            'training_date': datetime.now().isoformat(),
            'has_tensorflow': HAS_ML,
            'models_trained': [],
            'data_samples': {
                'weather': 1000,
                'crops': 1000
            }
        }

        if HAS_ML:
            metadata['models_trained'] = ['weather_lstm', 'crop_recommendation']

        metadata_path = os.path.join(self.models_dir, 'training_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"📋 Métadonnées sauvegardées: {metadata_path}")

    def train_all_models(self) -> Dict[str, bool]:
        """Entraîne tous les modèles IA"""
        print("🚀 Démarrage de l'entraînement des modèles IA AgroSmart")
        print("=" * 60)

        results = {}

        # Génération des données
        weather_data = self.generate_weather_data(1000)
        crop_data = self.generate_crop_data(1000)

        # Entraînement des modèles
        results['weather_lstm'] = self.train_weather_lstm(weather_data)
        results['crop_recommendation'] = self.train_crop_recommendation_model(crop_data)

        # Métadonnées
        self.save_training_metadata()

        # Résumé
        print("\n" + "="*60)
        print("📊 RÉSULTATS DE L'ENTRAÎNEMENT")
        print("="*60)

        for model, success in results.items():
            status = "✅ Entraîné" if success else "❌ Échoué"
            print(f"{model}: {status}")

        successful = sum(results.values())
        print(f"\nModèles entraînés avec succès: {successful}/{len(results)}")

        if successful == len(results):
            print("🎉 Tous les modèles IA sont prêts pour AgroSmart !")
        else:
            print("⚠️ Certains modèles n'ont pas pu être entraînés.")

        return results

def main():
    """Fonction principale"""
    trainer = MLModelTrainer()
    results = trainer.train_all_models()

    # Sauvegarde des résultats pour référence
    results_path = os.path.join(trainer.models_dir, 'training_results.json')
    with open(results_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, indent=2)

if __name__ == "__main__":
    main()