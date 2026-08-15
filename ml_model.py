import os
import json

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    from joblib import dump, load

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    dump = load = None
try:
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.pipeline import Pipeline
except Exception:
    ColumnTransformer = OneHotEncoder = StandardScaler = Pipeline = None

MODEL_PATH = os.path.join(os.path.dirname(__file__), "crop_advice_model.joblib")
MAPS_PATH = os.path.join(os.path.dirname(__file__), "models", "soil_crop_maps.json")

FEATURE_NAMES = [
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
]

LABELS = [
    "arroser",
    "attendre",
    "planter",
    "recolter",
    "continue",
]


def _rule_based_action(temperature: float, rainfall: float, soil_moisture: float, soil_humidity: float, ndvi: float, historical_rainfall: float, historical_temperature: float, days_since_planting: int) -> str:
    if soil_moisture < 0.2 and soil_humidity < 0.25 and rainfall < 5:
        return "arroser"
    if ndvi < 0.35 and historical_rainfall < 50:
        return "arroser"
    if days_since_planting > 80 and soil_moisture > 0.5 and ndvi > 0.45:
        return "recolter"
    if temperature > 32 and rainfall < 3 and historical_temperature > 30:
        return "attendre"
    if days_since_planting < 10 and soil_moisture > 0.4 and ndvi > 0.3:
        return "planter"
    if rainfall > 150 and soil_humidity > 0.55 and ndvi > 0.5:
        return "continue"
    return "attendre"


def build_sample_training_data():
    # Génère un jeu de données synthétique plus grand et réaliste
    try:
        import pandas as pd
    except Exception:
        pd = None

    n_samples = 1200
    records = []
    soil_choices = ["sableux", "loam", "argileux"]
    crop_choices = ["mil", "sorgho", "maïs", "riz", "arachide", "coton"]

    for _ in range(n_samples):
        temp = float(np.clip(np.random.normal(25, 6), 5, 45))
        if np.random.rand() < 0.2:
            rainfall = float(np.random.exponential(60))
        else:
            rainfall = float(np.random.exponential(15))
        rainfall = float(np.clip(rainfall, 0, 300))
        soil_moisture = float(np.clip(np.random.beta(2, 5), 0.01, 0.99))
        soil_humidity = float(np.clip(soil_moisture + np.random.normal(0, 0.08), 0.01, 0.99))
        ndvi = float(np.clip(0.2 + 0.6 * min(1.0, soil_moisture + rainfall / 500.0) + np.random.normal(0, 0.05), 0.05, 0.95))
        historical_rainfall = float(np.clip(rainfall + np.random.normal(15, 20), 0, 500))
        historical_temperature = float(np.clip(temp + np.random.normal(0, 2), 10, 40))
        days = int(np.random.randint(0, 121))
        soil = np.random.choice(soil_choices)
        crop = np.random.choice(crop_choices)

        label_str = _rule_based_action(temp, rainfall, soil_moisture, soil_humidity, ndvi, historical_rainfall, historical_temperature, days)
        label = LABELS.index(label_str)
        if np.random.rand() < 0.08:
            label = int(np.random.randint(0, len(LABELS)))

        records.append({
            "temperature": temp,
            "rainfall": rainfall,
            "soil_moisture": soil_moisture,
            "soil_humidity": soil_humidity,
            "ndvi": ndvi,
            "historical_rainfall": historical_rainfall,
            "historical_temperature": historical_temperature,
            "days_since_planting": days,
            "soil_type": soil,
            "current_crop": crop,
            "label": label,
        })

    if pd is not None:
        df = pd.DataFrame.from_records(records)
        X = df[[
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
        ]]
        y = df["label"].values
        return X, y

    # Fallback numpy arrays: encode categories as ints
    X_list = []
    y_list = []
    soil_map = {"sableux": 0, "loam": 1, "argileux": 2}
    crop_map = {"mil": 0, "sorgho": 1, "maïs": 2, "riz": 3, "arachide": 4, "coton": 5}
    for r in records:
        X_list.append([
            r["temperature"],
            r["rainfall"],
            r["soil_moisture"],
            r["soil_humidity"],
            r["ndvi"],
            r["historical_rainfall"],
            r["historical_temperature"],
            r["days_since_planting"],
            soil_map[r["soil_type"]],
            crop_map[r["current_crop"]],
        ])
        y_list.append(r["label"])
    return np.array(X_list, dtype=float), np.array(y_list, dtype=int)


