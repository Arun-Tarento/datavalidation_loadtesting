import locust
from locust import HttpUser, task, between, events
from loguru import logger
import base64
from pathlib import Path
import itertools
import os
import time
import json
from metrics_tracker import MetricsTracker

base_url = "https://sandbox.ai4inclusion.org"
metrics = MetricsTracker()

##  commands to run 
## locust -f  Load_testing_sandbox_scalable/AI4I/Loadtesting/nmt_loadtesting.py --users 100 --spawn-rate 1 --run-time 1h --host https://sandbox.ai4inclusion.org




class NmtUser(HttpUser):
    source_cache = None  
    source_iterator = None 
    wait_time = between(1, 5)
    api_key = "ak_5hDfQ9gu_toAG8cmT_8O-ieRmUFk59VubfK6Mf7Q8F0"
    TOKEN_LIFETIME = 14*60  # seconds
    connection_timeout = 120  # seconds
    network_timeout = 120

    def on_start(self):
        self.start_time = time.time()
        self.login()
        self.request_count = 0  
        
        if NmtUser.source_cache is None:
            with open("Samples/NMT/nmt_100_samples.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                NmtUser.source_cache = data["nmt_samples"]
                NmtUser.source_iterator = itertools.cycle(NmtUser.source_cache)
                logger.info(f"✅ Loaded {len(NmtUser.source_cache)} NMT samples")

    def on_stop(self):
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time
        logger.info(f"Total time: {self.total_time} seconds")
        
        # ✅ Per-user summary
        logger.info(f"👤 USER SESSION SUMMARY:")
        logger.info(f"   Duration: {self.total_time:.2f}s")
        logger.info(f"   Requests made: {getattr(self, 'request_count', 0)}")       


    def login(self):
        try:
            login_response = self.client.post(f"{base_url}/api/v1/auth/login", json={
                                                                    "email": "arunagiriperumal.atchilingam+01@tarento.com",
                                                                    "password": "Password@123",
                                                                    "remember_me": False
                                                                })
                                                            
            #logger.info(login_response.json())

            if login_response.status_code == 200:
                logger.info(f"✅ Login successful with status code {login_response.status_code}")
                # ✅ Only parse JSON on success
                data = login_response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_expiry_time = time.time() + NmtUser.TOKEN_LIFETIME
            else:
                logger.error(f"❌ Login failed with status code {login_response.status_code}")
                # ✅ Don't try to parse JSON on error
                logger.error(f"Response: {login_response.text[:200]}")  # Log first 200 chars
                self.access_token = None
                self.refresh_token = None
                
        except Exception as e:
            logger.error(f"❌ Login exception: {e}")
            self.access_token = None
            self.refresh_token = None
    
    def token_refresh(self):
        """Refresh access token"""
        if time.time() > self.token_expiry_time:
            try:
                refresh_response = self.client.post(
                    f"{base_url}/api/v1/auth/refresh",
                    json={"refresh_token": self.refresh_token}
                )
                
                if refresh_response.status_code == 200:
                    logger.info(f"✅ Token refresh successful")
                    data = refresh_response.json()
                    self.access_token = data.get("access_token")
                    self.token_expiry_time = time.time() + NmtUser.TOKEN_LIFETIME
                else:
                    logger.error(f"❌ Token refresh failed: {refresh_response.status_code}")
                    self.access_token = None
                    
            except Exception as e:
                logger.error(f"❌ Token refresh exception: {e}")
                self.access_token = None

    @task
    def nmt_task(self):
        """NMT translation task"""
        # ✅ Skip if no access token
        if not self.access_token:
            logger.warning("⚠️ No access token, skipping NMT request")
            return
        
        self.token_refresh()
        
        # ✅ Check again after refresh attempt
        if not self.access_token:
            logger.warning("⚠️ Token refresh failed, skipping NMT request")
            return
        
        sample = next(NmtUser.source_iterator)
        source_id = sample["source_id"]
        source_text = sample["source"]
        logger.info(f"Sample used {source_id}: {source_text}")

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
                "serviceId": "ai4bharat/indictrans--gpu-t4",
                "language": {"sourceLanguage": "hi", "targetLanguage": "en"}
            },
            "controlConfig": {"additionalProp1": {"dataTracking": False}}
        }

        start_time = time.time()
        error = None
        status_code = 0
        
        try:
            nmt_response = self.client.post(
                url=f"{base_url}/api/v1/nmt/inference",
                headers=headers,
                json=payload,
                timeout=NmtUser.connection_timeout
            )
            elapsed = time.time() - start_time
            status_code = nmt_response.status_code
            
            # ✅ Record metrics
            metrics.record_request(status_code, elapsed)
            self.request_count += 1
            
            if status_code == 200:
                logger.info(f"✅ NMT success: {status_code} ({elapsed:.2f}s)")
            else:
                logger.error(f"❌ NMT failed: {status_code} ({elapsed:.2f}s)")
                
        except Exception as e:
            elapsed = time.time() - start_time
            error = str(e)
            status_code = 0
            
            metrics.record_request(status_code, elapsed, error)
            self.request_count += 1
            logger.error(f"❌ NMT request failed: {e} ({elapsed:.2f}s)")

# ✅ Event listeners with error handling
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        metrics.start_time = time.time()
        logger.info("🚀 Load test started")
    except Exception as e:
        logger.error(f"Error in test_start: {e}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    try:
        metrics.end_time = time.time()
        
        logger.info("=" * 80)
        logger.info("🏁 LOAD TEST COMPLETED")
        logger.info("=" * 80)
        
        summary = metrics.get_summary()
        
        # ✅ Check for errors in summary
        if "error" in summary:
            logger.error(f"Error generating summary: {summary['error']}")
            return
        
        logger.info(f"\n📊 SUMMARY STATISTICS:")
        logger.info(f"  Total Requests:       {summary['total_requests']}")
        logger.info(f"  Successful:           {summary['successful']} ({summary['success_rate']})")
        logger.info(f"  Failed:               {summary['failed']}")
        logger.info(f"  Duration:             {summary['duration_seconds']}s")
        logger.info(f"  Throughput:           {summary['requests_per_second']} req/s")
        
        logger.info(f"\n⏱️  RESPONSE TIMES:")
        logger.info(f"  Minimum:              {summary['response_times']['min']}")
        logger.info(f"  Average:              {summary['response_times']['avg']}")
        logger.info(f"  Median:               {summary['response_times']['median']}")
        logger.info(f"  95th Percentile:      {summary['response_times']['p95']}")
        logger.info(f"  99th Percentile:      {summary['response_times']['p99']}")
        logger.info(f"  Maximum:              {summary['response_times']['max']}")
        
        if summary['status_codes']:
            logger.info(f"\n📈 STATUS CODES:")
            for code, count in sorted(summary['status_codes'].items()):
                logger.info(f"  {code}: {count} requests")
        
        if summary['top_errors']:
            logger.info(f"\n❌ TOP ERRORS:")
            for error, count in summary['top_errors'].items():
                logger.info(f"  {error[:100]}: {count} occurrences")
        
        logger.info("=" * 80)
        
        # ✅ Save to JSON with error handling
        try:
            os.makedirs("Load_testing_sandbox_scalable/AI4I/logs", exist_ok=True)
            with open(f"Load_testing_sandbox_scalable/AI4I/logs/metrics_summary_{int(time.time())}.json", "w") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"📁 Metrics saved to Load_testing_sandbox_scalable/AI4I/logs/metrics_summary_{int(time.time())}.json")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            
    except Exception as e:
        logger.error(f"Error in test_stop handler: {e}")
        import traceback
        logger.error(traceback.format_exc())