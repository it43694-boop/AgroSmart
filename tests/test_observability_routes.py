from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main


def test_health_route_is_unique_and_metrics_route_exists():
    health_routes = [route for route in main.app.routes if getattr(route, "path", None) == "/health"]
    assert len(health_routes) == 1
    assert any(getattr(route, "path", None) == "/metrics" for route in main.app.routes)
