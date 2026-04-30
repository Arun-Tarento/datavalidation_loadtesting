import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: ENV=sandbox locust -f testing/AI4I/loadtesting/asr_loadtesting.py ...
load_dotenv("testing/.env")
env = os.getenv("ENVIRONMENT", "staging")

from locust import HttpUser, task, between
from loguru import logger
import base64
from pathlib import Path
import itertools
import time

base_url = os.getenv("BASE_URL")


class ASRUser(HttpUser):
    audio_cache = None
    audio_iterator = None
    wait_time = between(1, 5)
    api_key = os.getenv("API_KEY")
    TOKEN_LIFETIME = int(os.getenv("TOKEN_LIFETIME", 840))
    connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", 120))

    def on_start(self):
        self.login()

        if ASRUser.audio_cache is None:
            ASRUser.audio_cache = self._load_audio_samples()
            ASRUser.audio_iterator = itertools.cycle(ASRUser.audio_cache)
            logger.info(f"Loaded {len(ASRUser.audio_cache)} audio samples")
        else:
            logger.info(f"Using cached audio samples: {len(ASRUser.audio_cache)} files")

        self.start_time = time.time()

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
            self.token_expiry_time = time.time() + ASRUser.TOKEN_LIFETIME
        except Exception as e:
            logger.error(f"Login exception: {e}")
            self.access_token = None
            self.refresh_token = None
            self.token_expiry_time = time.time() + ASRUser.TOKEN_LIFETIME

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
                    self.token_expiry_time = time.time() + ASRUser.TOKEN_LIFETIME
                else:
                    logger.error(f"Token refresh failed ({response.status_code}), re-logging in")
                    self.login()
            except Exception as e:
                logger.error(f"Token refresh exception: {e}, re-logging in")
                self.login()

    def _load_audio_samples(self):
        samples_dir = Path(os.getenv("ASR_SAMPLES_DIR", "samples/ASR"))
        audio_files = (
            list(samples_dir.glob("*.mp3")) +
            list(samples_dir.glob("*.wav")) +
            list(samples_dir.glob("*.ogg"))
        )
        logger.info(f"Found {len(audio_files)} audio files in {samples_dir}")

        samples = []
        for f in audio_files:
            try:
                audio_bytes = f.read_bytes()
                b64 = base64.b64encode(audio_bytes).decode("utf-8")
                samples.append({
                    "filename": f.name,
                    "audioContent": b64,
                    "file_size_mb": f.stat().st_size / (1024 * 1024),
                    "base64_size_mb": len(b64) / (1024 * 1024)
                })
                logger.info(f"  {f.name} converted to base64")
            except Exception as e:
                logger.error(f"  Failed to load {f.name}: {e}")
        return samples

    @task
    def asr_task(self):
        if not ASRUser.audio_cache:
            logger.error("No audio samples available!")
            return

        if not self.access_token:
            logger.warning("No access token, attempting login...")
            self.login()

        self.token_refresh()

        audio_sample = next(ASRUser.audio_iterator)
        logger.info(f"Using sample: {audio_sample['filename']}")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key": ASRUser.api_key,
            "x-auth-source": "BOTH",
            "Connection": "keep-alive"
        }

        payload = {
            "audio": [{"audioContent": audio_sample["audioContent"]}],
            "config": {
                "serviceId": os.getenv("ASR_SERVICE_ID"),
                "language": {"sourceLanguage": os.getenv("ASR_SOURCE_LANGUAGE", "hi")},
                "audioFormat": os.getenv("ASR_AUDIO_FORMAT", "wav"),
                "samplingRate": int(os.getenv("ASR_SAMPLING_RATE", 16000)),
                "transcriptionFormat": "transcript",
                "bestTokenCount": 0
            },
            "controlConfig": {"dataTracking": False}
        }

        try:
            start_time = time.time()
            response = self.client.post(
                f"{base_url}/api/v1/asr/inference",
                headers=headers,
                json=payload,
                timeout=ASRUser.connection_timeout
            )
            elapsed = time.time() - start_time
            logger.info(f"ASR response: {response.status_code} ({elapsed:.2f}s)")
        except Exception as e:
            logger.error(f"ASR request failed: {e}")
