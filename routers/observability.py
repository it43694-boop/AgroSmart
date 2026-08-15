import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session

import auth
import monitoring
from core.request_context import get_request_id
from database import get_db
from services.health_service import HealthService

router = APIRouter()


@router.get("/api/health/", tags=["system"], operation_id="api_health_check")
def api_health_check(db: Session = Depends(get_db)):
    return HealthService.get_status(db)


@router.get("/api/observability/health", tags=["system"], operation_id="observability_service_health")
def observability_health(request: Request):
    request_id = get_request_id() or request.headers.get("X-Request-ID") or "unknown"
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            scheme, token = auth_header.split(maxsplit=1)
            if scheme.lower() == "bearer":
                payload = auth.jwt.decode(
                    token,
                    auth._get_signing_key(),
                    algorithms=[auth.ALGORITHM],
                    issuer="agrosmart",
                )
                user_id = payload.get("sub")
        except Exception:
            user_id = None
    return {
        "status": "ok",
        "service": "agrosmart",
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.get("/metrics", tags=["system"], operation_id="metrics_export")
def metrics(request: Request):
    environment = getattr(request.app.state, "environment", "development")
    metrics_enabled = getattr(request.app.state, "metrics_enabled", False)
    metrics_access_token = getattr(request.app.state, "metrics_access_token", "")

    if environment == "production":
        if not metrics_enabled:
            raise HTTPException(status_code=404, detail="Not found")

        auth_header = request.headers.get("Authorization", "")
        if metrics_access_token:
            expected = f"Bearer {metrics_access_token}"
            if auth_header != expected:
                raise HTTPException(status_code=403, detail="Forbidden")
        elif auth_header:
            raise HTTPException(status_code=403, detail="Forbidden")

    return Response(
        generate_latest(monitoring.registry),
        media_type=CONTENT_TYPE_LATEST,
    )
