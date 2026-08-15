import os
from typing import List


def validate_runtime_config() -> List[str]:
    """Valide les variables critiques pour un déploiement sécurisé."""
    issues: List[str] = []

    environment = (os.getenv("ENVIRONMENT") or "development").lower()

    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    if environment == "production" and not secret_key:
        issues.append("SECRET_KEY is required in production")
    elif environment == "production" and secret_key in {"changeme", "CHANGE_ME"}:
        issues.append("SECRET_KEY uses an insecure default value")

    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if environment == "production" and not database_url:
        issues.append("DATABASE_URL is required in production")
    elif environment == "production" and database_url.startswith("sqlite"):
        issues.append("DATABASE_URL must point to a production database (not SQLite) in production")

    metrics_enabled = os.getenv("ENABLE_PROMETHEUS_METRICS", "false").lower() in ("1", "true", "yes")
    metrics_access_token = (os.getenv("METRICS_ACCESS_TOKEN") or "").strip()
    if environment == "production" and metrics_enabled and not metrics_access_token:
        issues.append("METRICS_ACCESS_TOKEN is required when metrics are enabled in production")

    return issues
