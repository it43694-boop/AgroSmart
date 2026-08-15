import datetime
from database import SessionLocal, init_db
import models


def seed_training_data():
    init_db()
    db = SessionLocal()
    try:
        user = db.query(models.User).first()
        if user is None:
            user = models.User(
                full_name="Demo Farmer",
                email="demo@example.com",
                username="demo_farmer",
                hashed_password="demo-password",
                role="farmer",
                is_validated=True,
                is_active=True,
            )
            db.add(user)
            db.flush()

        existing = db.query(models.WeatherData).count()
        if existing == 0:
            samples = [
                models.WeatherData(location="Bamako", latitude=12.65, longitude=-8.00, temperature=31.0, humidity=68.0, precipitation=8.0, wind_speed=12.0, pressure=1012.0, soil_moisture=54.0, timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=3)),
                models.WeatherData(location="Ségou", latitude=13.45, longitude=-6.27, temperature=29.5, humidity=72.0, precipitation=12.0, wind_speed=10.0, pressure=1010.0, soil_moisture=58.0, timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=2)),
                models.WeatherData(location="Mopti", latitude=14.49, longitude=-4.20, temperature=34.0, humidity=55.0, precipitation=4.0, wind_speed=15.0, pressure=1008.0, soil_moisture=38.0, timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=1)),
            ]
            db.add_all(samples)

        if db.query(models.SensorReading).count() == 0:
            sensor_samples = [
                models.SensorReading(user_id=user.id, sensor_type="temperature", value=31.0, unit="°C", location="Bamako", timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=3)),
                models.SensorReading(user_id=user.id, sensor_type="humidity", value=68.0, unit="%", location="Bamako", timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=3)),
                models.SensorReading(user_id=user.id, sensor_type="soil_moisture", value=54.0, unit="%", location="Bamako", timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=3)),
            ]
            db.add_all(sensor_samples)

        if db.query(models.YieldPrediction).count() == 0:
            crop = db.query(models.Crop).filter(models.Crop.owner_id == user.id).first()
            if crop is None:
                crop = models.Crop(name="Maïs demo", surface=2.5, owner_id=user.id)
                db.add(crop)
                db.flush()

            yield_samples = [
                models.YieldPrediction(user_id=user.id, crop_id=crop.id, predicted_yield=1200.0, actual_yield=1320.0, factors_used='{"weather_data": {"temperature": 31.0, "precipitation": 8.0, "humidity": 68.0}, "crop_data": {"region": "Bamako", "soil_moisture": 54.0}}', prediction_date=datetime.datetime.utcnow() - datetime.timedelta(days=2)),
                models.YieldPrediction(user_id=user.id, crop_id=crop.id, predicted_yield=1100.0, actual_yield=1180.0, factors_used='{"weather_data": {"temperature": 29.5, "precipitation": 12.0, "humidity": 72.0}, "crop_data": {"region": "Ségou", "soil_moisture": 58.0}}', prediction_date=datetime.datetime.utcnow() - datetime.timedelta(days=1)),
            ]
            db.add_all(yield_samples)

        db.commit()
        print("Données d'entraînement insérées avec succès")
    finally:
        db.close()


if __name__ == "__main__":
    seed_training_data()
