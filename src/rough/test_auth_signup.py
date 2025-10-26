import pytest
import json
import requests
from loguru import logger





@pytest.mark.order(1)
def test_01_auth_signup(new_user, base_url, CaptureUserdetails):
    r = requests.post(base_url+"/auth/signup", json=new_user)
    assert r.status_code == 201
    assert r.json()["message"] == "User registered successfully"
    assert r.json()["name"] == new_user["name"]
    assert r.json()["email"] == new_user["email"]
    print(r.json()['role']) == "CONSUMER"
    data = r.json()
    

    user_record = {
                "id": data["id"],
                "name": data["name"],
                "email": data["email"],
                "role": data["role"],
                "api_key": data["api_key"],
                "message": data["message"]}

    logger.info(f"user record, {user_record}")
    CaptureUserdetails(user_record)


    
    
