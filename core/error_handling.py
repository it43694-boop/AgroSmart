from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class ServiceError(Exception):
    """Erreur métier standardisée pour les services."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def raise_http_error(exc: ServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, **exc.details})
