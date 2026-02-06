import locust
from locust import HttpUser, task, between 
from loguru import logger
import base64
from pathlib import Path
import itertools
import os
import time
import json
base_url = "https://sandbox.ai4inclusion.org"


##  commands to run 
## locust -f  Load_testing_sandbox_scalable/AI4I/Loadtesting/nmt_loadtesting.py --users 100 --spawn-rate 1 --run-time 1h --host https://sandbox.ai4inclusion.org


class TTSUser(HttpUser):
    source_cache = None  
    source_iterator = None 
    wait_time = between(1, 5)
    api_key = "ak_wBjB5xSrqnxthZYVDM1Ay3Kpgm8quMgC-pfpQw3RTB8"
    TOKEN_LIFETIME = 14*60  # seconds
    connection_timeout = 120  # seconds
    network_timeout = 120

    def on_start(self):
        self.start_time = time.time()
        self.login()
        if TTSUser.source_cache is None:
            with open("Samples/TTS/tts_100_samples.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                TTSUser.source_cache = data["tts_samples"]
                TTSUser.source_iterator = itertools.cycle(TTSUser.source_cache)
                logger.info(f"✅ Loaded {len(TTSUser.source_cache)} TTS samples")

    def on_stop(self):
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time
        logger.info(f"Total time: {self.total_time} seconds")

    def login(self):
            login_response = self.client.post(f"{base_url}/api/v1/auth/login", json={
                                                                    "email": "arunagiriperumal.atchilingam+01@tarento.com",
                                                                    "password": "Password@123",
                                                                    "remember_me": False
                                                                })

            if login_response.status_code == 200:
                logger.info(f"Login successful with status code {login_response.status_code}")
            else:
                logger.error(f"Login failed with status code {login_response.status_code}")
            self.access_token = login_response.json().get("access_token")
            self.refresh_token = login_response.json().get("refresh_token")
            self.token_expiry_time = time.time() + TTSUser.TOKEN_LIFETIME


    def token_refresh(self):
        if time.time() > self.token_expiry_time:
            refresh_response = self.client.post(f"{base_url}/api/v1/auth/refresh", json={
                                                                    "refresh_token": self.refresh_token
                                                                })

            if refresh_response.status_code == 200:
                logger.info(f"Token refresh successful with status code {refresh_response.status_code}")
            else:
                logger.error(f"Token refresh failed with status code {refresh_response.status_code}")
            self.access_token = refresh_response.json().get("access_token")
            self.token_expiry_time = time.time() + TTSUser.TOKEN_LIFETIME


    @task
    def tts_task(self):
        self.token_refresh()
        sample = next(TTSUser.source_iterator)
        source_id = sample["source_id"]
        source_text = sample["source"]
        logger.info(f"Smaple used {source_id} : {source_text}")

        headers  = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key" : TTSUser.api_key,
            "x-auth-source": "BOTH",
            "Connection": "keep-alive"  }


        payload = {"input":[{"source":source_text}],"config":{"language":{"sourceLanguage":"hi"},"serviceId":"indic-tts-coqui-indo_aryan","gender":"female","samplingRate":22050,"audioFormat":"wav"},"controlConfig":{"dataTracking":False}}

        try:
            start_time = time.time()
            tts_response = self.client.post(url=f"{base_url}/api/v1/tts/inference", headers=headers, json=payload, timeout= TTSUser.connection_timeout )
            elasped = time.time() - start_time
            logger.info(f"TTS response: {tts_response.status_code}")
            logger.info(f"TTS request took {elasped:.2f} seconds")
        except Exception as e:
            logger.error(f"TTS request failed: {e}")
        