from datetime import date
from shutil import register_unpack_format
from requests.utils import dotted_netmask
import pytest
import requests
import random
import string
import os
import uuid
import csv
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime
from loguru import logger
import sys
from playwright.sync_api import Playwright, APIRequestContext
from typing import Generator
from myproject.utils.env_utils import update_env_var
import httpx

_here = Path(__file__).resolve().parent
_env_candidates = [ _here / ".env",            
    _here.parent / ".env",     
    _here.parent.parent / ".env",  
    _here.parent.parent.parent / ".env"  ]

for p in _env_candidates:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break
base_url = os.getenv("BASE_URL")

user_store_file = Path(__file__).parent / "created_users.json"
USER_LOG_FILE = Path(__file__).parent/ "USER_LOG_FILE"

@pytest.fixture(scope="session")
def api_client_factory(base_url):
    def _make_client(headers: dict | None = None, timeout: float = 120.0):
        client = httpx.Client(
            base_url=base_url,
            headers=headers or {},
            timeout=timeout,
        )
        return client
    yield _make_client

@pytest.fixture(scope="function")
def api_client(api_client_factory):
    client = api_client_factory()
    yield client
    client.close()



@pytest.fixture(scope="session")
def api_factory(playwright: Playwright):
    def _make_api_context(base_url: str, headers: dict | None = None):
        ctx = playwright.request.new_context(
            base_url=base_url,
            extra_http_headers=headers or {},
            timeout=60000
        )
        return ctx
    yield _make_api_context

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        logger.debug("Response not JSON. content-type=%s body=%s", resp.headers.get("content-type"), resp.text[:2000])
        raise

@pytest.fixture(scope="function")
def auth_token_refreshed(base_url):
    # ----- Sign in -----
    logger.info("Attempting sign-in for user {}", os.getenv("CONSUMEREMAIL"))
    signin_resp = requests.post(
        f"{base_url}/auth/signin",
        json={
            "email": os.getenv("CONSUMEREMAIL"),
            "password": os.getenv("CONSUMERPASSWORD"),
        },
        timeout=20,  # give it a bit more time
    )
    logger.debug("Signin response status: {} ".format(signin_resp.status_code))
    logger.debug("Signin response headers: {}".format(signin_resp.headers))
    logger.debug("Signin response body: {}".format(signin_resp.text[:2000]))
    signin_resp.raise_for_status()
    signin_data = safe_json(signin_resp)
    token_after_signin = signin_data.get("token") or signin_data.get("access_token")
    logger.info("Token obtained from sign-in: {}", token_after_signin)
    # if not token_after_signin:
    #     raise RuntimeError(f"No token returned from signin: {signin_data}")

    # # ----- Refresh token: try header first, then JSON -----
    # refreshed_token = None
    # refresh_url = f"{base_url}/auth/refresh"
    # attempts = []

    # # # attempt A: Authorization header (most common)
    # # try:
    # #     logger.info("Trying refresh with Authorization header")
    # #     headers = {"Authorization": f"Bearer {token_after_signin}"}
    # #     refresh_resp = requests.post(refresh_url, headers=headers, timeout=15)
    # #     attempts.append(("header", refresh_resp))
    # #     logger.debug("Refresh(status={}) headers={}".format(refresh_resp.status_code, refresh_resp.headers))
    # #     logger.debug("Refresh body: {}".format(refresh_resp.text[:2000]))
    # #     if refresh_resp.ok:
    # #         refresh_data = safe_json(refresh_resp)
    # #         refreshed_token = refresh_data.get("token") or refresh_data.get("access_token")
    # #         if refreshed_token:
    # #             logger.success("Refreshed token (header): {}".format(refreshed_token))
    # # except Exception as e:
    # #     logger.exception("Refresh attempt with header raised an exception")

    # # attempt B: JSON payload with raw token (no Bearer)
    # # if not refreshed_token:
    # try:
    #     logger.info("Trying refresh with JSON body (raw token)")
    #     refresh_resp = requests.post(refresh_url, json={"token": str(token_after_signin)}, timeout=15)
    #     attempts.append(("json_raw", refresh_resp))
    #     logger.debug("Refresh(status={}) headers={}".format(refresh_resp.status_code, refresh_resp.headers))
    #     logger.debug("Refresh body: {}".format(refresh_resp.text[:2000]))
    #     if refresh_resp.ok:
    #         refresh_data = safe_json(refresh_resp)
    #         refreshed_token = refresh_data.get("token") or refresh_data.get("access_token")
    #         if refreshed_token:
    #             logger.success("Refreshed token (json raw): {}".format(refreshed_token))
    # except Exception:
    #     logger.exception("Refresh attempt with JSON raw token raised an exception")

    # # # attempt C: JSON payload with Bearer prefix (less common)
    # # if not refreshed_token:
    # #     try:
    # #         logger.info("Trying refresh with JSON body (Bearer prefix)")
    # #         refresh_resp = requests.post(refresh_url, json={"token": "Bearer " + str(token_after_signin)}, timeout=15)
    # #         attempts.append(("json_bearer", refresh_resp))
    # #         logger.debug("Refresh(status=%s) headers=%s", refresh_resp.status_code, refresh_resp.headers)
    # #         logger.debug("Refresh body: %s", refresh_resp.text[:2000])
    # #         if refresh_resp.ok:
    # #             refresh_data = safe_json(refresh_resp)
    # #             refreshed_token = refresh_data.get("token") or refresh_data.get("access_token")
    # #             if refreshed_token:
    # #                 logger.success("Refreshed token (json bearer): %s", refreshed_token)
    # #     except Exception:
    # #         logger.exception("Refresh attempt with JSON Bearer raised an exception")

    # # If still no token, raise an error with full attempt logs
    # if not refreshed_token:
    #     # Collect readable summaries
    #     attempt_summaries = []
    #     for kind, resp in attempts:
    #         status = None if resp is None else resp.status_code
    #         body = None if resp is None else (resp.text[:1000] + ("..." if len(resp.text) > 1000 else ""))
    #         attempt_summaries.append(f"{kind}: status={status} body={body}")
    #     logger.error("All refresh attempts failed. Attempts: %s", " | ".join(attempt_summaries))
    #     raise RuntimeError("Token refresh failed; see logs for response bodies")

    # # Step 3: Update .env or return the token
    # # NOTE: update_env_var should be defined by you; prefer returning token instead 
    # try:
    #     update_env_var("REFRESHED_AUTH_TOKEN", refreshed_token)
    # except Exception:
    #     logger.warning("update_env_var failed (not critical). Returning token instead.")

    return token_after_signin

    