def train_model(n_estimators: int = 100, test_size: float = 0.25, random_state: int = 42):
    """Entraîne le modèle `crop_advice_model.joblib`.

    Params:
      - n_estimators: nombre d'arbres pour RandomForest
      - test_size: proportion du test set
      - random_state: graine aléatoire
    """
    if not HAS_SKLEARN:
        return 0.0

    # Prefer real dataset if available
    X, y = None, None
    real = _load_real_training_data()
    if real is not None:
        X, y = real
    else:
        X, y = build_sample_training_data()

    # If X is a DataFrame with categorical columns, build a pipeline
    try:
        import pandas as pd
    except Exception:
        pd = None

    if pd is not None and hasattr(X, "columns"):
        # Use ColumnTransformer + OneHotEncoder for categorical features
        numeric_features = [
            "temperature",
            "rainfall",
            "soil_moisture",
            "soil_humidity",
            "ndvi",
            "historical_rainfall",
            "historical_temperature",
            "days_since_planting",
        ]
        categorical_features = ["soil_type", "current_crop"]

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_features),
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ],
            remainder="drop",
        )

        clf = Pipeline(steps=[("pre", preprocessor), ("clf", RandomForestClassifier(n_estimators=int(n_estimators), random_state=int(random_state)))])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=float(test_size), random_state=int(random_state))
        clf.fit(X_train, y_train)
        predictions = clf.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        # Persist the full pipeline
        dump(clf, MODEL_PATH)
        return float(accuracy)

    # Fallback: numeric numpy arrays
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=float(test_size), random_state=int(random_state))
    clf = RandomForestClassifier(n_estimators=int(n_estimators), random_state=int(random_state))
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    dump(clf, MODEL_PATH)
    return float(accuracy)


def load_model():
    if not HAS_SKLEARN:
        return None
    if os.path.exists(MODEL_PATH):
        return load(MODEL_PATH)
    accuracy = train_model()
    print(f"Modele entraine localement, accuracy={accuracy:.2f}")
    return load(MODEL_PATH)


def _load_real_training_data():
    """Charge un fichier CSV si présent à data/real_training.csv.
    Le fichier attendu doit contenir les colonnes: temperature,rainfall,soil_moisture,days_since_planting,soil_type,current_crop,label
    """
    try:
        import pandas as pd
    except Exception:
        return None

    path = os.path.join(os.path.dirname(__file__), "data", "real_training.csv")
    if not os.path.exists(path):
        return None

    try:
        df = pd.read_csv(path)
        required = [
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
        ]
        if not all(c in df.columns for c in required):
            return None

        # Build mappings for categorical features and persist them
        soil_types = sorted([str(x) for x in df["soil_type"].unique() if pd.notna(x)])
        crops = sorted([str(x) for x in df["current_crop"].unique() if pd.notna(x)])

        maps = {
            "soil_types": soil_types,
            "crops": crops,
        }

        os.makedirs(os.path.join(os.path.dirname(__file__), "models"), exist_ok=True)
        try:
            with open(MAPS_PATH, "w", encoding="utf-8") as mf:
                json.dump(maps, mf)
        except Exception:
            pass

        soil_map = {v: i for i, v in enumerate(soil_types)}
        crop_map = {v: i for i, v in enumerate(crops)}

        # Convert categorical columns to numeric using maps
        soil_vals = [soil_map.get(str(x), 0) for x in df["soil_type"].values]
        crop_vals = [crop_map.get(str(x), 0) for x in df["current_crop"].values]

        X = np.column_stack((
            df["temperature"].astype(float).values,
            df["rainfall"].astype(float).values,
            df["soil_moisture"].astype(float).values,
            df["soil_humidity"].astype(float).values,
            df["ndvi"].astype(float).values,
            df["historical_rainfall"].astype(float).values,
            df["historical_temperature"].astype(float).values,
            df["days_since_planting"].astype(int).values,
            np.array(soil_vals, dtype=float),
            np.array(crop_vals, dtype=float),
        ))
        y = df["label"].astype(int).values
        return X, y
    except Exception:
        return None


