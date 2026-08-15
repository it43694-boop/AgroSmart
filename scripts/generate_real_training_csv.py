"""
Génère un dataset synthétique réaliste pour `data/real_training.csv`.
Colonnes: temperature,rainfall,soil_moisture,soil_humidity,ndvi,historical_rainfall,historical_temperature,days_since_planting,soil_type,current_crop,label
"""
import os
import csv
import random
import numpy as np

OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)
PATH = os.path.join(OUT, "real_training.csv")

soil_types = ["sableux", "loam", "argileux"]
crops = ["mil", "sorgho", "maïs", "riz", "arachide", "coton"]


def rule_label(temp, rainfall, soil_moisture, soil_humidity, ndvi, hist_rainfall, hist_temp, days):
    # rules enriched with satellite / historical weather signals
    if soil_moisture < 0.2 and soil_humidity < 0.25 and rainfall < 5:
        return "arroser"
    if ndvi < 0.35 and hist_rainfall < 50:
        return "arroser"
    if days > 80 and soil_moisture > 0.5 and ndvi > 0.45:
        return "recolter"
    if temp > 32 and rainfall < 3 and hist_temp > 30:
        return "attendre"
    if days < 10 and soil_moisture > 0.4 and ndvi > 0.3:
        return "planter"
    if rainfall > 150 and soil_humidity > 0.55 and ndvi > 0.5:
        return "continue"
    return "attendre"

LABELS = {"arroser":0, "attendre":1, "planter":2, "recolter":3, "continue":4}

N = 2500
with open(PATH, "w", newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        "temperature",
        "rainfall",
        "soil_moisture",
        "soil_humidity",
        "ndvi",
        "historical_rainfall",
        "historical_temperature",
        "days_since_planting",
        "soil_type",
        "current_crop",
        "label",
    ])
    for _ in range(N):
        temp = float(np.clip(np.random.normal(25, 6), 5, 45))
        rainfall = float(np.clip(np.random.exponential(20 if np.random.rand() > 0.2 else 60), 0, 400))
        soil_moisture = float(np.clip(np.random.beta(2, 5), 0.01, 0.99))
        soil_humidity = float(np.clip(soil_moisture + np.random.normal(0, 0.08), 0.01, 0.99))
        ndvi = float(np.clip(0.2 + 0.6 * min(1.0, soil_moisture + rainfall / 500.0) + np.random.normal(0, 0.05), 0.05, 0.95))
        hist_rainfall = float(np.clip(rainfall + np.random.normal(15, 20), 0, 500))
        hist_temp = float(np.clip(temp + np.random.normal(0, 2), 10, 40))
        days = int(np.random.randint(0, 121))
        soil = random.choice(soil_types)
        crop = random.choice(crops)

        lbl_str = rule_label(temp, rainfall, soil_moisture, soil_humidity, ndvi, hist_rainfall, hist_temp, days)
        if random.random() < 0.06:
            lbl = random.randint(0, 4)
        else:
            lbl = LABELS[lbl_str]
        writer.writerow([
            f"{temp:.2f}",
            f"{rainfall:.2f}",
            f"{soil_moisture:.3f}",
            f"{soil_humidity:.3f}",
            f"{ndvi:.3f}",
            f"{hist_rainfall:.2f}",
            f"{hist_temp:.2f}",
            days,
            soil,
            crop,
            lbl,
        ])

print(f"Wrote {PATH}")
