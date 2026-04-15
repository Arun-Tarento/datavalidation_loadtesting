import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: ENV=sandbox locust -f testing/AI4I/loadtesting/x.py ...
env = os.getenv("ENV", "staging")
load_dotenv(f"testing/.{env}.env", override=True)

from locust import HttpUser, task, between, StopUser, events
from loguru import logger
from itertools import cycle
import time

logs_dir = os.getenv("LOGS_DIR", "testing/AI4I/logs")
os.makedirs(logs_dir, exist_ok=True)
logger.add(
    f"{logs_dir}/login_test_{{time:YYYY-MM-DD_HH-mm-ss}}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
    level="INFO"
)

base_url = os.getenv("BASE_URL")
email_pattern = os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com")
password = os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123")
account_count = int(os.getenv("TEST_ACCOUNT_COUNT", 100))

TEST_ACCOUNTS = [
    {"email": email_pattern.format(i), "password": password}
    for i in range(1, account_count + 1)
]

accounts_cycle = cycle(TEST_ACCOUNTS)


class LoginUser(HttpUser):
    host = base_url
    wait_time = between(1, 2)

    def on_start(self):
        self.account = next(accounts_cycle)
        self.logged_in = False
        logger.info(f"Assigned: {self.account['email']}")

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
            logger.info(f"{self.account['email']} logged in ({elapsed:.2f}s)")
        else:
            logger.error(f"{self.account['email']} failed ({response.status_code}) {response.text}")

        raise StopUser()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("Login load test completed")
