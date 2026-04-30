import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: ENV=sandbox python testing/AI4I/Errors/asr_errors.py
load_dotenv("testing/.env")
env = os.getenv("ENVIRONMENT", "staging")

from faker import Faker
import requests
import random
from loguru import logger
import time
import base64

fake = Faker()
base_url = os.getenv("BASE_URL")
token_expiry_time = int(os.getenv("TOKEN_LIFETIME", 840))
time_now = time.time()


class AsrUser():
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
        if response.status_code != 200:
            logger.error(f"Login failed ({response.status_code}): {response.text!r}")
            raise RuntimeError(f"Login failed with status {response.status_code}")
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
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

    def get_audio_sample(self):
        samples_dir = os.getenv("ASR_SAMPLES_DIR", "samples/ASR")
        sample_path = os.path.join(samples_dir, "hindi_4s.wav")
        with open(sample_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def send_request(self, force_error=None):
        self.token_refresh()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "x-auth-source": "BOTH"
        }
        endpoint = f"{base_url}/api/v1/asr/inference"
        audio_content = self.get_audio_sample()

        service_id = os.getenv("ASR_SERVICE_ID", "asr_am_ensemble")
        source_lang = os.getenv("ASR_SOURCE_LANGUAGE", "hi")
        audio_format = os.getenv("ASR_AUDIO_FORMAT", "wav")
        sampling_rate = int(os.getenv("ASR_SAMPLING_RATE", 16000))

        valid_payload = {
            "audio": [{"audioContent": audio_content}],
            "config": {
                "serviceId": service_id,
                "language": {"sourceLanguage": source_lang},
                "audioFormat": audio_format,
                "samplingRate": sampling_rate,
                "transcriptionFormat": "transcript",
                "bestTokenCount": 0
            },
            "controlConfig": {"dataTracking": False}
        }
        payload = valid_payload

        if force_error:
            logger.info(f"Triggering error: {force_error}")

            if force_error == "400":
                payload = {**valid_payload, "audio": [{"audioContent": fake.text(max_nb_chars=50)}]}

            elif force_error == "401":
                headers["Authorization"] = "Bearer invalid_token_xyz123"

            elif force_error == "403":
                headers["x-api-key"] = "invalid_api_key_12345"

            elif force_error == "404":
                endpoint = f"{base_url}/api/v1/asr/nonexistent_endpoint"

            elif force_error == "500":
                payload = {
                    "audio": [{"audioContent": None}],
                    "config": {
                        "serviceId": "None",
                        "language": None,
                        "audioFormat": audio_format,
                        "samplingRate": sampling_rate,
                        "transcriptionFormat": "transcript",
                        "bestTokenCount": 0
                    },
                    "controlConfig": {"dataTracking": False}
                }

            elif force_error == "502":
                payload = {**valid_payload, "audio": [{"audioContent": audio_content * 200000}]}
        else:
            logger.info("Sending valid request")

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            logger.info(f"Status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Exception: {e}")
            return None


if __name__ == "__main__":
    user = AsrUser()
    logger.info(f"Logging in [{env} environment]...")
    user.login()
    logger.info(f"Login successful - Token: {user.access_token[:20]}...")

    error_code = input("Enter error code (400/401/403/404/500/502/valid): ").strip()
    num_requests = int(input("Enter number of requests: ").strip())

    for i in range(num_requests):
        logger.info(f"--- Request {i+1}/{num_requests} ---")
        if error_code == "valid":
            user.send_request(force_error=None)
        else:
            user.send_request(force_error=error_code)
        time.sleep(1)

    logger.info("Done.")
