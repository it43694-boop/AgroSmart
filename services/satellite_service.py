"""
Satellite Service - Gestion des données satellitaires avec cache
"""
import os
import requests
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from mali_data import get_region_by_coords, get_cercle_by_coords
from mali_apis import MaliRealAPIs
import schemas
from services.cache_service import cached


def _build_requests_session(retries: int = 2, backoff: float = 0.5):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


@cached(ttl_seconds=3600)  # Cache 1 heure pour les données satellites
def fetch_satellite(lat: float = 0.0, lon: float = 0.0) -> schemas.SatelliteResponse:
    """
    Fetch Mali satellite data for vegetation monitoring.
    If the external sources are unavailable, return an unavailable state rather than
    a synthesized NDVI value that could be displayed as if it were real data.
    """
    try:
        region = get_region_by_coords(lat, lon)
        cercle, _ = get_cercle_by_coords(lat, lon)
    except Exception:
        region = "Mali"
        cercle = "Unknown"

    try:
        sentinel_ndvi = MaliRealAPIs.get_sentinel_ndvi(lat, lon)
        if isinstance(sentinel_ndvi, (int, float)):
            return schemas.SatelliteResponse(
                summary=f"Données satellitaires reçues pour {region} ({cercle})",
                vegetation_index=float(np.clip(sentinel_ndvi, 0.0, 1.0)),
                advisor_note="Source: sentinel",
                image_url=None,
            )
    except Exception:
        pass

    try:
        rainfall_history = MaliRealAPIs.get_chirps_rainfall(lat, lon)
        if rainfall_history and len(rainfall_history) > 0:
            avg_rainfall = sum(r["rainfall"] for r in rainfall_history) / len(rainfall_history)
            vegetation_index_value = float(np.clip(avg_rainfall / 700.0, 0.20, 0.85))
            return schemas.SatelliteResponse(
                summary=f"Données satellitaires reçues pour {region} ({cercle})",
                vegetation_index=vegetation_index_value,
                advisor_note="Source: chirps",
                image_url=None,
            )
    except Exception:
        pass

    return schemas.SatelliteResponse(
        summary="Données satellitaires indisponibles",
        vegetation_index=None,
        advisor_note="Aucune donnée satellitaire disponible",
        image_url=None,
    )