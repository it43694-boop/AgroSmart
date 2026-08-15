import os
from typing import Optional
from fastapi import HTTPException, Request


ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def validate_admin_secret(request: Request) -> bool:
    """Valide l'accès admin via header Bearer ou X-Admin-Token."""
    if not ADMIN_SECRET:
        return True

    auth_header = request.headers.get("Authorization") or request.headers.get("X-Admin-Token")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized admin token")

    parts = auth_header.split(None, 1)
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else auth_header

    if token != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized admin token")

    return True
