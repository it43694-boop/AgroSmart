from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI


def register_app_routers(
    app: FastAPI,
    logger: Any,
    *,
    marketplace_router: Any,
    marketplace_endpoints_router: Optional[Any] = None,
    users_router: Optional[Any] = None,
    frontend_router: Optional[Any] = None,
    finance_router: Optional[Any] = None,
    dashboard_router: Optional[Any] = None,
    blockchain_router: Optional[Any] = None,
    community_router: Optional[Any] = None,
    learning_router: Optional[Any] = None,
    cooperatives_router: Optional[Any] = None,
    security_router: Optional[Any] = None,
    client_router: Optional[Any] = None,
    bank_router: Optional[Any] = None,
    insurance_api_router: Optional[Any] = None,
    admin_users_router: Optional[Any] = None,
    iot_router: Optional[Any] = None,
    voice_router: Optional[Any] = None,
    agro_brain_router: Optional[Any] = None,
    payments_router: Optional[Any] = None,
    logistics_router: Optional[Any] = None,
    gamification_router: Optional[Any] = None,
    recommendations_router: Optional[Any] = None,
    notifications_router: Optional[Any] = None,
    sms_ussd_router: Optional[Any] = None,
    mobile_money_router: Optional[Any] = None,
    payment_release_router: Optional[Any] = None,
    ai_router: Optional[Any] = None,
    insurance_router: Optional[Any] = None,
    integration_router: Optional[Any] = None,
    impact_router: Optional[Any] = None,
    compliance_router: Optional[Any] = None,
    dao_router: Optional[Any] = None,
    ml_router: Optional[Any] = None,
    real_marketplace_router: Optional[Any] = None,
    chat_router: Optional[Any] = None,
    vision_router: Optional[Any] = None,
    reports_router: Optional[Any] = None,
    admin_retrain_router: Optional[Any] = None,
    observability_router: Optional[Any] = None,
    modules_available: bool = False,
    marketplace_endpoints_available: bool = False,
) -> None:
    """Register the application routers in a single, isolated bootstrap helper."""

    app.include_router(marketplace_router)

    if marketplace_endpoints_available and marketplace_endpoints_router is not None:
        app.include_router(marketplace_endpoints_router)

    if users_router is not None:
        app.include_router(users_router)
    if frontend_router is not None:
        app.include_router(frontend_router)

    if finance_router is not None:
        app.include_router(finance_router)
    if dashboard_router is not None:
        app.include_router(dashboard_router)
    if blockchain_router is not None:
        app.include_router(blockchain_router)
    if community_router is not None:
        app.include_router(community_router)
    if learning_router is not None:
        app.include_router(learning_router)
    if cooperatives_router is not None:
        app.include_router(cooperatives_router)
    if security_router is not None:
        app.include_router(security_router)
    if client_router is not None:
        app.include_router(client_router)
    if bank_router is not None:
        app.include_router(bank_router)
    if insurance_api_router is not None:
        app.include_router(insurance_api_router)
    if admin_users_router is not None:
        app.include_router(admin_users_router)
    if iot_router is not None:
        app.include_router(iot_router)
    if voice_router is not None:
        app.include_router(voice_router)
    if agro_brain_router is not None:
        app.include_router(agro_brain_router)
    if payments_router is not None:
        app.include_router(payments_router)
    if logistics_router is not None:
        app.include_router(logistics_router)
    if gamification_router is not None:
        app.include_router(gamification_router)
    if recommendations_router is not None:
        app.include_router(recommendations_router)
    if notifications_router is not None:
        app.include_router(notifications_router)
    if sms_ussd_router is not None:
        app.include_router(sms_ussd_router)
    if mobile_money_router is not None:
        app.include_router(mobile_money_router)
    if payment_release_router is not None:
        app.include_router(payment_release_router)

    if modules_available:
        if ai_router is not None:
            app.include_router(ai_router)
        if insurance_router is not None:
            app.include_router(insurance_router)
        if integration_router is not None:
            app.include_router(integration_router)
        if impact_router is not None:
            app.include_router(impact_router)
        if compliance_router is not None:
            app.include_router(compliance_router)
        if dao_router is not None:
            app.include_router(dao_router)
        logger.info("[OK] All 7 module routers registered")
    else:
        logger.warning("[WARNING] Module routers not available")

    if ml_router is not None:
        app.include_router(ml_router)
        logger.info("[OK] ML router registered")

    if observability_router is not None:
        app.include_router(observability_router)
        logger.info("[OK] Observability router registered")

    if chat_router is not None:
        app.include_router(chat_router)
        logger.info("[OK] Chat router registered")

    if vision_router is not None:
        app.include_router(vision_router)
        logger.info("[OK] Vision router registered")

    if reports_router is not None:
        app.include_router(reports_router)
        logger.info("[OK] Reports router registered")

    if admin_retrain_router is not None:
        app.include_router(admin_retrain_router)
        logger.info("[OK] Admin retrain router registered")

    if real_marketplace_router is not None:
        app.include_router(real_marketplace_router)
        logger.info("[OK] Real marketplace router registered (SAGA + Real Payments + Real Data)")
