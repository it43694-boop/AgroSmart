from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class HealthService:
    """Service de santé centralisé pour les vérifications production."""

    @staticmethod
    def get_status(db: Session) -> Dict[str, Any]:
        try:
            db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as exc:  # pragma: no cover - defensive path
            db_status = f"unavailable: {exc}"

        return {
            "status": "ok" if db_status == "connected" else "degraded",
            "database": db_status,
            "service": "agrosmart",
        }
