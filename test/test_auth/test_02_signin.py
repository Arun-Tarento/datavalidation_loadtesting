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
     
def test_02_signin(api_request_context, base_url):
    user_state=load_state()
    if not user_state:
        pytest.skip("Signup state not found — run signup first (test_01_signup).")
    

