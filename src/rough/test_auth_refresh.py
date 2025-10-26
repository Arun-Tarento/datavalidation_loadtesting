
from math import log
import pytest
import requests
import json
from loguru import logger


@pytest.mark.order(3)
def test_03_auth_refresh(base_url, last_user, Updating_token_lastuser):
    old_token = last_user["token"]
    body = {"token": old_token}

    logger.info(f"Old token: {old_token}")
    

    r = requests.post(base_url+"/auth/refresh", json=body)
    data = r.json()
    logger.info(f"data : {json.dumps(data, indent=2)}")
    new_token = data["token"]

    logger.info(f"New token after update: {new_token}")

    assert r.status_code == 200
    assert "token" in data, f"Missing 'token' key in response: {data}"
    assert isinstance(new_token, str), "Token must be a string"
    assert old_token != new_token

    logger.info(f"New token: {new_token}")
    logger.success(f"New token: {new_token}")

    '''' Same token to be used throughout the session, 
    so no need to update the token after every refresh '''
    Updating_token_lastuser(new_token)

    