def predict_action(
    temperature: float,
    rainfall: float,
    soil_moisture: float,
    days_since_planting: int,
    soil_type: str = None,
    current_crop: str = None,
    soil_humidity: float = None,
    ndvi: float = None,
    historical_rainfall: float = None,
    historical_temperature: float = None,
) -> str:
    """Predict action. New optional features: satellite and Mali historical weather data.
    Backwards compatible: if model missing or libraries absent, falls back to rule-based action.
    """
    if not HAS_SKLEARN:
        return _rule_based_action(
            temperature,
            rainfall,
            soil_moisture,
            soil_humidity if soil_humidity is not None else 0.5,
            ndvi if ndvi is not None else 0.5,
            historical_rainfall if historical_rainfall is not None else rainfall,
            historical_temperature if historical_temperature is not None else temperature,
            days_since_planting,
        )

    model = load_model()

    # Load persisted maps if available, else fallback to sensible defaults
    soil_t = 1
    crop_t = 0
    try:
        if os.path.exists(MAPS_PATH):
            with open(MAPS_PATH, "r", encoding="utf-8") as mf:
                maps = json.load(mf)
                soil_list = maps.get("soil_types", [])
                crop_list = maps.get("crops", [])
                if soil_type is not None and soil_list:
                    soil_t = float(soil_list.index(soil_type) if soil_type in soil_list else 0)
                if current_crop is not None and crop_list:
                    crop_t = float(crop_list.index(current_crop) if current_crop in crop_list else 0)
    except Exception:
        pass

    # If model is a pipeline expecting DataFrame, build a one-row DataFrame
    try:
        import pandas as pd
    except Exception:
        pd = None

    if pd is not None:
        try:
            df = pd.DataFrame([{
                "temperature": float(temperature),
                "rainfall": float(rainfall),
                "soil_moisture": float(soil_moisture),
                "soil_humidity": float(soil_humidity if soil_humidity is not None else 0.5),
                "ndvi": float(ndvi if ndvi is not None else 0.5),
                "historical_rainfall": float(historical_rainfall if historical_rainfall is not None else rainfall),
                "historical_temperature": float(historical_temperature if historical_temperature is not None else temperature),
                "days_since_planting": int(days_since_planting),
                "soil_type": soil_type if soil_type is not None else "loam",
                "current_crop": current_crop if current_crop is not None else "mil",
            }])
            label = model.predict(df)[0]
            return LABELS[int(label)]
        except Exception:
            pass

    # Fallback to numeric array prediction
    X = np.array([[
        float(temperature),
        float(rainfall),
        float(soil_moisture),
        float(soil_humidity if soil_humidity is not None else 0.5),
        float(ndvi if ndvi is not None else 0.5),
        float(historical_rainfall if historical_rainfall is not None else rainfall),
        float(historical_temperature if historical_temperature is not None else temperature),
        int(days_since_planting),
        float(soil_t),
        float(crop_t),
    ]])
    try:
        label = model.predict(X)[0]
        return LABELS[int(label)]
    except Exception:
        return _rule_based_action(
            temperature,
            rainfall,
            soil_moisture,
            soil_humidity if soil_humidity is not None else 0.5,
            ndvi if ndvi is not None else 0.5,
            historical_rainfall if historical_rainfall is not None else rainfall,
            historical_temperature if historical_temperature is not None else temperature,
            days_since_planting,
        )
