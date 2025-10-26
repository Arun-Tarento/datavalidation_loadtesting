import re
import pytest
import json
import requests
from loguru import logger





@pytest.mark.order(6)
def test_06_auth_user_list(base_url, last_user):
    

    token = last_user["token"]    
    headers = {
        "x-auth-source": "AUTH_TOKEN",
         "Authorization": f"Bearer {token}"
     }

    r = requests.get(base_url+"/auth/user/list", headers=headers)

    data = r.json()
    
    logger.info(f"printing auth user list : {data}")

    