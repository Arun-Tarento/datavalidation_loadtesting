from locust import HttpUser, task, between 
from loguru import logger
import base64
from pathlib import Path
import itertools
import os
import time
base_url = "https://sandbox.ai4inclusion.org"

class ASRUser(HttpUser):
    audio_cache = None
    audio_iterator = None
    wait_time = between(1, 5)
    api_key = "ak_31E6O1EHGgvk0tMAweXXwavp1ns7aCDs9vMI-iFVhC4"
    TOKEN_LIFETIME = 14*60  # seconds
    connection_timeout = 120  # seconds
    network_timeout = 120

    def on_start(self):
        self.login()

        
        if ASRUser.audio_cache is None:
            ASRUser.audio_cache = self.audio_samples_converted_to_base64()
            ASRUser.audio_iterator = itertools.cycle(ASRUser.audio_cache)
            logger.info(f"Loaded {len(ASRUser.audio_cache)} audio samples into cache")
        else:
            logger.info(f"Using cached audio samples: {len(ASRUser.audio_cache)} files")

        ##start timer
        self.start_time = time.time()

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
                                                            
            #logger.info(login_response.json())

            if login_response.status_code == 200:
                logger.info(f"Login successful with status code {login_response.status_code}")
            else:
                logger.error(f"Login failed with status code {login_response.status_code}")
            self.access_token = login_response.json().get("access_token")
            self.refresh_token = login_response.json().get("refresh_token")
            self.token_expiry_time = time.time() + ASRUser.TOKEN_LIFETIME
    
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
            self.token_expiry_time = time.time() + ASRUser.TOKEN_LIFETIME

    def audio_samples_converted_to_base64(self):
        audio_samples = []
        samples_dir = Path("/home/arun/Doc2/datavalidation_loadtesting/Samples/ASR")

        audio_files = list(samples_dir.glob("*.mp3")) + list(samples_dir.glob("*.wav")) + list(samples_dir.glob("*.ogg")) 
        
        logger.info(f"Found {len(audio_files)} audio files in {samples_dir}")

        for sam in audio_files:
            try:
                with open(sam, "rb") as f:
                    audio_to_binary = f.read()

                audio_samples_base64 = base64.b64encode(audio_to_binary)
                audio_samples_base64_string = audio_samples_base64.decode("utf-8")

                file_size_mb = os.path.getsize(sam) / (1024 * 1024)
                base64_size_mb = len(audio_samples_base64_string) / (1024 * 1024)

                audio_samples.append({"filename" : sam.name, "audioContent" : audio_samples_base64_string, "file_size_mb": file_size_mb, "base64_size_mb": base64_size_mb})
                logger.info(f"  {sam.name} converted to base64")
            except Exception as e:
                logger.error(f"  Failed to load {sam.name}: {e}")
    
        return audio_samples
        
        


    @task
    def asr_task(self):
        if not ASRUser.audio_cache:
            logger.error("No audio samples available!")
            return

        self.token_refresh()
    

        audio_sample = next(ASRUser.audio_iterator)
        logger.info(f"Using sample: {audio_sample['filename']}")

        headers  = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key" : ASRUser.api_key,
            "x-auth-source": "BOTH",
            "Connection": "keep-alive"  }

        try:
            
            start_time = time.time()
            asr_response = self.client.post(f"{base_url}/api/v1/asr/inference", 
                                            headers=headers, json={
                                            "audio": [
                                                {
                                                "audioContent": audio_sample['audioContent'],
                                                # "audioUri": "string"
                                                }
                                            ],
                                            "config": {
                                                "serviceId": "asr_am_ensemble",
                                                "language": {
                                                "sourceLanguage": "hi"
                                                },
                                                "audioFormat": "wav",
                                                "samplingRate": 16000,
                                                "transcriptionFormat": "transcript",
                                                "bestTokenCount": 0
                                            },
                                            "controlConfig": {
                                                "dataTracking":False 
                                            }
                                            
                                            }, timeout=ASRUser.connection_timeout)
                                            #catch_response=True )
            elasped = time.time() - start_time
            logger.info(f"ASR response: {asr_response.status_code}")
            logger.info(f"ASR request took {elasped:.2f} seconds")
        except Exception as e:
            logger.error(f"ASR request failed: {e}")


        






        
        
