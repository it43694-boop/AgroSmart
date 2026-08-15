#!/usr/bin/env python3
"""Detailed diagnostic of Open-Meteo response"""

import requests

print("=" * 70)
print("🔍 Diagnostic Détaillé: Open-Meteo Response Structure")
print("=" * 70)

params = {
    "latitude": 11.9,
    "longitude": -8.0,
    "current_weather": True,
    "hourly": "temperature_2m,precipitation,relativehumidity_2m,weathercode",
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
    "forecast_days": 7,
    "timezone": "Africa/Bamako"
}

response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
data = response.json()

print("\n[1] Current Weather Data")
print("-" * 70)
current_weather = data.get('current_weather', {})
print(f"Time: {current_weather.get('time')}")
print(f"Temperature: {current_weather.get('temperature')}°C")
print(f"Windspeed: {current_weather.get('windspeed')} km/h")

print("\n[2] Hourly Data Structure")
print("-" * 70)
hourly = data.get('hourly', {})
hourly_time = hourly.get('time', [])
hourly_temp = hourly.get('temperature_2m', [])
hourly_humidity = hourly.get('relativehumidity_2m', [])
hourly_precip = hourly.get('precipitation', [])

print(f"Number of hourly records: {len(hourly_time)}")
print(f"First 5 times: {hourly_time[:5]}")
print(f"First 5 temps: {hourly_temp[:5]}")
print(f"First 5 humidity: {hourly_humidity[:5]}")
print(f"First 5 precipitation: {hourly_precip[:5]}")

print("\n[3] Time Matching")
print("-" * 70)
current_time = current_weather.get('time')
print(f"Current time from current_weather: {current_time}")
print(f"Current time in hourly list: {current_time in hourly_time}")

if current_time in hourly_time:
    idx = hourly_time.index(current_time)
    print(f"Index in hourly: {idx}")
    print(f"Temperature at that index: {hourly_temp[idx]}°C")
    print(f"Humidity at that index: {hourly_humidity[idx]}%")
else:
    print("⚠️  Current time NOT found in hourly times!")
    print(f"Taking first record as fallback:")
    print(f"  Temperature: {hourly_temp[0] if hourly_temp else 'N/A'}°C")
    print(f"  Humidity: {hourly_humidity[0] if hourly_humidity else 'N/A'}%")

print("\n[4] Daily Data")
print("-" * 70)
daily = data.get('daily', {})
daily_time = daily.get('time', [])
temps_max = daily.get('temperature_2m_max', [])
temps_min = daily.get('temperature_2m_min', [])
precip_sum = daily.get('precipitation_sum', [])

print(f"Number of daily records: {len(daily_time)}")
print(f"First 3 days:")
for i in range(min(3, len(daily_time))):
    print(f"  {daily_time[i]}: {temps_min[i]:.0f}°C - {temps_max[i]:.0f}°C, rain {precip_sum[i]:.1f}mm")
