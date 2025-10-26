import email
import pytest
import requests
from loguru import logger
import time

@pytest.mark.order(2)
def test_02_auth_sign_in(base_url, last_user, CaptureUserdetails, LastUserCsv):
    body = {
            "email": last_user["email"],
            "password": LastUserCsv["password"]
            }
    r = requests.post(base_url+"/auth/signin", json=body)
    data = r.json()
    assert isinstance(data["id"], str)
    assert isinstance(data["email"], str)
    assert isinstance(data["token"], str)
    assert isinstance(data["role"], str)
    assert data["role"] == "CONSUMER"

    user_record = {"id" : data["id"],
                    "email" : data["email"],
                    "token" : data["token"],
                    "role" : data["role"]
                    }
    logger.info(f"user record, {user_record}")

    CaptureUserdetails(user_record)
    time.sleep(5)

