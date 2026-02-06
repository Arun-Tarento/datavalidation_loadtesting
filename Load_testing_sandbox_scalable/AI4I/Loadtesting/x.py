from locust import HttpUser, task, between, StopUser, events
from loguru import logger
from itertools import cycle
import time
import os

# ---------------- Logging ----------------
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/login_test_{time:YYYY-MM-DD_HH-mm-ss}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
    level="INFO"
)

BASE_URL = "https://sandbox.ai4inclusion.org"

# 100 pre-created users
TEST_ACCOUNTS = [
    {"email": f"test_user_{i}@test.com", "password": "Password@123"}
    for i in range(1, 101)
]

accounts_cycle = cycle(TEST_ACCOUNTS)

class LoginUser(HttpUser):
    host = BASE_URL
    wait_time = between(1, 2)

    def on_start(self):
        self.account = next(accounts_cycle)
        self.logged_in = False
        logger.info(f"👤 Assigned: {self.account['email']}")

    @task
    def login_once(self):
        if self.logged_in:
            raise StopUser()

        start = time.time()
        response = self.client.post(
            "/api/v1/auth/login",
            name="/api/v1/auth/login",
            json={
                "email": self.account["email"],
                "password": self.account["password"],
                "remember_me": False
            }
        )

        elapsed = time.time() - start

        if response.status_code == 200:
            self.logged_in = True
            logger.info(f"✅ {self.account['email']} logged in ({elapsed:.2f}s)")
            raise StopUser()
        else:
            logger.error(
                f"❌ {self.account['email']} failed "
                f"({response.status_code}) {response.text}"
            )
            raise StopUser()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("🏁 Login load test completed")
