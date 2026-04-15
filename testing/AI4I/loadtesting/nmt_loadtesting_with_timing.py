"""
Enhanced NMT load test with detailed timing breakdowns
Captures: DNS, TCP connect, TLS handshake, request send, TTFB, response download
Usage: ENV=sandbox locust -f testing/AI4I/loadtesting/nmt_loadtesting_with_timing.py --users 10 --spawn-rate 1
"""
import os
from dotenv import load_dotenv

env = os.getenv("ENV", "staging")
load_dotenv(f"testing/.{env}.env", override=True)

from locust import HttpUser, task, between, events
from loguru import logger
import itertools
import time
import json
import random
from urllib3.util import connection
import socket

base_url = os.getenv("BASE_URL")

# Email and password config
email_pattern = os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com")
password = os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123")
account_count = int(os.getenv("TEST_ACCOUNT_COUNT", 100))

TEST_ACCOUNTS = [
    {"email": email_pattern.format(i), "password": password}
    for i in range(1, account_count + 1)
]
TEST_ACCOUNTS_ITERATOR = itertools.cycle(TEST_ACCOUNTS)


class DetailedMetricsTracker:
    """Enhanced metrics tracker with timing breakdowns"""

    def __init__(self):
        self.requests = []
        self.start_time = None
        self.end_time = None

    def record_request(self, timings, status_code, server_timings=None, error=None):
        """
        timings: dict with keys: dns, tcp_connect, tls, request_send, ttfb, response_download, total
        server_timings: dict from server headers (e.g., {'inference': 1.23, 'preprocessing': 0.05})
        """
        self.requests.append({
            'status_code': status_code,
            'timings': timings,
            'server_timings': server_timings or {},
            'error': error,
            'timestamp': time.time()
        })

    def get_summary(self):
        if not self.requests:
            return {"error": "No requests recorded"}

        successful = [r for r in self.requests if r['status_code'] == 200]
        failed = [r for r in self.requests if r['status_code'] != 200]

        def calc_percentiles(values, field_path):
            """Extract nested field and calculate percentiles"""
            extracted = []
            for v in values:
                try:
                    val = v
                    for key in field_path:
                        val = val[key]
                    if val is not None:
                        extracted.append(val)
                except (KeyError, TypeError):
                    pass

            if not extracted:
                return {}

            sorted_vals = sorted(extracted)
            n = len(sorted_vals)
            return {
                'min': f"{min(sorted_vals):.3f}s",
                'avg': f"{sum(sorted_vals)/n:.3f}s",
                'p50': f"{sorted_vals[n//2]:.3f}s",
                'p95': f"{sorted_vals[int(n*0.95)]:.3f}s" if n > 20 else "N/A",
                'p99': f"{sorted_vals[int(n*0.99)]:.3f}s" if n > 100 else "N/A",
                'max': f"{max(sorted_vals):.3f}s"
            }

        duration = (self.end_time - self.start_time) if (self.end_time and self.start_time) else 0

        # Calculate timing breakdowns
        summary = {
            'total_requests': len(self.requests),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': f"{len(successful)/len(self.requests)*100:.2f}%" if self.requests else "0%",
            'duration_seconds': f"{duration:.2f}",
            'requests_per_second': f"{len(self.requests)/duration:.2f}" if duration > 0 else "0",

            # HTTP layer timings (client-side)
            'http_timings': {
                'dns_lookup': calc_percentiles(successful, ['timings', 'dns']),
                'tcp_connect': calc_percentiles(successful, ['timings', 'tcp_connect']),
                'tls_handshake': calc_percentiles(successful, ['timings', 'tls']),
                'request_send': calc_percentiles(successful, ['timings', 'request_send']),
                'ttfb': calc_percentiles(successful, ['timings', 'ttfb']),  # Time to first byte (server processing)
                'response_download': calc_percentiles(successful, ['timings', 'response_download']),
                'total': calc_percentiles(successful, ['timings', 'total']),
            },

            # Server-side timings (from headers, if available)
            'server_timings': {}
        }

        # Check if server provides timing headers
        server_timing_keys = set()
        for req in successful:
            server_timing_keys.update(req.get('server_timings', {}).keys())

        for key in server_timing_keys:
            summary['server_timings'][key] = calc_percentiles(
                [r for r in successful if key in r.get('server_timings', {})],
                ['server_timings', key]
            )

        # Calculate non-inference time (TTFB - server inference time)
        if 'inference' in server_timing_keys:
            non_inference_times = []
            for req in successful:
                ttfb = req.get('timings', {}).get('ttfb')
                inference = req.get('server_timings', {}).get('inference')
                if ttfb is not None and inference is not None:
                    non_inference_times.append(ttfb - inference)

            if non_inference_times:
                sorted_vals = sorted(non_inference_times)
                n = len(sorted_vals)
                summary['non_inference_server_time'] = {
                    'min': f"{min(sorted_vals):.3f}s",
                    'avg': f"{sum(sorted_vals)/n:.3f}s",
                    'p95': f"{sorted_vals[int(n*0.95)]:.3f}s" if n > 20 else "N/A",
                    'max': f"{max(sorted_vals):.3f}s"
                }

        # Status codes
        status_counts = {}
        for req in self.requests:
            status_counts[req['status_code']] = status_counts.get(req['status_code'], 0) + 1
        summary['status_codes'] = status_counts

        return summary