''' common function to store user records when a user is created. '''
def saveRecords(user_record: dict):
    if user_store_file.exists():
        with open(user_store_file, "r+") as f:
            try:
                existing_users = json.load(f)
            except json.JSONDecodeError:
                existing_users = []
            existing_users.append(user_record)
            f.seek(0)
            json.dump(existing_users, f, indent=4)

    else:
        with open(user_store_file, "w") as f:
            json.dump([user_record], f, indent=2)    


''' logging '''
@pytest.fixture(scope="session", autouse=True)
def setup_logger():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # --- Create timestamped file name ---
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"test_session_{timestamp}.log"

    # --- Remove default sink (Loguru prints to stderr by default) ---
    logger.remove()

    # --- Add console sink (so logs appear in pytest output) ---
    logger.add(
        sys.stdout,
        level="DEBUG",
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # --- Add rotating file sink (persistent detailed logs) ---
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} | {file}:{line}",
        rotation="5 MB",
        retention="7 days",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # --- Log session start ---
    logger.info(f"🚀 Logging started: {log_file}")

    yield

    # --- Log session end ---
    logger.info("✅ Logging finished.")
    logger.remove()

''' base url '''
@pytest.fixture(scope="session")
def base_url():
    env = os.getenv("ENVIRONMENT", "dev").lower()
    base_url_map = {
        "test": os.getenv("BASE_URL_TEST"),
        "dev": os.getenv("BASE_URL_DEV"),
        "prod": os.getenv("BASE_URL_PROD")
    }

    base_url = base_url_map.get(env)
    assert base_url, f"BASE_URL not set for environment: {env}"
    return base_url

''' Creates a new user, everytime we start the test '''
@pytest.fixture(scope="function")
def new_user():
    suffix = uuid.uuid4().hex[:8]
    
    user = {
        "name": f"TestUser_{suffix}",
        "email": f"testuser_{suffix}@example.com",
        "password": f"TestUser_{suffix}"
    }
    with open(USER_LOG_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(user.values())
    return user

''' Store user details, usesthe save records funtion '''
@pytest.fixture(scope="function")
def CaptureUserdetails():
    def _store_user_details(record: dict):
        saveRecords(record)
    return _store_user_details



# @pytest.fixture(scope="function")
# def last_user():
#     with open(user_store_file, "r") as f:
#         users = json.load(f)
#         last_user = users[-1]
#     return last_user

# @pytest.fixture(scope="function")
# def last_user_apikey():
#     with open(user_store_file, "r") as f:
#         users = json.load(f)
#         _last_user_apikey = users[-2]
#     return _last_user_apikey


''' this is to retrive, the password of the last user crated in the system '''
@pytest.fixture(scope="function")
def LastUserCsv():
    if not USER_LOG_FILE.exists():
        pytest.skip("No CSV file found with created users")

    with open(USER_LOG_FILE, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        if not reader:
            pytest.skip("CSV file is empty")
        last_row = reader[-1]

    # Expect CSV structure: name,email,password
    return {
        "name": last_row[0],
        "email": last_row[1],
        "password": last_row[2]
    }


'''' This is only to update the token in the last dictionary of created_user.json file. '''
@pytest.fixture(scope="function")
def Updating_token_lastuser():
    def update_token(new_token: str):
        with open(user_store_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data or not isinstance(data, list):
            raise ValueError("user_store_file does not contain a list of users")
        data[-1]["token"] = new_token
        with open(user_store_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return update_token       






