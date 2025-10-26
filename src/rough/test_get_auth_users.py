from math import log
import pytest
import requests
import json
from loguru import logger



@pytest.mark.order(4)
def test_get_auth_users(base_url, last_user, last_user_apikey):
    email = last_user["email"]
    api_key = last_user_apikey["api_key"]
    token = last_user["token"]
    name = last_user_apikey["name"]
    role = last_user_apikey["role"]

    params = {
    "email": email 
            }


    # headers =  headers = {
    #     "x-auth-source": "AUTH_TOKEN",
    #     "Authorization": f"Bearer {token}"
    # }

    headers = {
        "accept": "application/json",
        "x-auth-source": "API_KEY",
        "Authorization": f"apiKey {api_key}"
    }
    

    r = requests.get(base_url+"/auth/user", params=params,  headers=headers )

    data = r.json()

    if r.status_code == 401:
        pytest.fail(f"❌ Unauthorized: Invalid or expired credentials → {r.text}")

    assert r.status_code == 200, f"❌ Expected 200 OK but got {r.status_code}: {r.text}"
    assert email == data["email"]
    assert data["role"] == "CONSUMER"
    assert data["name"] == name


    