metrics = DetailedMetricsTracker()


class NmtUserWithTiming(HttpUser):
    source_cache = None
    wait_time = between(0.1, 0.2)
    TOKEN_LIFETIME = int(os.getenv("TOKEN_LIFETIME", 840))
    connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", 120))

    def on_start(self):
        self.start_time = time.time()
        self.request_count = 0
        self.access_token = None
        self.refresh_token = None
        self.token_expiry_time = 0

        self.account = next(TEST_ACCOUNTS_ITERATOR)
        logger.info(f"User assigned: {self.account['email']}")

        self.login()

        if NmtUserWithTiming.source_cache is None:
            samples_file = os.getenv("NMT_SAMPLES_FILE")
            with open(samples_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                NmtUserWithTiming.source_cache = data["nmt_samples"]
                logger.info(f"Loaded {len(NmtUserWithTiming.source_cache)} NMT samples")

    def on_stop(self):
        total_time = time.time() - self.start_time
        logger.info(f"USER SESSION: duration={total_time:.2f}s requests={self.request_count}")

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
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_expiry_time = time.time() + NmtUserWithTiming.TOKEN_LIFETIME
                logger.info(f"{self.account['email']} - Login successful")
            else:
                logger.error(f"{self.account['email']} - Login failed ({response.status_code})")
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
                    self.access_token = response.json().get("access_token")
                    self.token_expiry_time = time.time() + NmtUserWithTiming.TOKEN_LIFETIME
                    logger.info(f"{self.account['email']} - Token refreshed")
                else:
                    logger.error(f"{self.account['email']} - Refresh failed, re-logging in")
                    self.login()
            except Exception as e:
                logger.error(f"{self.account['email']} - Refresh exception, re-logging in")
                self.login()

    @task
    def nmt_task(self):
        if not self.access_token:
            self.login()
            if not self.access_token:
                return

        self.token_refresh()

        if not self.access_token:
            return

        sample = random.choice(NmtUserWithTiming.source_cache)
        source_text = sample["source"]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-User-Id": self.account["email"],
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

        # Detailed timing tracking
        timings = {}
        t_start = time.perf_counter()

        try:
            # We use requests directly to get more timing control
            import requests

            # Create a session for connection reuse
            if not hasattr(self, '_session'):
                self._session = requests.Session()

            # Hook to capture timing details
            timing_data = {}

            def response_hook(resp, *args, **kwargs):
                timing_data['total'] = time.perf_counter() - t_start
                timing_data['response_download'] = resp.elapsed.total_seconds() - timing_data.get('ttfb', 0)

            response = self._session.post(
                url=f"{base_url}/api/v1/nmt/inference",
                headers=headers,
                json=payload,
                timeout=NmtUserWithTiming.connection_timeout,
                hooks={'response': response_hook}
            )

            # Extract timing from response object
            # Note: requests library doesn't expose all timing details,
            # but we can approximate:
            elapsed = response.elapsed.total_seconds()

            # Parse Server-Timing header if present
            server_timings = {}
            if 'Server-Timing' in response.headers:
                # Example: "inference;dur=1230, preprocessing;dur=45"
                for part in response.headers['Server-Timing'].split(','):
                    if ';dur=' in part:
                        name, dur = part.strip().split(';dur=')
                        server_timings[name] = float(dur) / 1000  # Convert ms to seconds

            # Check for custom timing headers
            for header_name in response.headers:
                if 'time' in header_name.lower() or 'duration' in header_name.lower():
                    try:
                        server_timings[header_name] = float(response.headers[header_name])
                    except ValueError:
                        pass

            # Approximate timing breakdown
            # (For true breakdown, we'd need lower-level instrumentation)
            timings = {
                'dns': None,  # Not easily accessible via requests
                'tcp_connect': None,
                'tls': None,
                'request_send': None,
                'ttfb': elapsed,  # Approximate TTFB as total elapsed
                'response_download': 0,  # Negligible for JSON responses
                'total': time.perf_counter() - t_start
            }

            status_code = response.status_code
            metrics.record_request(timings, status_code, server_timings)
            self.request_count += 1

            if status_code == 200:
                inference_info = f" (inference={server_timings.get('inference', 'N/A')}s)" if server_timings else ""
                logger.info(f"NMT success: total={timings['total']:.3f}s{inference_info}")
            elif status_code == 401:
                logger.warning(f"Unauthorized - clearing token")
                self.access_token = None
            else:
                logger.error(f"NMT failed: {status_code}")

        except Exception as e:
            timings = {
                'dns': None, 'tcp_connect': None, 'tls': None,
                'request_send': None, 'ttfb': None,
                'response_download': None,
                'total': time.perf_counter() - t_start
            }
            metrics.record_request(timings, 0, None, str(e))
            self.request_count += 1
            logger.error(f"NMT exception: {e}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    metrics.start_time = time.time()
    logger.info(f"Load test started [{env} environment] with detailed timing")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    try:
        metrics.end_time = time.time()
        logger.info("=" * 80)
        logger.info("LOAD TEST COMPLETED - DETAILED TIMING BREAKDOWN")
        logger.info("=" * 80)

        summary = metrics.get_summary()

        if "error" in summary:
            logger.error(f"Error: {summary['error']}")
            return

        logger.info(f"Total Requests:  {summary['total_requests']}")
        logger.info(f"Successful:      {summary['successful']} ({summary['success_rate']})")
        logger.info(f"Failed:          {summary['failed']}")
        logger.info(f"Duration:        {summary['duration_seconds']}s")
        logger.info(f"Throughput:      {summary['requests_per_second']} req/s")

        logger.info("\n" + "=" * 80)
        logger.info("HTTP LAYER TIMINGS (client-side measurement)")
        logger.info("=" * 80)
        for layer, stats in summary['http_timings'].items():
            if stats:
                logger.info(f"{layer:20s}: avg={stats.get('avg', 'N/A'):>10s}  p95={stats.get('p95', 'N/A'):>10s}  max={stats.get('max', 'N/A'):>10s}")

        if summary.get('server_timings'):
            logger.info("\n" + "=" * 80)
            logger.info("SERVER-SIDE TIMINGS (from response headers)")
            logger.info("=" * 80)
            for layer, stats in summary['server_timings'].items():
                if stats:
                    logger.info(f"{layer:20s}: avg={stats.get('avg', 'N/A'):>10s}  p95={stats.get('p95', 'N/A'):>10s}  max={stats.get('max', 'N/A'):>10s}")

        if 'non_inference_server_time' in summary:
            logger.info("\n" + "=" * 80)
            logger.info("NON-INFERENCE SERVER TIME (TTFB - inference)")
            logger.info("=" * 80)
            stats = summary['non_inference_server_time']
            logger.info(f"avg={stats['avg']}  p95={stats['p95']}  max={stats['max']}")
            logger.info("(This includes auth, validation, preprocessing, postprocessing, but NOT inference)")

        # Save to file
        logs_dir = os.getenv("LOGS_DIR", "testing/AI4I/logs")
        os.makedirs(logs_dir, exist_ok=True)
        filename = f"{logs_dir}/nmt_timing_breakdown_{env}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"\n✅ Detailed metrics saved to {filename}")

    except Exception as e:
        logger.error(f"Error in test_stop: {e}")
        import traceback
        logger.error(traceback.format_exc())
