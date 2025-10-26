from myproject.utils.test_user import test_class
import pytest
import time
from pathlib import Path
import json
from playwright.sync_api import APIRequestContext

STATE_FILE = Path("test.test_state.json")
def save_state(data: dict):
     STATE_FILE.write_text(json.dumps(data, indent=2))

def load_state() -> dict | None:
     if not STATE_FILE.exists():
        return None
     try:
        return json.loads(STATE_FILE.read_text())
     except json.JSONDecodeError:
        return None
     

def test_01_signup(api_request_context, new_user, base_url):
    include_fields = {"name", "email", "password"}
    user = test_class(**new_user)
    resp = user.post_request(api_request_context, '/auth/signup', include_fields=include_fields)
    assert resp.status in (200, 201), f"Unexpected status: {resp.status}, Body: {resp.text()}"
    data = resp.json()
    user.id = data.get("id")
    user.email = data.get("email")
    user.token = data.get("token")
    user.role = data.get("role")
    user.password = user.password
    user.api_key = data.get("api_key")

    test_class.id = user.id
    test_class.email = user.email
    test_class.token = user.token
    test_class.role = user.role
    test_class.password = user.password
    test_class.api_key = user.api_key

    user_state = {
        "id": user.id,
        "email": user.email,
        "token": user.token,
        "role": user.role,
        "password": user.password,
        "api_key": user.api_key,
    }
    save_state(user_state)

