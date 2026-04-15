import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: locust -f testing/AI4I/loadtesting/login_test_concurrency.py -u 1 -r 1 -t 3m --host=https://staging.ai4inclusion.org
env = os.getenv("ENV", "staging")
load_dotenv(f"testing/.{env}.env", override=True)

from locust import HttpUser, task, between, events, constant
from loguru import logger
import time
import random

logs_dir = os.getenv("LOGS_DIR", "testing/AI4I/logs")
os.makedirs(logs_dir, exist_ok=True)
logger.add(
    f"{logs_dir}/login_test_{{time:YYYY-MM-DD_HH-mm-ss}}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)

base_url = os.getenv("BASE_URL")
email_pattern = os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com")
password = os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123")
account_count = int(os.getenv("TEST_ACCOUNT_COUNT", 9))

TEST_ACCOUNTS = [
    {"email": email_pattern.format(i), "password": password}
    for i in range(1, account_count + 1)
]


class LoginUser(HttpUser):
    wait_time = constant(20)
    host = base_url

    def on_start(self):
        self.account = random.choice(TEST_ACCOUNTS)
        logger.info(f"User assigned: {self.account['email']}")

    @task
    def login_task(self):
        start_time = time.time()

        response = self.client.post(
            "/api/v1/auth/login",
            name="/api/v1/auth/login",
            json={
                "email": self.account["email"],
                "password": self.account["password"],
                "remember_me": False
            }
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            logger.info(f"{self.account['email']} logged in ({elapsed:.2f}s)")
            self.access_token = response.json().get("access_token")
            self.refresh_token = response.json().get("refresh_token")
        else:
            logger.error(f"{self.account['email']} failed ({response.status_code})")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("Load test completed")
