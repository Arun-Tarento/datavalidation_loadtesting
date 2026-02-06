from locust import HttpUser, task, between, events
from loguru import logger
import time
import random
import os
from locust_plugins.listeners.influxdb import  InfluxDBSettings
from locust_plugins.listeners import InfluxDB2Listener


influxdb_settings = InfluxDBSettings(
    host="localhost",
    port=8086,
    token="ZqSVoOFsf60VS_zDHb7YIGSWfd1k2XYgyGSWJuU7Pd6RN1Id7ZQLp7Ky1iDlgXI78jYRJxIjLgfMh86z6eFszw==",  # From step 2
    org="ai4i",
    bucket="locust_bucket"
)

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    InfluxDBListener(env=environment, **influxdb_settings.__dict__)



# Setup logging
os.makedirs("logs", exist_ok=True)
logger.add(
    "Load_testing_sandbox_scalable/AI4I/logs/login_test_{time:YYYY-MM-DD_HH-mm-ss}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)

base_url = "https://sandbox.ai4inclusion.org"

# Option 1: If you have 100 created accounts
TEST_ACCOUNTS = [
    {"email": f"ltest_user_{i}@tet.com", "password": "Password@123"}  # ← Fix typo
    for i in range(1, 101)
]

class LoginUser(HttpUser):
    wait_time = between(1, 3)
    host = base_url

    def on_start(self):
        """Pick a random test account"""
        self.account = random.choice(TEST_ACCOUNTS)
        logger.info(f"👤 User assigned: {self.account['email']}")

    @task
    def login_task(self):
        start_time = time.time()
        
        response = self.client.post(
            "/api/v1/auth/login",  # ← Use relative URL (host already set)
            name="/api/v1/auth/login",  # ← For Locust stats grouping
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
            logger.error(f"❌ {self.account['email']} failed ({response.status_code})")


        # ##### logout
        #     activity_time = random.uniform(2, 5)  # 2-5 seconds of "work"
        #     time.sleep(activity_time)
                
        #     # 3. Logout
        #     logout_start = time.time()
        #     logout_response = self.client.post(
        #         "/api/v1/auth/logout",
        #         name="/api/v1/auth/logout",
        #         headers={"Authorization": f"Bearer {self.access_token}"}, json={"refresh_token": self.refresh_token}
        #     )
        #     logout_elapsed = time.time() - logout_start
            
        #     if logout_response.status_code == 200:
        #         logger.info(f"🚪 {self.account['email']} logged out ({logout_elapsed:.2f}s)")
        #     else:
        #         logger.error(f"❌ {self.account['email']} logout failed ({logout_response.status_code})")
                
        # else:
        #     logger.error(f"❌ {self.account['email']} login failed ({response.status_code})")




@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("🏁 Load test completed")

# ---

# ## **🎯 What This Code Will Do:**

# ### **With Random Assignment (Recommended for now):**
# ```
# 20 users spawn:
# - User 1 → Random account (e.g., +01)
# - User 2 → Random account (e.g., +03)
# - User 3 → Random account (e.g., +01) ← Can be same as User 1
# ...

# Each user:
# 1. Picks random account
# 2. Attempts login once
# 3. Logs result
# 4. Stops (doesn't retry)

# Result: Still some duplicate collision possible, but much less
# ```

# ### **Expected Results with Random (5 accounts, 20 users):**
# ```
# Best case (all pick different accounts at different times):
# - Success rate: ~80-90%
# - Response time: 0.5-2s
# - Some duplicates still (birthday paradox)

# Realistic case (some collision):
# - Success rate: ~60-70%
# - Response time: 1-5s
# - ~30-40% duplicates

# Current bug case (same expiry second):
# - Success rate: ~50% (same as before)
# - Response time: 10-15s
# - Still failing due to token bug