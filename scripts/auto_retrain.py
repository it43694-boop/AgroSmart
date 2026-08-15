"""
Script d'automatisation : génère le CSV réaliste puis réentraîne les modèles.
Usage: python scripts/auto_retrain.py
"""
import subprocess
import sys
import json
import os

# Ensure project root is on sys.path so imports like 'ml_model' work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print('Generating real CSV dataset...')
subprocess.check_call([sys.executable, 'scripts/generate_real_training_csv.py'])

print('Retraining crop_advice model using in-project API...')
from ml_model import train_model
acc = train_model(n_estimators=150, test_size=0.2, random_state=42)
print(f'crop_advice accuracy: {acc:.4f}')

print('Retraining mali models...')
from mali_ml import mali_ml as mali_ml_instance
mali_ml_instance.train_crop_model()
mali_ml_instance.train_price_model()
print('mali models trained: crop_model.pkl, price_model.pkl')

summary = {
    'crop_advice_accuracy': acc,
    'files': ['crop_advice_model.joblib','crop_model.pkl','price_model.pkl']
}
print(json.dumps(summary, indent=2))
