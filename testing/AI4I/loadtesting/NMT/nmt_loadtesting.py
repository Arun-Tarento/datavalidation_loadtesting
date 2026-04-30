import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load env file based on ENV variable (default: staging)
# locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 1h
# ENV=sandbox locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 1h

load_dotenv("testing/.env")
env = os.getenv("ENVIRONMENT", "staging")

from locust import HttpUser, task, between, events
from loguru import logger
import itertools
import time
import json
import random
from metrics_tracker import MetricsTracker

base_url = os.getenv("BASE_URL")
metrics = MetricsTracker()

# Create test account pool
email_pattern = os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com")
password = os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123")
account_count = int(os.getenv("TEST_ACCOUNT_COUNT", 100))

TEST_ACCOUNTS = [
    {"email": email_pattern.format(i), "password": password}
    for i in range(1, account_count + 1)
]

# Iterator to assign unique accounts to each user
TEST_ACCOUNTS_ITERATOR = itertools.cycle(TEST_ACCOUNTS)


class NmtUser(HttpUser):
    source_cache = None
    wait_time = between(0.1, 0.2)  # Variable wait time (1-5 seconds) simulates real user behavior
    TOKEN_LIFETIME = int(os.getenv("TOKEN_LIFETIME", 840))
    connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", 120))

    def on_start(self):
        self.start_time = time.time()
        self.request_count = 0
        self.access_token = None
        self.refresh_token = None
        self.token_expiry_time = 0

        # Assign unique test account to this user (round-robin)
        self.account = next(TEST_ACCOUNTS_ITERATOR)
        logger.info(f"User assigned: {self.account['email']}")

        self.login()

        # Load samples once (shared across all users)
        if NmtUser.source_cache is None:
            samples_file = os.getenv("NMT_SAMPLES_FILE")
            with open(samples_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                NmtUser.source_cache = data["nmt_samples"]
                logger.info(f"Loaded {len(NmtUser.source_cache)} NMT samples from {samples_file}")

    def on_stop(self):
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        logger.info(f"USER SESSION SUMMARY: duration={total_time:.2f}s requests={self.request_count}")

    def login(self):
        try:
            response = self.client.post(
                f"{base_url}/api/v1/auth/login",
                json={
                    "email": self.account["email"],
                    "password": self.account["password"],
                    "remember_me": False
                }
            )
            if response.status_code == 200:
                logger.info(f"{self.account['email']} - Login successful ({response.status_code})")
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_expiry_time = time.time() + NmtUser.TOKEN_LIFETIME
            else:
                logger.error(f"{self.account['email']} - Login failed ({response.status_code}): {response.text[:200]}")
                self.access_token = None
                self.refresh_token = None
        except Exception as e:
            logger.error(f"{self.account['email']} - Login exception: {e}")
            self.access_token = None
            self.refresh_token = None

    def token_refresh(self):
        if time.time() > self.token_expiry_time:
            try:
                response = self.client.post(
                    f"{base_url}/api/v1/auth/refresh",
                    json={"refresh_token": self.refresh_token}
                )
                if response.status_code == 200:
                    logger.info(f"{self.account['email']} - Token refresh successful")
                    self.access_token = response.json().get("access_token")
                    self.token_expiry_time = time.time() + NmtUser.TOKEN_LIFETIME
                else:
                    logger.error(f"{self.account['email']} - Token refresh failed ({response.status_code}), re-logging in")
                    self.login()
            except Exception as e:
                logger.error(f"{self.account['email']} - Token refresh exception: {e}, re-logging in")
                self.login()

    @task
    def nmt_task(self):
        if not self.access_token:
            logger.warning("No access token, attempting login...")
            self.login()
            if not self.access_token:
                logger.warning("Login failed, skipping NMT request")
                return

        self.token_refresh()

        if not self.access_token:
            logger.warning("Still no token after refresh, skipping NMT request")
            return

        # Each user randomly picks a sample (realistic user behavior)
        sample = random.choice(NmtUser.source_cache)
        source_text = sample["source"]
        logger.info(f"Sample {sample['source_id']}: {source_text[:80]}...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-User-Id": self.account["email"],  # Rate limiting key (per-user)
            "Connection": "keep-alive"
        }

        payload = {
            "input": [{"source": source_text}],
            "config": {
                "serviceId": os.getenv("NMT_SERVICE_ID"),
                "language": {
                    "sourceLanguage": os.getenv("NMT_SOURCE_LANGUAGE", "hi"),
                    "targetLanguage": os.getenv("NMT_TARGET_LANGUAGE", "en")
                }
            },
            "controlConfig": {"additionalProp1": {"dataTracking": False}}
        }

        start_time = time.time()
        try:
            response = self.client.post(
                url=f"{base_url}/api/v1/nmt/inference",
                headers=headers,
                json=payload,
                timeout=NmtUser.connection_timeout
            )
            elapsed = time.time() - start_time
            status_code = response.status_code

            # Extract timing headers from response
            trace_id = response.headers.get("x-trace-id")
            trace_url = f"{base_url}/jaeger/trace/{trace_id}" if trace_id else None

            # Extract server-side processing time (excludes network latency)
            server_time = float(response.headers.get("x-process-time", elapsed))

            # Extract inference time (in milliseconds, convert to seconds)
            # Handle both formats: "353.0" and "353.0ms"
            inference_time_str = response.headers.get("X-Inference-Model-Time", "0")
            inference_time_ms = float(inference_time_str.replace("ms", "").strip()) if inference_time_str else 0
            inference_time = inference_time_ms / 1000.0 if inference_time_ms > 0 else 0

            # Calculate non-inference time: x-process-time - (X-Inference-Model-Time / 1000)
            # This gives pure server-side API overhead (auth, preprocessing, postprocessing)

            metrics.record_request(
                status_code=status_code,
                response_time=server_time,    # x-process-time (server-side total)
                trace_id=trace_id,
                inference_time=inference_time  # X-Inference-Model-Time (ML/GPU only)
            )
            self.request_count += 1

            if status_code == 200:
                logger.info(f"NMT success ({elapsed:.2f}s) trace={trace_url}")
            elif status_code == 401:
                logger.warning(f"NMT unauthorized ({elapsed:.2f}s) trace={trace_url} - clearing token")
                self.access_token = None
            elif status_code == 429:
                logger.warning(f"Rate limited ({elapsed:.2f}s) trace={trace_url}")
            else:
                logger.error(f"NMT failed: {status_code} ({elapsed:.2f}s) trace={trace_url}")
        except Exception as e:
            elapsed = time.time() - start_time
            metrics.record_request(0, elapsed, str(e))
            self.request_count += 1
            logger.error(f"NMT exception: {e} ({elapsed:.2f}s)")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    metrics.start_time = time.time()
    logger.info(f"Load test started [{env} environment]")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    try:
        metrics.end_time = time.time()
        logger.info("=" * 80)
        logger.info("LOAD TEST COMPLETED")
        logger.info("=" * 80)

        summary = metrics.get_summary()
        if "error" in summary:
            logger.error(f"Error generating summary: {summary['error']}")
            return

        logger.info(f"Total Requests:  {summary['total_requests']}")
        logger.info(f"Successful:      {summary['successful']} ({summary['success_rate']})")
        logger.info(f"Failed:          {summary['failed']}")
        logger.info(f"Duration:        {summary['duration_seconds']}s")
        logger.info(f"Throughput:      {summary['requests_per_second']} req/s")
        logger.info(f"Response Times:  min={summary['response_times']['min']} avg={summary['response_times']['avg']} p95={summary['response_times']['p95']} max={summary['response_times']['max']}")

        if summary['status_codes']:
            logger.info(f"Status Codes: {summary['status_codes']}")
        if summary['top_errors']:
            logger.info(f"Top Errors: {summary['top_errors']}")

        # Print detailed request timing table
        print("\n")
        metrics.print_detailed_table()

        # Print inference breakdown if available
        if 'avg_inference_time' in summary:
            print(f"\n{'='*80}")
            print("INFERENCE vs NON-INFERENCE BREAKDOWN")
            print(f"{'='*80}")
            print(f"Avg Total Response Time:     {summary['response_times']['avg']}")
            print(f"Avg Inference Time:          {summary['avg_inference_time']} ({summary['inference_percentage']})")
            print(f"Avg Non-Inference Time:      {summary['avg_non_inference_time']} ({summary['non_inference_percentage']})")
            print(f"{'='*80}\n")

        logs_dir = os.getenv("LOGS_DIR", "testing/AI4I/logs")
        os.makedirs(logs_dir, exist_ok=True)

        # Save JSON summary
        filename = f"{logs_dir}/nmt_metrics_{env}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Metrics saved to {filename}")

        # Save detailed CSV
        csv_filename = f"{logs_dir}/nmt_detailed_timings_{env}_{int(time.time())}.csv"
        try:
            import csv
            with open(csv_filename, "w", newline='') as csvfile:
                fieldnames = ['request_num', 'status_code', 'server_time', 'inference_time', 'non_inference_time', 'inference_percentage', 'trace_id']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for req in summary.get('detailed_requests', []):
                    server_time = req['server_time']
                    writer.writerow({
                        'request_num': req['request_num'],
                        'status_code': req['status_code'],
                        'server_time': f"{server_time:.3f}",
                        'inference_time': f"{req['inference_time']:.3f}",
                        'non_inference_time': f"{req['non_inference_time']:.3f}",
                        'inference_percentage': f"{(req['inference_time']/server_time*100):.1f}" if server_time > 0 and req['inference_time'] > 0 else "0.0",
                        'trace_id': req['trace_id'] or ''
                    })
            logger.info(f"Detailed timings CSV saved to {csv_filename}")
        except Exception as e:
            logger.warning(f"Could not save CSV: {e}")
    except Exception as e:
        logger.error(f"Error in test_stop handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
