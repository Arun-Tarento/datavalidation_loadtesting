import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: ENV=sandbox python testing/AI4I/Errors/nmt_errors.py
load_dotenv("testing/.env")
env = os.getenv("ENVIRONMENT", "staging")

from faker import Faker
import requests
import random
from loguru import logger
import time
import json

fake = Faker()
base_url = os.getenv("BASE_URL")
token_expiry_time = int(os.getenv("TOKEN_LIFETIME", 840))
time_now = time.time()


class NmtUser():
    api_key = os.getenv("API_KEY")

    def __init__(self):
        self.access_token = ""
        self.refresh_token = ""
        self.token_expiry_time = time_now

    def login(self):
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json={
                "email": os.getenv("EMAIL"),
                "password": os.getenv("PASSWORD"),
                "remember_me": False
            }
        )
        self.access_token = response.json()["access_token"]
        self.refresh_token = response.json()["refresh_token"]
        self.token_expiry_time = time.time() + token_expiry_time

    def token_refresh(self):
        if time.time() > self.token_expiry_time:
            response = requests.post(
                f"{base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            if response.status_code == 200:
                logger.info(f"Token refresh successful ({response.status_code})")
            else:
                logger.error(f"Token refresh failed ({response.status_code})")
            self.access_token = response.json().get("access_token")
            self.token_expiry_time = time.time() + token_expiry_time

    def fetch_samples(self):
        samples_file = os.getenv("NMT_SAMPLES_FILE", "samples/NMT/nmt_100_samples.json")
        with open(samples_file, "r") as f:
            data = json.load(f)
        return random.choice(data["nmt_samples"])

    def send_nmt_request(self, force_error=None):
        self.token_refresh()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key": NmtUser.api_key,
            "x-auth-source": "BOTH"
        }
        endpoint = f"{base_url}/api/v1/nmt/inference"
        sample = self.fetch_samples()
        source_text = sample["source"]

        service_id = os.getenv("NMT_SERVICE_ID")
        source_lang = os.getenv("NMT_SOURCE_LANGUAGE", "hi")
        target_lang = os.getenv("NMT_TARGET_LANGUAGE", "en")

        payload = {
            "input": [{"source": source_text}],
            "config": {
                "serviceId": service_id,
                "language": {"sourceLanguage": source_lang, "targetLanguage": target_lang}
            },
            "controlConfig": {"additionalProp1": {"dataTracking": False}}
        }

        if force_error is None:
            error_type = None
        else:
            error_type = force_error

        if error_type:
            logger.info(f"Triggering error: {error_type}")

            if error_type == "400":
                payload["input"] = [{"source": ""}]

            elif error_type == "401":
                headers["Authorization"] = "Bearer invalid_token_xyz123"

            elif error_type == "403":
                headers["x-api-key"] = "invalid_api_key_12345"

            elif error_type == "404":
                endpoint = f"{base_url}/api/v1/nmt/nonexistent_endpoint"

            elif error_type == "500":
                payload["input"] = [{"source": None}]
                payload["config"]["serviceId"] = None

            elif error_type == "502":
                payload["input"] = [{"source": source_text * 100000}]
        else:
            logger.info("Sending valid request")

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {response.json()}")
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
        except Exception as e:
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    user = NmtUser()
    logger.info(f"Logging in [{env} environment]...")
    user.login()
    logger.info(f"Login successful - Token: {user.access_token[:20]}...")

    error_code = input("Enter error code (400/401/403/404/500/502/valid): ").strip()
    num_requests = int(input("Enter number of requests: ").strip())

    for i in range(num_requests):
        logger.info(f"--- Request {i+1}/{num_requests} ---")
        if error_code == "valid":
            user.send_nmt_request(force_error=None)
        else:
            user.send_nmt_request(force_error=error_code)
        time.sleep(1)

    logger.info("Done.")
