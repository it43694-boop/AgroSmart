import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()

from mali_apis import MaliRealAPIs, fetch_real_mali_data
from core.app_bootstrap import create_app
from core.app_modules import get_app_router_config, get_compatibility_router
from core.observability import logger
from core.router_registry import register_app_routers

BASE_DIR = Path(__file__).resolve().parent

app = create_app()
router_config = get_app_router_config()
register_app_routers(app, logger, **router_config)

app.include_router(get_compatibility_router())
app.mount("/frontend", StaticFiles(directory=BASE_DIR / "frontend"), name="frontend")

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    requested_port = int(os.getenv("PORT", "8001"))
    fallback_port = int(os.getenv("FALLBACK_PORT", "8002"))

    def _pick_available_port(host: str, preferred_port: int, fallback_port: int) -> int:
        for port in (preferred_port, fallback_port):
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                sock.close()
                return port
            except OSError:
                continue
        return preferred_port

    selected_port = _pick_available_port(host, requested_port, fallback_port)
    if selected_port != requested_port:
        logger.warning(f"Port {requested_port} occupied, starting on fallback port {selected_port}")

    import uvicorn

    uvicorn.run(app, host=host, port=selected_port, reload=False)
