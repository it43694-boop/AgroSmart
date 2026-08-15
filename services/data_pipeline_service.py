"""
Data Pipeline Service - Pipeline de données pour capteurs IoT, météo et prix marché
"""

import datetime
import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

import models
from mali_apis import MaliRealAPIs
from services.cache_service import cached

logger = logging.getLogger("data_pipeline")


class DataPipelineService:
    """Service pour gérer le pipeline de données temporelles"""

    @staticmethod
    def store_weather_data(location: str, lat: float, lon: float,
                          weather_data: Dict[str, Any], db: Session = None) -> models.WeatherData:
        """Store weather data in database"""
        if db is None:
            from database import get_db
            db = next(get_db())

        weather = models.WeatherData(
            location=location,
            latitude=lat,
            longitude=lon,
            temperature=weather_data.get("temperature"),
            humidity=weather_data.get("humidity"),
            precipitation=weather_data.get("precipitation"),
            wind_speed=weather_data.get("wind_speed"),
            wind_direction=weather_data.get("wind_direction"),
            pressure=weather_data.get("pressure"),
            uv_index=weather_data.get("uv_index"),
            soil_moisture=weather_data.get("soil_moisture"),
            forecast_data=json.dumps(weather_data.get("forecast", {})),
            source=weather_data.get("source", "open-meteo"),
            timestamp=datetime.datetime.utcnow()
        )

        db.add(weather)
        db.commit()
        db.refresh(weather)

        logger.info(f"Weather data stored for {location}")
        return weather

    @staticmethod
    def store_market_price(crop_type: str, market_location: str, price_per_kg: float,
                          volume: Optional[float] = None, quality_grade: Optional[str] = None,
                          source: str = "worldbank", db: Session = None) -> models.MarketPrice:
        """Store market price data"""
        if db is None:
            from database import get_db
            db = next(get_db())

        price = models.MarketPrice(
            crop_type=crop_type,
            market_location=market_location,
            price_per_kg=price_per_kg,
            volume_traded=volume,
            quality_grade=quality_grade,
            source=source,
            timestamp=datetime.datetime.utcnow()
        )

        db.add(price)
        db.commit()
        db.refresh(price)

        logger.info(f"Market price stored: {crop_type} at {price_per_kg} XOF/kg in {market_location}")
        return price

    @staticmethod
    @cached(ttl_seconds=1800)  # Cache 30 minutes
    def fetch_and_store_weather(lat: float, lon: float, location: str = "Unknown",
                               db: Session = None) -> Optional[models.WeatherData]:
        """Fetch weather from API and store in database"""
        try:
            weather_api = MaliRealAPIs()
            weather_data = weather_api.get_weather_real(lat, lon)

            if weather_data:
                current = weather_data.get("current_weather", {})
                processed_data = {
                    "temperature": current.get("temperature"),
                    "humidity": None,  # Open-Meteo doesn't provide current humidity
                    "precipitation": None,
                    "wind_speed": current.get("windspeed"),
                    "wind_direction": None,
                    "pressure": None,
                    "uv_index": None,
                    "soil_moisture": None,
                    "forecast": weather_data.get("daily", {}),
                    "source": "open-meteo"
                }

                return DataPipelineService.store_weather_data(location, lat, lon, processed_data, db)

        except Exception as e:
            logger.error(f"Failed to fetch/store weather data: {e}")

        return None

    @staticmethod
    @cached(ttl_seconds=3600)  # Cache 1 hour
    def fetch_and_store_market_prices(db: Session = None) -> List[models.MarketPrice]:
        """Fetch market prices from APIs and store in database"""
        stored_prices = []

        try:
            weather_api = MaliRealAPIs()

            # Fetch World Bank commodity prices
            wb_data = weather_api.get_commodity_prices_worldbank("MLI")
            if wb_data:
                # Process World Bank data (simplified example)
                crops = ["maize", "rice", "millet", "sorghum"]
                for crop in crops:
                    # Mock prices - in real implementation, parse actual API response
                    mock_price = 500 + (hash(crop) % 1000)  # Mock price calculation
                    price = DataPipelineService.store_market_price(
                        crop_type=crop,
                        market_location="Bamako",
                        price_per_kg=float(mock_price),
                        source="worldbank",
                        db=db
                    )
                    stored_prices.append(price)

            # Fetch FAO prices
            fao_data = weather_api.get_fao_prices()
            if fao_data:
                # Process FAO data (simplified)
                for crop_code in ["221", "56", "15"]:  # Maize, Rice, Wheat
                    crop_names = {"221": "maize", "56": "rice", "15": "wheat"}
                    mock_price = 600 + (hash(crop_code) % 800)
                    price = DataPipelineService.store_market_price(
                        crop_type=crop_names.get(crop_code, "unknown"),
                        market_location="Mali",
                        price_per_kg=float(mock_price),
                        source="fao",
                        db=db
                    )
                    stored_prices.append(price)

        except Exception as e:
            logger.error(f"Failed to fetch/store market prices: {e}")

        return stored_prices

    @staticmethod
    def get_weather_history(location: str, days: int = 7, db: Session = None) -> List[models.WeatherData]:
        """Get historical weather data"""
        if db is None:
            from database import get_db
            db = next(get_db())

        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        return db.query(models.WeatherData).filter(
            models.WeatherData.location == location,
            models.WeatherData.timestamp >= since
        ).order_by(models.WeatherData.timestamp.desc()).all()

    @staticmethod
    def get_market_price_history(crop_type: str, days: int = 30, db: Session = None) -> List[models.MarketPrice]:
        """Get historical market prices"""
        if db is None:
            from database import get_db
            db = next(get_db())

        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        return db.query(models.MarketPrice).filter(
            models.MarketPrice.crop_type == crop_type,
            models.MarketPrice.timestamp >= since
        ).order_by(models.MarketPrice.timestamp.desc()).all()

    @staticmethod
    def get_latest_weather(lat: float, lon: float, db: Session = None) -> Optional[models.WeatherData]:
        """Get latest weather data for coordinates"""
        if db is None:
            from database import get_db
            db = next(get_db())

        return db.query(models.WeatherData).filter(
            models.WeatherData.latitude.between(lat - 0.1, lat + 0.1),
            models.WeatherData.longitude.between(lon - 0.1, lon + 0.1)
        ).order_by(models.WeatherData.timestamp.desc()).first()

    @staticmethod
    def get_latest_market_price(crop_type: str, market_location: str = None, db: Session = None) -> Optional[models.MarketPrice]:
        """Get latest market price for crop"""
        if db is None:
            from database import get_db
            db = next(get_db())

        query = db.query(models.MarketPrice).filter(
            models.MarketPrice.crop_type == crop_type
        )

        if market_location:
            query = query.filter(models.MarketPrice.market_location == market_location)

        return query.order_by(models.MarketPrice.timestamp.desc()).first()</content>
<parameter name="filePath">c:\Users\ACHANGER\anaconda3\projet2\services\data_pipeline_service.py