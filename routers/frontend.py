from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

router = APIRouter(tags=["frontend"])


@router.get("/")
def serve_root():
    return RedirectResponse(url="/frontend/index.html")


@router.get("/login")
def serve_login():
    return RedirectResponse(url="/frontend/login.html")


@router.get("/signup")
def serve_signup():
    return RedirectResponse(url="/frontend/signup.html")


@router.get("/nexus")
def serve_nexus():
    return RedirectResponse(url="/frontend/nexus.html")


@router.get("/client-dashboard")
def serve_client_dashboard():
    return RedirectResponse(url="/frontend/client-dashboard.html")


@router.get("/farmer-dashboard")
def serve_farmer_dashboard():
    return RedirectResponse(url="/frontend/farmer-dashboard.html")


@router.get("/iot-dashboard")
def serve_iot_dashboard():
    return RedirectResponse(url="/frontend/iot-dashboard.html")


@router.get("/bank-dashboard")
def serve_bank_dashboard():
    return RedirectResponse(url="/frontend/bank-dashboard.html")


@router.get("/insurance-dashboard")
def serve_insurance_dashboard():
    return RedirectResponse(url="/frontend/insurance-dashboard.html")


@router.get("/admin")
def serve_admin():
    return RedirectResponse(url="/frontend/admin.html")


@router.get("/mfa-setup")
def serve_mfa_setup():
    return RedirectResponse(url="/frontend/mfa-setup.html")


@router.get("/community")
@router.get("/community-services")
def serve_community_services():
    return RedirectResponse(url="/frontend/community-services.html")


@router.get("/frontend/community.html")
def serve_frontend_community():
    return RedirectResponse(url="/frontend/community-services.html")


@router.get("/frontend/farmer-dashboard.html")
def serve_frontend_farmer_dashboard():
    return FileResponse(FRONTEND_DIR / "farmer-dashboard.html")


@router.get("/frontend/client-dashboard.html")
def serve_frontend_client_dashboard():
    return FileResponse(FRONTEND_DIR / "client-dashboard.html")


@router.get("/frontend/admin.html")
def serve_frontend_admin_dashboard():
    return FileResponse(FRONTEND_DIR / "admin.html")


@router.get("/frontend/iot-dashboard.html")
def serve_frontend_iot_dashboard():
    return FileResponse(FRONTEND_DIR / "iot-dashboard.html")


@router.get("/frontend/bank-dashboard.html")
def serve_frontend_bank_dashboard():
    return FileResponse(FRONTEND_DIR / "bank-dashboard.html")


@router.get("/frontend/insurance-dashboard.html")
def serve_frontend_insurance_dashboard():
    return FileResponse(FRONTEND_DIR / "insurance-dashboard.html")


@router.get("/frontend/community-services.html")
def serve_frontend_community_services():
    return FileResponse(FRONTEND_DIR / "community-services.html")


@router.get("/frontend/mfa-setup.html")
def serve_frontend_mfa_setup():
    return FileResponse(FRONTEND_DIR / "mfa-setup.html")
