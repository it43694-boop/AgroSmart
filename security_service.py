"""
Service de sécurité pour la gestion des rôles et des accès.
Valide les rôles, les permissions et les restrictions par dashboard.
"""

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, status

import auth
import models

logger = logging.getLogger("security")

# Définition des rôles et permissions
ROLES = ["admin", "farmer", "client", "bank", "insurance"]

# Mappage des endpoints protégés par rôle
ROLE_DASHBOARD_MAP = {
    "admin": "/admin",
    "farmer": "/farmer-dashboard",
    "client": "/client-dashboard",
    "bank": "/bank-dashboard",
    "insurance": "/insurance-dashboard",
}

# Permissions par rôle
ROLE_PERMISSIONS = {
    "admin": [
        "view_all_users",
        "manage_users",
        "view_analytics",
        "manage_system",
        "create_listings",
        "manage_orders",
        "view_payments",
        "manage_roles",
    ],
    "farmer": [
        "create_listings",
        "manage_own_listings",
        "view_orders",
        "manage_crops",
        "view_financial_records",
        "request_loans",
        "request_insurance",
    ],
    "client": [
        "browse_listings",
        "create_orders",
        "manage_own_orders",
        "write_reviews",
        "contact_sellers",
    ],
    "bank": [
        "view_loan_requests",
        "approve_loan_requests",
        "manage_bank_data",
        "view_farmers",
    ],
    "insurance": [
        "view_insurance_requests",
        "approve_insurance_requests",
        "manage_insurance_data",
        "view_farmers",
    ],
}


def validate_role(role: str) -> bool:
    """Valider qu'un rôle est reconnu"""
    return role in ROLES


def validate_user_role(user: models.User) -> str:
    """Extraire et valider le rôle d'un utilisateur"""
    role = user.effective_role
    if not validate_role(role):
        logger.warning(f"Rôle invalide pour l'utilisateur {user.id}: {role}")
        return "farmer"
    return role


def has_permission(user: models.User, permission: str) -> bool:
    """Vérifier qu'un utilisateur a une permission spécifique"""
    role = validate_user_role(user)
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


def require_permission(user: models.User, permission: str) -> None:
    """Lever une exception si l'utilisateur n'a pas la permission"""
    if not has_permission(user, permission):
        role = validate_user_role(user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission refusée. Le rôle '{role}' ne peut pas: {permission}",
        )


def get_allowed_dashboard(user: models.User) -> str:
    """Obtenir le dashboard autorisé pour un utilisateur"""
    role = validate_user_role(user)
    return ROLE_DASHBOARD_MAP.get(role, "/login")


def can_access_dashboard(user: models.User, dashboard: str) -> bool:
    """Vérifier qu'un utilisateur peut accéder à un dashboard"""
    role = validate_user_role(user)
    allowed = ROLE_DASHBOARD_MAP.get(role, "/login")
    return dashboard == allowed or role == "admin"


def require_dashboard_access(user: models.User, dashboard: str) -> None:
    """Lever une exception si l'utilisateur n'a pas accès au dashboard"""
    if not can_access_dashboard(user, dashboard):
        allowed = get_allowed_dashboard(user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Accès refusé. Redirection vers {allowed}",
        )


def require_dashboard_access_dependency(dashboard: str):
    """Retourne une dépendance FastAPI qui vérifie l'accès au dashboard"""
    def dependency(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
        require_dashboard_access(current_user, dashboard)
        return current_user
    return dependency


def can_view_user(current_user: models.User, target_user: models.User) -> bool:
    """Vérifier qu'un utilisateur peut voir un autre utilisateur"""
    role = validate_user_role(current_user)
    if role == "admin":
        return True
    if current_user.id == target_user.id:
        return True
    if current_user.effective_role in {"farmer", "client", "bank", "insurance"} and target_user is not None:
        return current_user.id == getattr(target_user, "id", None)
    return False


def require_user_view_access(current_user: models.User, target_user: models.User) -> None:
    """Lever une exception si l'utilisateur n'a pas accès à voir un autre utilisateur"""
    if not can_view_user(current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé à cet utilisateur",
        )


def can_manage_user(current_user: models.User, target_user: models.User) -> bool:
    """Vérifier qu'un utilisateur peut gérer un autre utilisateur"""
    role = validate_user_role(current_user)
    if role != "admin":
        return False
    if validate_user_role(target_user) == "admin" and current_user.id != target_user.id:
        return False
    return True


def require_user_management_access(current_user: models.User, target_user: models.User) -> None:
    """Lever une exception si l'utilisateur n'a pas accès pour gérer un autre utilisateur"""
    if not can_manage_user(current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé pour gérer cet utilisateur",
        )


def get_user_summary(user: models.User) -> dict:
    """Obtenir un résumé sûr des informations de l'utilisateur"""
    role = validate_user_role(user)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "village": user.village,
        "region": user.region,
        "total_surface": user.total_surface,
        "role": role,
        "account_type": role,
        "is_admin": role == "admin",
        "is_active": user.is_active,
        "is_validated": user.is_validated,
        "mfa_enabled": user.mfa_enabled,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "dashboard": get_allowed_dashboard(user),
        "permissions": ROLE_PERMISSIONS.get(role, []),
    }
