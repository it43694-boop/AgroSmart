import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Load Mali market prices from local cache
MALI_PRICES_CACHE_PATH = os.path.join(os.path.dirname(__file__), "mali_market_prices.json")
_mali_prices_cache = None

def _load_mali_prices_cache():
    """Load Mali market prices from local JSON file."""
    global _mali_prices_cache
    if _mali_prices_cache is None:
        try:
            if os.path.exists(MALI_PRICES_CACHE_PATH):
                with open(MALI_PRICES_CACHE_PATH, 'r', encoding='utf-8') as f:
                    _mali_prices_cache = json.load(f)
            else:
                _mali_prices_cache = {}
        except Exception as e:
            print(f"[WARN] Failed to load Mali prices cache: {e}")
            _mali_prices_cache = {}
    return _mali_prices_cache


class MaliRealAPIs:
    """Integration with real APIs for Mali agricultural data"""
    
    @staticmethod
    def get_weather_real(lat, lon):
        """Get real weather from Open-Meteo (covers Mali)"""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "temperature_2m,precipitation,relativehumidity_2m,weathercode",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": 14,
                "timezone": "Africa/Bamako"
            }
            response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[WARN] Weather API failed: {e}")
            return None
    
    @staticmethod
    def get_commodity_prices_worldbank(country_code="MLI"):
        """Get commodity prices from World Bank API"""
        try:
            # World Bank commodity prices
            url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/NE.RSB.GNFS.CD?format=json&per_page=100"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[WARN] World Bank API failed: {e}")
            return None
    
    @staticmethod
    def get_fao_prices(crops=["221", "56", "15"]):  # Maize, Rice, Wheat
        """Get commodity prices from FAO FAOSTAT"""
        try:
            params = {
                "domain": "QCL",  # Crops and livestock
                "areaCodes": "157",  # Mali code
                "itemCodes": ",".join(crops),
                "elementCodes": "5312",  # Price received
                "years": "2023,2022",
                "format": "json"
            }
            url = "https://fenixservices2.fao.org/faostat/api/v1/en/data"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[WARN] FAO API failed: {e}")
            return None
    
    @staticmethod
    def get_chirps_rainfall(lat, lon, start_date="2024-01-01", end_date="2024-12-31"):
        """Get historical rainfall from CHIRPS (Climate Hazards Group)"""
        try:
            # CHIRPS provides historical rainfall data
            url = f"https://chc.ucsb.edu/data/chirps/timeseries/monthly/{lat:.2f}_{lon:.2f}.txt"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            # Parse the data
            data = []
            for line in response.text.split('\n')[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        data.append({
                            "date": parts[0],
                            "rainfall": float(parts[1])
                        })
            return data
        except Exception as e:
            print(f"[WARN] CHIRPS API failed: {e}")
            return None
    
    @staticmethod
    def get_sentinel_ndvi(lat, lon):
        """Get vegetation index from Sentinel Hub (requires API key)"""
        try:
            api_key = os.getenv("SENTINEL_API_KEY")
            if not api_key:
                return None
            
            # Simplified Sentinel-1/2 API call
            params = {
                "lat": lat,
                "lon": lon,
                "time_range": "2024-01-01/2024-12-31"
            }
            # Note: This would need proper authentication with Sentinel Hub
            return None
        except Exception as e:
            print(f"[WARN] Sentinel API failed: {e}")
            return None
    
    @staticmethod
    def get_fews_net_prices():
        """Get Mali market prices from FEWS NET API (real-time)"""
        try:
            # FEWS NET provides market prices for West Africa
            url = "https://api.reliefweb.int/v1/reports"
            params = {
                "filter[advanced-search]": '(country:Mali) AND (primary_country.iso3:mli)',
                "filter[fields][name]": "title,posted_at,body",
                "limit": 10,
                "sort": ["posted_at:desc"]
            }
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()
            data = response.json()
            
            # Extract basic market data (returns mostly text/reports, not structured prices)
            # This is useful for market trends but not direct prices
            if data and 'data' in data:
                print(f"[INFO] FEWS NET reports found: {len(data['data'])} records")
                return {"source": "FEWS NET", "status": "connected"}
        except Exception as e:
            print(f"[WARN] FEWS NET API failed: {e}")
        return None
    
    @staticmethod
    def get_fao_commodity_prices():
        """Get FAO commodity prices for Mali crops (using FAOSTAT)"""
        try:
            # FAO provides commodity price data via FAOSTAT
            # Mapping: Mali crops to FAO item codes
            crop_codes = {
                "mil": "103",  # Millet
                "sorgho": "104",  # Sorghum
                "maïs": "56",  # Maize
                "riz": "27",  # Rice
                "arachide": "223",  # Groundnuts
                "coton": "665",  # Cotton
            }
            
            prices = {}
            # Try to fetch from FAO for each crop
            for crop, code in crop_codes.items():
                try:
                    url = f"https://fenixservices2.fao.org/faostat/api/v1/en/data"
                    params = {
                        "domain": "QCL",  # Crops and livestock
                        "areaCodes": "157",  # Mali ISO code
                        "itemCodes": code,
                        "elementCodes": "5312",  # Price received by farmers
                        "years": "2023",
                        "format": "json"
                    }
                    resp = requests.get(url, params=params, timeout=5)
                    resp.raise_for_status()
                    fao_data = resp.json()
                    
                    if fao_data and 'data' in fao_data and len(fao_data['data']) > 0:
                        # Extract latest price (in FCFA/kg)
                        latest = fao_data['data'][0]
                        price = float(latest.get('Value', 0))
                        if price > 0:
                            prices[crop] = {"price": round(price, 2), "unit": "FCFA/kg", "source": "FAO FAOSTAT"}
                except Exception as e:
                    print(f"[WARN] FAO price fetch for {crop} failed: {e}")
            
            if prices:
                print(f"[INFO] FAO prices retrieved: {len(prices)} crops")
                return prices
        except Exception as e:
            print(f"[WARN] FAO commodity prices failed: {e}")
        return None
    
    @staticmethod
    def get_mali_market_prices():
        """Get Mali-specific market prices (aggregated from multiple sources)."""
        cache = _load_mali_prices_cache()
        
        if not cache or 'prices' not in cache:
            print("[INFO] No cached Mali prices available")
            return None
        
        base_prices = cache.get('prices', {})
        if base_prices:
            prices = {}
            for crop, price in base_prices.items():
                prices[crop] = {
                    "price": round(price, 2),
                    "unit": "FCFA/kg",
                    "source": "FAO FAOSTAT 2024 (Mali)",
                    "currency": "FCFA"
                }
            print(f"[SUCCESS] Using FAO real prices from cache: {len(prices)} crops")
            return prices

        fews_status = MaliRealAPIs.get_fews_net_prices()
        if fews_status:
            print("[INFO] FEWS NET returned status but no structured market prices")

        print("[INFO] No real market prices available")
        return None
    
    @staticmethod
    def get_regional_price_adjustment(lat: float, lon: float) -> float:
        """Get price adjustment factor based on region."""
        try:
            from mali_data import get_region_by_coords
            region = get_region_by_coords(lat, lon)
            cache = _load_mali_prices_cache()
            variations = cache.get('regional_variations', {})
            if region in variations:
                return variations[region].get('multiplier', 1.0)
        except:
            pass
        return 1.0

# Real-time data fetcher
def fetch_real_mali_data(lat, lon):
    """Fetch all real Mali data"""
    weather = MaliRealAPIs.get_weather_real(lat, lon)
    prices = MaliRealAPIs.get_mali_market_prices()
    rainfall_history = MaliRealAPIs.get_chirps_rainfall(lat, lon)
    
    return {
        "weather": weather,
        "prices": prices,
        "rainfall_history": rainfall_history
    }

# Utility: Get price source info
def get_market_price_source():
    """Identify which source provided the prices"""
    prices = MaliRealAPIs.get_mali_market_prices()
    if prices and len(prices) > 0:
        sample = list(prices.values())[0]
        return sample.get('source', 'Unknown')
    return 'No prices available'
