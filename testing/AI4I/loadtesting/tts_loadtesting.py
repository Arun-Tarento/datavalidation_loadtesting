import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: ENV=sandbox locust -f testing/AI4I/loadtesting/tts_loadtesting.py ...
load_dotenv("testing/.env")
env = os.getenv("ENVIRONMENT", "staging")

from locust import HttpUser, task, between
from loguru import logger
import itertools
import time
import json

base_url = os.getenv("BASE_URL")


class TTSUser(HttpUser):
    source_cache = None
    source_iterator = None
    wait_time = between(1, 5)
    api_key = os.getenv("API_KEY")
    TOKEN_LIFETIME = int(os.getenv("TOKEN_LIFETIME", 840))
    connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", 120))

    def on_start(self):
        self.start_time = time.time()
        self.login()

        if TTSUser.source_cache is None:
            samples_file = os.getenv("TTS_SAMPLES_FILE")
            with open(samples_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                TTSUser.source_cache = data["tts_samples"]
                TTSUser.source_iterator = itertools.cycle(TTSUser.source_cache)
                logger.info(f"Loaded {len(TTSUser.source_cache)} TTS samples from {samples_file}")

    def on_stop(self):
        total_time = time.time() - self.start_time
        logger.info(f"Total time: {total_time:.2f}s")

    def login(self):
        try:
            response = self.client.post(
                f"{base_url}/api/v1/auth/login",
                json={
                    "email": os.getenv("EMAIL"),
                    "password": os.getenv("PASSWORD"),
                    "remember_me": False
                }
            )
            if response.status_code == 200:
                logger.info(f"Login successful ({response.status_code})")
            else:
                logger.error(f"Login failed ({response.status_code})")
            self.access_token = response.json().get("access_token")
            self.refresh_token = response.json().get("refresh_token")
            self.token_expiry_time = time.time() + TTSUser.TOKEN_LIFETIME
        except Exception as e:
            logger.error(f"Login exception: {e}")
            self.access_token = None
            self.refresh_token = None
            self.token_expiry_time = time.time() + TTSUser.TOKEN_LIFETIME

    def token_refresh(self):
        if time.time() > self.token_expiry_time:
            try:
                response = self.client.post(
                    f"{base_url}/api/v1/auth/refresh",
                    json={"refresh_token": self.refresh_token}
                )
                if response.status_code == 200:
                    logger.info("Token refresh successful")
                    self.access_token = response.json().get("access_token")
                    self.token_expiry_time = time.time() + TTSUser.TOKEN_LIFETIME
                else:
                    logger.error(f"Token refresh failed ({response.status_code}), re-logging in")
                    self.login()
            except Exception as e:
                logger.error(f"Token refresh exception: {e}, re-logging in")
                self.login()

    @task
    def tts_task(self):
        if not self.access_token:
            logger.warning("No access token, attempting login...")
            self.login()

        self.token_refresh()

        sample = next(TTSUser.source_iterator)
        source_text = sample["source"]
        logger.info(f"Sample {sample['source_id']}: {source_text[:80]}")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key": TTSUser.api_key,
            "x-auth-source": "BOTH",
            "Connection": "keep-alive"
        }

        payload = {
            "input": [{"source": source_text}],
            "config": {
                "language": {"sourceLanguage": os.getenv("TTS_SOURCE_LANGUAGE", "hi")},
                "serviceId": os.getenv("TTS_SERVICE_ID"),
                "gender": os.getenv("TTS_GENDER", "female"),
                "samplingRate": int(os.getenv("TTS_SAMPLING_RATE", 22050)),
                "audioFormat": os.getenv("TTS_AUDIO_FORMAT", "wav")
            },
            "controlConfig": {"dataTracking": False}
        }

        try:
            start_time = time.time()
            response = self.client.post(
                url=f"{base_url}/api/v1/tts/inference",
                headers=headers,
                json=payload,
                timeout=TTSUser.connection_timeout
            )
            elapsed = time.time() - start_time
            logger.info(f"TTS response: {response.status_code} ({elapsed:.2f}s)")
        except Exception as e:
            logger.error(f"TTS request failed: {e}")
