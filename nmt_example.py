import os
from dotenv import load_dotenv

# Load env file based on ENV variable (default: staging)
# Usage: ENV=sandbox locust -f testing/AI4I/loadtesting/nmt_loadtesting.py ...
# env = os.getenv("ENV", "staging")
# load_dotenv(f"testing/.{env}.env", override=True)

from locust import HttpUser, task, between, events
from loguru import logger
import itertools
import time
import json
from metrics_tracker import MetricsTracker

base_url = os.getenv("BASE_URL")
metrics = MetricsTracker()


class NmtUser(HttpUser):
    source_cache = None
    source_iterator = None
    wait_time = between(1, 5)
    api_key = "ak_5e6LlSlsiv6PeV9R2CA8hQB9TuLouSd0-uf07fz4V6w"
    TOKEN_LIFETIME = 840
    connection_timeout = 120

    def on_start(self):
        self.start_time = time.time()
        self.request_count = 0
        self.access_token = None
        self.refresh_token = None
        self.token_expiry_time = 0

        self.login()

        if NmtUser.source_cache is None:
            # samples_file = os.getenv("NMT_SAMPLES_FILE")
            # with open(samples_file, "r", encoding="utf-8") as f:
            data = {
                    "nmt_samples": [
                        {
                        "source_id": "source_1",
                        "source": "आर्टिफिशियल इंटेलिजेंस के क्षेत्र में भारत की तरक्की कमाल की है, जो हेल्थकेयर, लैंग्वेज टेक्नोलॉजी और गवर्नेंस जैसे क्षेत्रों में इनोवेशन को बड़े पैमाने पर असल दुनिया के असर के साथ मिलाती है। देश का बढ़ता AI इकोसिस्टम रिसर्च, एथिकल डेवलपमेंट और सभी को शामिल करने वाले डिजिटल ट्रांसफॉर्मेशन के प्रति मज़बूत कमिटमेंट को दिखाता है।"
                        },
                        {
                        "source_id": "source_2",
                        "source": "देश का बढ़ता AI इकोसिस्टम रिसर्च के प्रति मज़बूत कमिटमेंट को दिखाता है।"
                        },
                        {
                        "source_id": "source_3",
                        "source": "भारत में प्रौद्योगिकी का विकास तेजी से हो रहा है। यह एक अतिरिक्त पाठ है जो नमूने की लंबाई को समायोज"
                        },
                        {
                        "source_id": "source_4",
                        "source": "शिक्षा और स्वास्थ्य सेवा में डिजिटल समाधान महत्वपूर्ण बदलाव ला रहे हैं।"
                        },
                        {
                        "source_id": "source_5",
                        "source": "कृत्रिम बुद्धिमत्ता भविष्य की तकनीक का एक महत्वपूर्ण हिस्सा है।"
                        },
                        {
                        "source_id": "source_6",
                        "source": "मशीन लर्निंग आधुनिक तकनीकी विकास का एक महत्वपूर्ण स्तंभ बन गया है।"
                        }]}
            NmtUser.source_cache = data["nmt_samples"]
            NmtUser.source_iterator = itertools.cycle(NmtUser.source_cache)
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
                    "email": "arunagiriperumal.atchilingam+01@tarento.com",
                    "password": "Password@123",
                    "remember_me": False
                }
            )
            if response.status_code == 200:
                logger.info(f"Login successful ({response.status_code})")
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_expiry_time = time.time() + NmtUser.TOKEN_LIFETIME
            else:
                logger.error(f"Login failed ({response.status_code}): {response.text[:200]}")
                self.access_token = None
                self.refresh_token = None
        except Exception as e:
            logger.error(f"Login exception: {e}")
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
                    logger.info("Token refresh successful")
                    self.access_token = response.json().get("access_token")
                    self.token_expiry_time = time.time() + NmtUser.TOKEN_LIFETIME
                else:
                    logger.error(f"Token refresh failed ({response.status_code}), re-logging in")
                    self.login()
            except Exception as e:
                logger.error(f"Token refresh exception: {e}, re-logging in")
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

        sample = next(NmtUser.source_iterator)
        source_text = sample["source"]
        logger.info(f"Sample {sample['source_id']}: {source_text[:80]}...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key": NmtUser.api_key,
            "x-auth-source": "BOTH",
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

            metrics.record_request(status_code, elapsed)
            self.request_count += 1

            if status_code == 200:
                logger.info(f"NMT success ({elapsed:.2f}s)")
            elif status_code == 401:
                logger.warning(f"NMT unauthorized ({elapsed:.2f}s) - clearing token")
                self.access_token = None
            elif status_code == 429:
                logger.warning(f"Rate limited ({elapsed:.2f}s)")
            else:
                logger.error(f"NMT failed: {status_code} ({elapsed:.2f}s)")
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

        logs_dir = os.getenv("LOGS_DIR", "testing/AI4I/logs")
        os.makedirs(logs_dir, exist_ok=True)
        filename = f"{logs_dir}/nmt_metrics_{env}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Metrics saved to {filename}")
    except Exception as e:
        logger.error(f"Error in test_stop handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
