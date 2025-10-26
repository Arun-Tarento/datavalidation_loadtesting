from utils.test_base_class import test_class
import pytest
import time
from pathlib import Path
import json
from playwright.sync_api import APIRequestContext

STATE_FILE = Path(".test_state.json")
def save_state(data: dict):
     STATE_FILE.write_text(json.dumps(data, indent=2))

def load_state() -> dict | None:
     if not STATE_FILE.exists():
        return None
     try:
        return json.loads(STATE_FILE.read_text())
     except json.JSONDecodeError:
        return None
     


def test_signup(base_url, new_user):
     url = f"{base_url}/auth/signup"
     include_fields = {"name", "email", "password"}
     user = test_class(**new_user)
     response = user.post_request(url, include_fields)
     assert response.status_code in [200, 201], (
        f"Unexpected status: {response.status_code}, Body: {response.text}"
    )
     data = response.json()
     test_class.id = data.get("id")
     test_class.email = data.get("email")
     test_class.token = data.get("token")
     test_class.role = data.get("role")
     test_class.password = user.password
     test_class.api_key = data.get("api_key")
     user_state = {
        "id": data.get("id"),
        "email": data.get("email"),
        "token": data.get("token"),
        "role": data.get("role"),
        "password": user.password,
        "api_key": data.get("api_key"),
    }
     save_state(user_state) 

def test_signin(base_url):
     url = f"{base_url}/auth/signin"
     include_fields = {"email", "password"}
     user_state = load_state()
     user = test_class(
        email=user_state["email"],
        password=user_state["password"]
    )
     response = user.post_request(url, include_fields)
     assert response.status_code in [200, 201], (
        f"Unexpected status: {response.status_code}, Body: {response.text}"
    )
     data = response.json()
     time.sleep(5)
     test_class.token = data.get("token")
     user_state["token"] = data.get("token")
     save_state(user_state) 


def test_refresh(base_url):
     url = f"{base_url}/auth/refresh"
     include_fields = {"token"}
     user_state = load_state()
     user = test_class(token = user_state["token"])
     response = user.post_request(url, include_fields)
     time.sleep(5)
     assert response.status_code in [200, 201], (
        f"Unexpected status: {response.status_code}, Body: {response.text}"
    )
     data = response.json()
     test_class.token = data.get("token")
     user_state["token"] = data.get("token")
     save_state(user_state)


def test_get_api_key_list(base_url):
     url = f"{base_url}/auth/api-key/list"
     user_state = load_state()
     assert user_state and user_state.get("id") and user_state.get("token"), (
        "Missing user state — run signup first."
    )
     user = test_class(token=user_state["token"], id=user_state["id"])

     params = {
        "target_user_id": user.id,
        "target_service_id": None
    }
     
     params = {k: v for k, v in params.items() if v is not None}

     user.headers = {
         
        "x-auth-source": "AUTH_TOKEN",
        "Authorization": f"Bearer {user.token}"
    }
     response = user.request_get(url, headers=user.headers, params=params)
     assert response.status_code == 200, f"Failed: {response.status_code} {response.text}"
     data = response.json()
     print("API key list:", data)


def test_get_api_key_list(base_url):
     url = f"{base_url}/auth/api-key/list"
     user_state = load_state()
     assert user_state and user_state.get("id") and user_state.get("token"), (
        "Missing user state — run signup first."
    )
     user = test_class(token=user_state["token"], id=user_state["id"])

     params = {
        "target_user_id": user.id,
        "target_service_id": None
    }
     
     params = {k: v for k, v in params.items() if v is not None}

     user.headers = {
         
        "x-auth-source": "AUTH_TOKEN",
        "Authorization": f"Bearer {user.token}"
    }
     response = user.request_get(url, headers=user.headers, params=params)
     assert response.status_code == 200, f"Failed: {response.status_code} {response.text}"
     data = response.json()
     print("API key list:", data)








     

