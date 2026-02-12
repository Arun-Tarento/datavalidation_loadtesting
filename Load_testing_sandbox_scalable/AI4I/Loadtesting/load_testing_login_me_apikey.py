from locust import HttpUser, task, between, events
from loguru import logger
import time
import random
import os

# Setup logging
os.makedirs("Load_testing_sandbox_scalable/AI4I/logs", exist_ok=True)
logger.add(
    "Load_testing_sandbox_scalable/AI4I/logs/login_test_{time:YYYY-MM-DD_HH-mm-ss}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)

base_url = "https://sandbox.ai4inclusion.org"

# 100 test accounts
TEST_ACCOUNTS = [
    {"email": f"ltest_user_{i}@tet.com", "password": "Password@123"}
    for i in range(1, 101)
]

class LoginUser(HttpUser):
    wait_time = between(2, 5)
    host = base_url

    def on_start(self):
        """Pick a random test account and login ONCE"""
        self.account = random.choice(TEST_ACCOUNTS)
        self.access_token = None
        self.refresh_token = None
        logger.info(f"👤 User assigned: {self.account['email']}")
        
        # Login once when user starts
        self.login()

    def login(self):
        """Login method - called once in on_start"""
        start_time = time.time()
        
        response = self.client.post(
            "/api/v1/auth/login",
            name="/api/v1/auth/login",
            json={
                "email": self.account['email'],
                "password": self.account['password'],
                "remember_me": False
            }
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            logger.info(f"✅ {self.account['email']} logged in ({elapsed:.2f}s)")
            self.access_token = response.json().get("access_token")
            self.refresh_token = response.json().get("refresh_token")
        else:
            logger.error(f"❌ {self.account['email']} login failed ({response.status_code})")

    @task(5)
    def get_user_profile(self):
        """GET /api/v1/auth/me - Fetch current user info"""
        if not self.access_token:
            logger.warning(f"⚠️ No access token for {self.account['email']}, skipping")
            return
        
        start_time = time.time()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # ✅ Use WITH block for catch_response=True
        with self.client.get(
            "/api/v1/auth/me",
            name="/api/v1/auth/me",
            headers=headers,
            catch_response=True
        ) as response:
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"✅ {self.account['email']} - /me fetched ({elapsed:.2f}s)")
                response.success()
            elif response.status_code == 401:
                logger.warning(f"⚠️ {self.account['email']} token expired, re-logging in")
                self.login()
                response.failure("Token expired")
            else:
                logger.error(f"❌ {self.account['email']} - /me failed ({response.status_code})")
                response.failure(f"Status {response.status_code}")

    @task(2)
    def get_api_keys(self):
        """GET /api/v1/auth/api-keys - Fetch user's API keys"""
        if not self.access_token:
            logger.warning(f"⚠️ No access token for {self.account['email']}, skipping")
            return
        
        start_time = time.time()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # ✅ Use WITH block for catch_response=True
        with self.client.get(
            "/api/v1/auth/api-keys",
            name="/api/v1/auth/api-keys",
            headers=headers,
            catch_response=True
        ) as response:
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"✅ {self.account['email']} - api-keys fetched ({elapsed:.2f}s)")
                response.success()
            elif response.status_code == 401:
                logger.warning(f"⚠️ {self.account['email']} token expired, re-logging in")
                self.login()
                response.failure("Token expired")
            else:
                logger.error(f"❌ {self.account['email']} - api-keys failed ({response.status_code})")
                response.failure(f"Status {response.status_code}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("🏁 Load test completed")
    