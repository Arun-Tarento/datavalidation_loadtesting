from faker import Faker
import requests
import random
from loguru import logger 
import time
import base64

fake = Faker()
base_url = "https://sandbox.ai4inclusion.org"
ERROR_RATE = 1
token_expiry_time = 12*60
time_now = time.time()


class AsrUser():
    api_key = "ak_31E6O1EHGgvk0tMAweXXwavp1ns7aCDs9vMI-iFVhC4"
    def __init__(self):
        self.access_token = ""
        self.refresh_token = ""
        self.token_expiry_time = time_now
    def login(self):
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json={
                "email": "arunagiriperumal.atchilingam+01@tarento.com",
                "password": "Password@123",
                "remember_me": False
            }
        )
        self.access_token = response.json()["access_token"]
        self.refresh_token = response.json()["refresh_token"]
        self.token_expiry_time = time.time() + token_expiry_time

    def token_refresh(self):
            if time.time() > self.token_expiry_time:
                refresh_response = requests.post(f"{base_url}/api/v1/auth/refresh", json={
                                                                        "refresh_token": self.refresh_token
                                                                    })

                if refresh_response.status_code == 200:
                    logger.info(f"Token refresh successful with status code {refresh_response.status_code}")
                else:
                    logger.error(f"Token refresh failed with status code {refresh_response.status_code}")
                self.access_token = refresh_response.json().get("access_token")
                self.token_expiry_time = time.time() + token_expiry_time

    def get_audio_samples(self):
        with open("Samples/ASR/hindi_4s.wav", "rb") as f:
            audio_to_binary = f.read()
            audio_samples_base64 = base64.b64encode(audio_to_binary)
            audio_samples_base64_string = audio_samples_base64.decode("utf-8")
            return audio_samples_base64_string


    def send_request(self, force_error=None):
        self.token_refresh()
        headers = { "Authorization" : f"Bearer {self.access_token}", "Content-Type" : "application/json", "x-api-key" : self.api_key, "x-auth-source" : "BOTH"}
        endpoint = f"{base_url}/api/v1/asr/inference"
        audio_content = self.get_audio_samples()
        payload = {"audio": [{"audioContent": audio_content,
                                                # "audioUri": "string" 
                                                }],
                                            "config": {
                                                "serviceId": "asr_am_ensemble",
                                                "language": {
                                                "sourceLanguage": "hi"
                                                },
                                                "audioFormat": "wav",
                                                "samplingRate": 16000,
                                                "transcriptionFormat": "transcript",
                                                "bestTokenCount": 0},
                                            "controlConfig": {
                                                "dataTracking":False }}
        

        if force_error:  # Specific error requested
            error_type = force_error
        elif force_error is False:  # Explicitly valid
            error_type = None
        elif random.random() < ERROR_RATE:  # Random error
            error_type = random.choice(["400", "401", "403", "404", "500", "502", "503", "504"])
        else:  # Default: valid request
            error_type = None


      
        if error_type == "400": #bad_request, invalid payload
            payload = {"audio": [{"audioContent": fake.text(max_nb_chars=50),
                                            # "audioUri": "string" 
                                            }],
                                        "config": {
                                            "serviceId": "asr_am_ensemble",
                                            "language": {
                                            "sourceLanguage": "hi"
                                            },
                                            "audioFormat": "wav",
                                            "samplingRate": 16000,
                                            "transcriptionFormat": "transcript",
                                            "bestTokenCount": 0},
                                        "controlConfig": {
                                            "dataTracking":False }}

        elif error_type == "401":  # Unauthorized - Invalid/expired token
            headers["Authorization"] = "Bearer invalid_token_xyz123"
            payload = payload


        elif error_type == "403": ## Forbidden - Invalid API key
            headers["x-api-key"] = "invalid_api_key_12345"
            payload = payload  
            
        elif error_type == "404": # Not Found - Wrong endpoint
            endpoint = f"{base_url}/api/v1/asr/nonexistent_endpoint"
            payload = payload      

        elif error_type == "500": # Internal Server Error - Null/invalid values
            payload = {"audio": [{"audioContent": None
                                            # "audioUri": "string" 
                                            }],
                                        "config": {
                                            "serviceId": "None",
                                            "language": None,
                                            "audioFormat": "wav",
                                            "samplingRate": 16000,
                                            "transcriptionFormat": "transcript",
                                            "bestTokenCount": 0},
                                        "controlConfig": {
                                            "dataTracking":False }}

        elif error_type == "502": # Bad Gateway - Extremely large payload
            payload = {"audio": [{"audioContent": audio_content*200000,
                                            # "audioUri": "string" 
                                            }],
                                        "config": {
                                            "serviceId": "asr_am_ensemble",
                                            "language": {
                                            "sourceLanguage": "hi"
                                            },
                                            "audioFormat": "wav",
                                            "samplingRate": 16000,
                                            "transcriptionFormat": "transcript",
                                            "bestTokenCount": 0},"controlConfig": { "dataTracking":False }}
        else:
            logger.info("✅ Sending VALID request")
            payload = valid_payload


        try:
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=payload, 
                timeout=30)

            logger.info(f"📥 Response: {response.status_code}")
            return response

        except Exception as e:
            logger.error(f"💥 Exception: {e}")
            return None
                                                    
                                                



if __name__ == "__main__":
    user = AsrUser()
    logger.info("🔐 Logging in...")
    user.login()
    logger.info(f"✅ Login successful - Token: {user.access_token[:20]}...")

    # for error_code in ["400", "401", "403", "404", "500", "502"]:
    #     logger.info(f"\n--- Testing {error_code} Error ---")
    #     user.send_request(force_error=error_code)
    #     time.sleep(2)
    

    #Test specific error multiple times
    error_code = input("Enter error code: ").strip()
    num_requests = int(input("Enter number of requests: ").strip())
    for i in range(num_requests):
        logger.info(f"\n--- Request {i+1}/{num_requests} ---")
        
        if error_code == "valid":
            user.send_request(force_error=False)
        elif error_code == "random":
            user.send_request()
        else:
            user.send_request(force_error=error_code)
            
        time.sleep(1)
    
    logger.info("\n Errro have been susccefully sent!")




