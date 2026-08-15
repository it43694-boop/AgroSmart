from typing import Any, Dict, Optional

import models
import schemas
from core.error_handling import ServiceError


class UserProfileService:
    """Service métier pour la consultation et la mise à jour du profil utilisateur."""

    @staticmethod
    def get_profile(user: models.User) -> Dict[str, Any]:
        if not user:
            raise ServiceError("Utilisateur introuvable", status_code=404)
        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "username": user.username,
            "role": getattr(user, "effective_role", None) or getattr(user, "role", None),
            "region": user.region,
            "village": user.village,
            "is_admin": bool(getattr(user, "is_admin", False)),
            "is_validated": bool(getattr(user, "is_validated", False)),
        }

    @staticmethod
    def update_profile(user: models.User, payload: Dict[str, Any]) -> Dict[str, Any]:
        allowed_fields = {"full_name", "region", "village", "phone", "total_surface"}
        for field in payload:
            if field not in allowed_fields:
                raise ServiceError(f"Champ non autorisé: {field}", status_code=400)

        for field, value in payload.items():
            setattr(user, field, value)

        return UserProfileService.get_profile(user)
