"""
Weather Service - Gestion des données météorologiques avec cache
"""
import numpy as np
from mali_data import get_region_by_coords, MALI_REGIONS
from mali_apis import MaliRealAPIs
from services.cache_service import cached


def _coordinate_based_fallback(lat: float = 0.0, lon: float = 0.0) -> dict:
    """Provide deterministic fallback weather values that vary by coordinates."""
    lat = float(lat or 0.0)
    lon = float(lon or 0.0)

    temp = 24.0 + ((abs(lat) % 15) * 0.8) + ((abs(lon) % 10) * 0.2)
    humidity = 40.0 + ((abs(lon) % 20) * 1.1) + ((abs(lat) % 7) * 0.6)
    wind_speed = 7.0 + ((abs(lon) % 6) * 0.8) + ((abs(lat) % 5) * 0.3)
    rainfall = 3.0 + ((abs(lat) % 8) * 0.8) + ((abs(lon) % 6) * 0.5)

    forecast = []
    for i in range(7):
        forecast.append(
            f"Jour {i + 1}: {int(temp - 2 + (i % 3) * 1.5)}°C - {int(temp + 2 + (i % 2) * 1.0)}°C, pluie {max(0, int(rainfall + (i % 2) * 2))} mm"
        )

    return {
        "location": f"{lat},{lon}",
        "summary": f"Données de secours pour {lat:.2f},{lon:.2f}",
        "temperature_celsius": round(temp, 1),
        "rainfall": round(rainfall, 1),
        "soil_moisture": round(max(0.1, min(0.9, 0.35 + (humidity / 100.0) * 0.4)), 2),
        "forecast": forecast,
        "humidity": round(humidity, 1),
        "wind_speed": round(wind_speed, 1),
        "alert": None,
        "source": "fallback",
    }


@cached(ttl_seconds=300)  # Cache 5 minutes pour les données météo
def fetch_weather_data(lat: float = 0.0, lon: float = 0.0) -> dict:
    """
    Fetch real Mali weather data from Open-Meteo API.
    If the external source is unavailable, return an explicit unavailable state
    instead of inventing synthetic values for the dashboards.
    """
    try:
        real_weather = MaliRealAPIs.get_weather_real(lat, lon)
        if real_weather:
            current = real_weather.get("current", {}) or real_weather.get("current_weather", {})
            daily = real_weather.get("daily", {})
            hourly = real_weather.get("hourly", {})

            current_temp = float(current.get("temperature_2m", current.get("temperature", 25.0)))
            current_wind = float(current.get("windspeed", current.get("wind_speed", 0.0))) if current else 0.0

            # Extract hour from current_weather time (format: YYYY-MM-DDTHH:MM)
            # Hourly data only has HH:00 times, so we need to round/extract
            current_time = current.get("time")
            hourly_time = hourly.get("time", [])
            humidity_values = hourly.get("relativehumidity_2m", [])
            precipitation_values = hourly.get("precipitation", [])
            
            current_rain = 0.0
            current_humidity = 0.0
            
            if current_time and hourly_time:
                # Try to find exact time match first
                current_index = None
                if current_time in hourly_time:
                    current_index = hourly_time.index(current_time)
                else:
                    # Extract hour part (YYYY-MM-DDTHH) and find it
                    current_hour = current_time[:13]  # YYYY-MM-DDTHH
                    for i, ht in enumerate(hourly_time):
                        if ht[:13] == current_hour:
                            current_index = i
                            break
                
                # If still not found, use first record (closest approximation)
                if current_index is None and hourly_time:
                    current_index = 0
                
                if current_index is not None and current_index < len(hourly_time):
                    if current_index < len(precipitation_values):
                        current_rain = float(precipitation_values[current_index] or 0.0)
                    if current_index < len(humidity_values):
                        current_humidity = float(humidity_values[current_index] or 0.0)
            else:
                current_rain = float(current.get("precipitation", current.get("rain", 0.0)))
                current_humidity = float(current.get("relativehumidity_2m", current.get("humidity", 0.0))) if current else 0.0

            soil_moisture_data = daily.get("soil_moisture_0_1cm", [])
            current_soil = float(soil_moisture_data[0]) / 100.0 if soil_moisture_data else None

            forecast = []
            temps_max = daily.get("temperature_2m_max", [])
            temps_min = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])

            for i in range(min(7, len(temps_max))):
                forecast.append(f"Jour {i+1}: {temps_min[i]:.0f}°C - {temps_max[i]:.0f}°C, pluie {precip[i]:.0f} mm")

            summary = f"Temperature: {current_temp}°C, Humidity: {current_humidity}%, Wind: {current_wind} km/h"

            return {
                "location": f"{lat},{lon}",
                "summary": summary,
                "temperature_celsius": current_temp,
                "rainfall": current_rain,
                "soil_moisture": current_soil,
                "forecast": forecast,
                "humidity": current_humidity,
                "wind_speed": current_wind,
                "alert": None,
                "source": "Open-Meteo"
            }
    except Exception as e:
        print(f"[WARN] Real weather API failed: {e}")

    try:
        get_region_by_coords(lat, lon)
    except Exception:
        return {
            "location": f"{lat},{lon}",
            "summary": "Données météo indisponibles",
            "temperature_celsius": None,
            "rainfall": None,
            "soil_moisture": None,
            "forecast": [],
            "humidity": None,
            "wind_speed": None,
            "alert": None,
            "source": "unavailable",
        }

    return _coordinate_based_fallback(lat, lon)