#!/usr/bin/env python3
"""
Diagnose: Compare weather between home page (app.js) and dedicated weather section (farmer-dashboard.js)
"""

import requests

BASE_URL = "http://127.0.0.1:8001"

print("=" * 70)
print("🔍 Diagnostic: Météo Accueil vs Météo Section")
print("=" * 70)

# Test 1: What coordinates does app.js use?
print("\n[1] Appel Dashboard (app.js) - Coordonnées par défaut")
print("-" * 70)
print("⚠️  app.js récupère lat/lon du formulaire HTML (#dashboard-lat, #dashboard-lon)")
print("   Valeurs par défaut probables: 0.0, 0.0")

response = requests.get(f"{BASE_URL}/dashboard/1?lat=0.0&lon=0.0", 
                       headers={'Authorization': 'Bearer fake_token'}, timeout=5)
if response.status_code in [200, 401]:
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        weather_home = data.get('weather', {})
        print(f"   Météo retournée:")
        print(f"     - Temp: {weather_home.get('temperature_celsius')}°C")
        print(f"     - Location: {weather_home.get('location')}")
        print(f"     - Source: {weather_home.get('source')}")

# Test 2: What coordinates does farmer-dashboard.js use?
print("\n[2] API /weather - farmer-dashboard.js (vraies coordonnées)")
print("-" * 70)
print("✅ farmer-dashboard.js utilise les vraies coordonnées de l'utilisateur")
print("   (lat=12.6392 ou depuis /api/virtualfarm/field)")

response = requests.get(f"{BASE_URL}/weather/?lat=12.6392&lon=-8.0029", timeout=5)
if response.status_code == 200:
    weather_section = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Météo retournée:")
    print(f"     - Temp: {weather_section.get('temperature_celsius')}°C")
    print(f"     - Location: {weather_section.get('location')}")
    print(f"     - Humidity: {weather_section.get('humidity')}%")
    print(f"     - Source: {weather_section.get('source')}")

# Test 3: Compare
print("\n[3] Comparaison")
print("-" * 70)

if response.status_code == 200 and 'weather_home' in locals():
    temp_home = weather_home.get('temperature_celsius', 0)
    temp_section = weather_section.get('temperature_celsius', 0)
    
    if abs(temp_home - temp_section) > 1:
        print(f"❌ Différence de température détectée!")
        print(f"   Accueil: {temp_home}°C (coords par défaut)")
        print(f"   Section: {temp_section}°C (vraies coords)")
    else:
        print(f"✅ Températures similaires")
else:
    print("⚠️  Impossible de comparer (pas accès au dashboard)")

print("\n[4] 🎯 Explication")
print("-" * 70)
print("La météo est différente parce que:")
print("  • L'ACCUEIL (app.js) utilise des coords du formulaire (0,0 par défaut)")
print("  • LA SECTION (farmer-dashboard.js) utilise les VRAIES coords de l'utilisateur")
print("\nSolution: Modifier app.js pour récupérer les vraies coordonnées!")
