from typing import Any

from routers.real_marketplace_router import real_marketplace_router as marketplace_router

try:
    from marketplace_endpoints import router as marketplace_endpoints_router
    MARKETPLACE_ENDPOINTS_AVAILABLE = True
except Exception:
    marketplace_endpoints_router = None
    MARKETPLACE_ENDPOINTS_AVAILABLE = False

from routers.users import router as users_router
from routers.finance import router as finance_router
from routers.observability import router as observability_router
from routers.dashboard import router as dashboard_router
from routers.blockchain import router as blockchain_router
from routers.community import router as community_router
from routers.learning import router as learning_router
from routers.cooperatives import router as cooperatives_router
from routers.security import router as security_router
from routers.client import router as client_router
from routers.bank import router as bank_router
from routers.admin_users import router as admin_users_router
from routers.insurance import router as insurance_api_router
from routers.iot import router as iot_router
from routers.voice import router as voice_router
from routers.agro_brain import router as agro_brain_router
from routers.payments import router as payments_router
from routers.logistics import router as logistics_router
from routers.gamification import router as gamification_router
from routers.recommendations import router as recommendations_router
from routers.notifications import router as notifications_router
from routers.sms_ussd import router as sms_ussd_router
from routers.mobile_money import router as mobile_money_router
from routers.payment_release import router as payment_release_router
from routers.chat import router as chat_router
from routers.vision import router as vision_router
from routers.reports import router as reports_router
from routers.admin_retrain import router as admin_retrain_router
from routers.ml_router import router as ml_router
from routers.frontend import router as frontend_router
from routers.compatibility import router as compatibility_router

try:
    from routers.modules_router import (
        ai_router,
        insurance_router,
        integration_router,
        impact_router,
        compliance_router,
        dao_router,
    )
    MODULES_AVAILABLE = True
except Exception:
    ai_router = insurance_router = integration_router = impact_router = compliance_router = dao_router = None
    MODULES_AVAILABLE = False


def get_app_router_config() -> dict[str, Any]:
    return {
        "marketplace_router": marketplace_router,
        "marketplace_endpoints_router": marketplace_endpoints_router,
        "users_router": users_router,
        "frontend_router": frontend_router,
        "finance_router": finance_router,
        "dashboard_router": dashboard_router,
        "blockchain_router": blockchain_router,
        "community_router": community_router,
        "learning_router": learning_router,
        "cooperatives_router": cooperatives_router,
        "security_router": security_router,
        "client_router": client_router,
        "bank_router": bank_router,
        "insurance_api_router": insurance_api_router,
        "admin_users_router": admin_users_router,
        "iot_router": iot_router,
        "voice_router": voice_router,
        "agro_brain_router": agro_brain_router,
        "payments_router": payments_router,
        "logistics_router": logistics_router,
        "gamification_router": gamification_router,
        "recommendations_router": recommendations_router,
        "notifications_router": notifications_router,
        "sms_ussd_router": sms_ussd_router,
        "mobile_money_router": mobile_money_router,
        "payment_release_router": payment_release_router,
        "chat_router": chat_router,
        "vision_router": vision_router,
        "reports_router": reports_router,
        "admin_retrain_router": admin_retrain_router,
        "observability_router": observability_router,
        "ai_router": ai_router,
        "insurance_router": insurance_router,
        "integration_router": integration_router,
        "impact_router": impact_router,
        "compliance_router": compliance_router,
        "dao_router": dao_router,
        "ml_router": ml_router,
        "modules_available": MODULES_AVAILABLE,
        "marketplace_endpoints_available": MARKETPLACE_ENDPOINTS_AVAILABLE,
    }


def get_compatibility_router() -> Any:
    return compatibility_router
