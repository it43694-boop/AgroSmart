import os
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

import auth
import monitoring
from core.observability import logger
from core.production_hardening import validate_runtime_config
from core.request_context import get_request_id, set_request_id
from database import init_db
from utils import create_default_admin_if_missing


def _get_env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def _get_env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _make_lifespan() -> Callable:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        auth.validate_security_configuration()

        issues = validate_runtime_config()
        if issues:
            logger.error("Production configuration issues: %s", issues)
            raise RuntimeError("Invalid production configuration: " + "; ".join(issues))

        env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
        strict_override = os.getenv("STRICT_SECRETS", "0") == "1"

        if strict_override or env == "production":
            missing = []
            if not os.getenv("STRIPE_SECRET_KEY"):
                missing.append("STRIPE_SECRET_KEY")
            if not os.getenv("BLOCKCHAIN_PRIVATE_KEY"):
                missing.append("BLOCKCHAIN_PRIVATE_KEY")

            if missing:
                logger.error(f"Missing required secrets on startup: {missing}")
                raise RuntimeError(f"Missing required secrets: {', '.join(missing)}")

        init_db()
        create_default_admin_if_missing()
        yield

    return lifespan


def create_app() -> FastAPI:
    env = os.getenv("ENVIRONMENT", "development").lower()
    csrf_enabled = _get_env_bool("ENABLE_CSRF_PROTECTION")

    default_origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://localhost",
        "https://localhost:3000",
        "https://localhost:5173",
        "https://127.0.0.1",
        "https://127.0.0.1:3000",
        "https://127.0.0.1:5173",
    ]
    configured_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
        if origin.strip()
    ]
    allowed_origins = configured_origins or default_origins
    allowed_origins = list(dict.fromkeys(allowed_origins))

    app = FastAPI(
        title="Agro Smart API",
        description="API pour la gestion agricole intelligente - Marketplace, IoT, IA, Finance",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "Support AgroSmart",
            "email": "support@agro-smart.com",
        },
        license_info={
            "name": "MIT License",
        },
        lifespan=_make_lifespan(),
    )

    app.state.environment = env
    app.state.csrf_protection_enabled = csrf_enabled
    app.state.allowed_origins = allowed_origins
    app.state.metrics_enabled = _get_env_bool("ENABLE_PROMETHEUS_METRICS")
    app.state.metrics_access_token = _get_env_str("METRICS_ACCESS_TOKEN")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-CSRF-Token",
            "X-Requested-With",
        ],
        expose_headers=["WWW-Authenticate", "X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def https_enforcement_middleware(request: Request, call_next):
        if env == "production":
            scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
            if scheme.lower() != "https":
                secure_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(secure_url), status_code=307)
        return await call_next(request)

    @app.middleware("http")
    async def csrf_protection_middleware(request: Request, call_next):
        if csrf_enabled and request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if "authorization" not in request.headers and request.cookies:
                csrf_header = request.headers.get("X-CSRF-Token")
                csrf_cookie = request.cookies.get("csrftoken")
                if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token manquant ou invalide."},
                    )
        return await call_next(request)

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https:; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:;"
        )
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(self), camera=()");
        return response

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or _get_env_str("REQUEST_ID_PREFIX", "") + str(os.urandom(8).hex())
        set_request_id(request_id)
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            request_id=request_id,
        )
        return response

    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        endpoint = request.url.path
        if endpoint != "/metrics":
            monitoring.track_request(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            )
            monitoring.track_request_duration(
                method=request.method,
                endpoint=endpoint,
                duration=time.time() - start_time,
            )
        return response

    @app.get("/health", tags=["system"], summary="Health check", operation_id="system_health_check")
    async def health_check():
        return {
            "status": "ok",
            "environment": app.state.environment,
            "csrf_protection_enabled": app.state.csrf_protection_enabled,
            "metrics_enabled": app.state.metrics_enabled,
        }

    @app.get("/ready", tags=["system"], summary="Readiness check", operation_id="system_ready_check")
    async def ready_check():
        return {
            "status": "ready",
            "environment": app.state.environment,
            "checks": {
                "database_initialized": True,
                "security_configured": True,
                "metrics_enabled": app.state.metrics_enabled,
            },
        }

    return app
