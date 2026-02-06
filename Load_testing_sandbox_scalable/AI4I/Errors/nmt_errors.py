from faker import Faker
import requests
import random
from loguru import logger 
import time
import base64
import json


fake = Faker()
base_url = "https://sandbox.ai4inclusion.org"
ERROR_RATE = 1
token_expiry_time = 12*60
time_now = time.time()


class NmtUser():
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


    def fetch_samples(self):
        with open("Samples/NMT/nmt_100_samples.json", "r") as f:
            file = json.load(f)

        random_sample = random.choice(file["nmt_samples"])
        return random_sample

    def send_nmt_request(self, force_error=None):
        self.token_refresh()
        headers = { "Authorization" : f"Bearer {self.access_token}", "Content-Type" : "application/json", "x-api-key" : NmtUser.api_key, "x-auth-source" : "BOTH"}
        endpoint = f"{base_url}/api/v1/nmt/inference"
        sample = self.fetch_samples()
        source_id = sample["source_id"]
        source_text = sample["source"]
        
        payload = { "input": [{"source": source_text}],
        "config": {"serviceId": "ai4bharat/indictrans--gpu-t4","language": {"sourceLanguage": "hi","targetLanguage": "en"}},
        "controlConfig": {"additionalProp1": {"dataTracking":False}}}

        if force_error:
            error_type = force_error
        elif force_error is False:
            error_type = None
        elif random.random() < ERROR_RATE:
            error_type = random.choice(["400", "401", "403", "404", "500", "502"])
        else:
            error_type = None

        if error_type:
            logger.info(f"Triggering error: {error_type}")

            if error_type == "400": #Bad request
                payload = {"input": [{"source": ""}],
                "config": {"serviceId": "ai4bharat/indictrans--gpu-t4","language": {"sourceLanguage": "hi","targetLanguage": "en"}},
                "controlConfig": {"additionalProp1": {"dataTracking":False}}} 

            elif error_type == "401": #Unauthorized
                headers["Authorization"] = "Bearer invalid_token_xyz123"

            elif error_type == "403": #Forbidden
                headers["x-api-key"] = "invalid_api_key_12345"

            elif error_type == "404": #Not Found
                endpoint = f"{base_url}/api/v1/nmt/nonexistent_endpoint"

            elif error_type == "500": #Internal Server Error
                payload = { "input": [{"source": None}],
                "config": {"serviceId": "None","language": {"sourceLanguage": "hi","targetLanguage": "en"}},
                "controlConfig": {"additionalProp1": {"dataTracking":False}}}

            elif error_type == "502": #Bad Gateway - Extremely large text
                payload = { "input": [{"source": source_text*100000}],
                "config": {"serviceId": "ai4bharat/indictrans--gpu-t4","language": {"sourceLanguage": "hi","targetLanguage": "en"}},
                "controlConfig": {"additionalProp1": {"dataTracking":False}}}

        else:
            logger.info("Sending a valid request")


        try:
            response = requests.post(url=f"{base_url}/api/v1/nmt/inference",  headers=headers, json=payload,  timeout=30)
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.json()}")

        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

if __name__ =="__main__":
    user = NmtUser()
    logger.info("logging in ")
    user.login()
    logger.info(f"✅ Login successful - Token: {user.access_token[:20]}...")


    error_code = input("Enter error code: ").strip()
    
    num_requests = int(input("Enter number of requests: ").strip())

    for i in range(num_requests):
        logger.info(f"\n--- Request {i+1}/{num_requests} ---")
        
        if error_code == "valid":
            user.send_request(force_error=False)
        elif error_code == "random":
            user.send_request()
        else:
            user.send_nmt_request(force_error=error_code)
            
        time.sleep(1)
    
    logger.info("\n Errro have been susccefully sent!")