import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth import serialize_user_for_response


def test_serialize_user_for_response_normalizes_role_and_account_type():
    user = SimpleNamespace(
        id=1,
        full_name="Test User",
        email="farmer@example.com",
        username="farmer",
        phone="+22300000000",
        village="Bamako",
        region="Bamako",
        total_surface=5.5,
        is_admin=False,
        is_validated=True,
        account_type="Farmer",
        role="Farmer",
        is_active=True,
        mfa_enabled=False,
    )

    payload = serialize_user_for_response(user)

    assert payload["role"] == "farmer"
    assert payload["account_type"] == "farmer"
