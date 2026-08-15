"""
Service de cache pour optimiser les performances d'AgroSmart
Utilise Redis si disponible, sinon cache en mémoire
"""

import json
import time
from typing import Any, Optional
import os
import inspect
from functools import wraps

try:
    import redis
except ImportError:
    redis = None

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_cache_ttl = {}

        # Redis uniquement si REDIS_URL est explicitement defini
        if redis is None:
            self.redis_client = None
            return
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            self.redis_client = None
            return
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            print("Redis cache active")
        except Exception as e:
            print(f"Redis non disponible: {e}. Cache memoire.")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                return json.loads(data) if data else None
            except Exception:
                return None

        # Cache mémoire
        if key in self.memory_cache:
            if time.time() < self.memory_cache_ttl.get(key, 0):
                return self.memory_cache[key]
            else:
                # TTL expiré, supprimer
                del self.memory_cache[key]
                del self.memory_cache_ttl[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Stocke une valeur dans le cache avec TTL"""
        try:
            if self.redis_client:
                return self.redis_client.setex(key, ttl_seconds, json.dumps(value))
            else:
                # Cache mémoire
                self.memory_cache[key] = value
                self.memory_cache_ttl[key] = time.time() + ttl_seconds
                return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Supprime une clé du cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    del self.memory_cache_ttl[key]
                return True
        except Exception:
            return False

    def clear(self) -> bool:
        """Vide tout le cache"""
        try:
            if self.redis_client:
                return self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
                self.memory_cache_ttl.clear()
                return True
        except Exception:
            return False

# Instance globale du service de cache
cache_service = CacheService()

def cached(ttl_seconds: int = 300):
    """Décorateur pour mettre en cache le résultat d'une fonction"""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cached_result = cache_service.get(key)
                if cached_result is not None:
                    return cached_result

                result = await func(*args, **kwargs)
                cache_service.set(key, result, ttl_seconds)
                return result

            return wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cached_result = cache_service.get(key)
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            cache_service.set(key, result, ttl_seconds)
            return result

        return wrapper
    return decorator