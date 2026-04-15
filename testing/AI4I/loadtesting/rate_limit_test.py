import os
from dotenv import load_dotenv
import requests
import time
from loguru import logger
from collections import defaultdict
import json

# Load env file based on ENV variable (default: staging)
env = os.getenv("ENV", "staging")
load_dotenv(f"testing/.{env}.env", override=True)

base_url = os.getenv("BASE_URL")
email = os.getenv("EMAIL", "admin@ai4inclusion.org")
password = os.getenv("PASSWORD", "ADMIN_PASSWORD")

# Configure logger
logger.add(
    f"testing/AI4I/logs/rate_limit_test_{env}_{int(time.time())}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)


class RateLimitTester:
    """Test rate limiting behavior for API endpoints"""

    def __init__(self, base_url, email, password):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.access_token = None
        self.session = requests.Session()

    def login(self):
        """Login and get access token"""
        logger.info(f"Logging in as {self.email}...")
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": self.email,
                "password": self.password,
                "remember_me": False
            }
        )

        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            logger.info("Login successful")
            return True
        else:
            logger.error(f"Login failed: {response.status_code} - {response.text[:200]}")
            return False

    def test_rate_limit(self, endpoint, payload, user_id, max_requests=150, delay=0.1):
        """
        Test rate limiting by sending multiple requests with same X-User-Id

        Args:
            endpoint: API endpoint to test (e.g., "/api/v1/nmt/inference")
            payload: Request payload
            user_id: Value for X-User-Id header
            max_requests: Number of requests to send
            delay: Delay between requests (seconds)

        Returns:
            dict: Results containing rate limit analysis
        """
        logger.info("=" * 80)
        logger.info(f"RATE LIMIT TEST - X-User-Id: {user_id}")
        logger.info(f"Endpoint: {endpoint}")
        logger.info(f"Max Requests: {max_requests}")
        logger.info("=" * 80)

        results = {
            "user_id": user_id,
            "endpoint": endpoint,
            "total_requests": 0,
            "status_codes": defaultdict(int),
            "first_429_at": None,
            "rate_limit_hit": False,
            "successful_before_limit": 0,
            "response_times": [],
            "start_time": time.time(),
            "requests": []
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-User-Id": user_id,
            "Connection": "keep-alive"
        }

        for i in range(1, max_requests + 1):
            request_start = time.time()

            try:
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                elapsed = time.time() - request_start
                status_code = response.status_code

                results["total_requests"] += 1
                results["status_codes"][status_code] += 1
                results["response_times"].append(elapsed)

                # Extract response body (safely)
                try:
                    response_body = response.json()
                except:
                    response_body = response.text[:200] if response.text else None

                # Extract interesting headers
                interesting_headers = {
                    "X-Request-Id": response.headers.get("X-Request-Id"),
                    "X-Server-Id": response.headers.get("X-Server-Id"),
                    "X-Cache": response.headers.get("X-Cache"),
                    "Via": response.headers.get("Via"),
                    "Server": response.headers.get("Server"),
                }

                # Store detailed request info
                request_info = {
                    "request_num": i,
                    "status_code": status_code,
                    "response_time": round(elapsed, 3),
                    "timestamp": time.time(),
                    "response_body": response_body,
                    "headers": {k: v for k, v in interesting_headers.items() if v}  # Only non-None
                }
                results["requests"].append(request_info)

                # Log headers for first few requests to spot patterns
                if i <= 5 or (i <= 20 and i % 2 == 0):
                    if interesting_headers.get("X-Request-Id") or interesting_headers.get("X-Server-Id"):
                        logger.debug(f"  Headers: {interesting_headers}")

                if status_code == 429:
                    if not results["rate_limit_hit"]:
                        results["first_429_at"] = i
                        results["rate_limit_hit"] = True
                        results["successful_before_limit"] = i - 1
                        logger.warning(f"⚠️  RATE LIMIT HIT at request #{i}")

                        # Check for rate limit headers
                        rate_limit_info = {
                            "X-RateLimit-Limit": response.headers.get("X-RateLimit-Limit"),
                            "X-RateLimit-Remaining": response.headers.get("X-RateLimit-Remaining"),
                            "X-RateLimit-Reset": response.headers.get("X-RateLimit-Reset"),
                            "Retry-After": response.headers.get("Retry-After"),
                        }
                        results["rate_limit_headers"] = rate_limit_info
                        logger.info(f"Rate limit headers: {rate_limit_info}")

                    logger.debug(f"Request #{i}: 429 Rate Limited ({elapsed:.3f}s)")
                    logger.debug(f"  Response: {str(response_body)[:150]}")
                elif status_code == 200:
                    # Detect fast vs slow pattern
                    speed_indicator = "🟢 FAST" if elapsed < 2.0 else "🔴 SLOW"
                    logger.debug(f"Request #{i}: 200 Success ({elapsed:.3f}s) {speed_indicator}")

                    # Log response body for 200s to see what's being returned
                    if isinstance(response_body, dict):
                        output_text = response_body.get("output", [{}])[0].get("target", "")
                        logger.debug(f"  Translation: {output_text[:100]}")

                        # Log additional response metadata
                        if "metadata" in response_body:
                            logger.debug(f"  Metadata: {response_body['metadata']}")
                    else:
                        logger.debug(f"  Response: {str(response_body)[:150]}")
                else:
                    logger.warning(f"Request #{i}: {status_code} ({elapsed:.3f}s)")
                    logger.warning(f"  Response: {str(response_body)[:150]}")

                # Log every 10 requests
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{max_requests} requests sent")

            except Exception as e:
                logger.error(f"Request #{i} failed: {e}")
                results["status_codes"]["error"] += 1

            time.sleep(delay)

        results["end_time"] = time.time()
        results["total_duration"] = results["end_time"] - results["start_time"]

        return results

    def print_summary(self, results):
        """Print test summary"""
        logger.info("=" * 80)
        logger.info("RATE LIMIT TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"User ID: {results['user_id']}")
        logger.info(f"Total Requests: {results['total_requests']}")
        logger.info(f"Duration: {results['total_duration']:.2f}s")
        logger.info(f"")
        logger.info(f"Status Code Distribution:")
        for code, count in sorted(results['status_codes'].items()):
            logger.info(f"  {code}: {count} requests")
        logger.info(f"")

        # Analyze response time patterns
        if results['response_times']:
            response_times = results['response_times']
            fast_requests = [t for t in response_times if t < 2.0]
            slow_requests = [t for t in response_times if t >= 2.0]

            logger.info(f"Response Time Analysis:")
            logger.info(f"  Fast requests (<2s): {len(fast_requests)} (avg: {sum(fast_requests)/len(fast_requests):.3f}s)")
            logger.info(f"  Slow requests (≥2s): {len(slow_requests)} (avg: {sum(slow_requests)/len(slow_requests):.3f}s)" if slow_requests else "  Slow requests (≥2s): 0")

            # Detect alternating pattern
            if len(response_times) > 5:
                alternating = True
                for i in range(min(10, len(response_times) - 1)):
                    current_fast = response_times[i] < 2.0
                    next_fast = response_times[i + 1] < 2.0
                    if current_fast == next_fast:
                        alternating = False
                        break

                if alternating:
                    logger.warning(f"  ⚠️  PATTERN DETECTED: Alternating fast/slow response times!")
                    logger.warning(f"     This suggests load balancing, caching, or routing issues")
        logger.info(f"")

        if results['rate_limit_hit']:
            logger.info(f"✅ Rate Limit Detected:")
            logger.info(f"  First 429 at request: #{results['first_429_at']}")
            logger.info(f"  Successful before limit: {results['successful_before_limit']}")

            if "rate_limit_headers" in results:
                logger.info(f"  Rate Limit Headers:")
                for key, value in results["rate_limit_headers"].items():
                    if value:
                        logger.info(f"    {key}: {value}")
        else:
            logger.info(f"❌ No Rate Limit Hit (sent {results['total_requests']} requests)")

        logger.info("=" * 80)

    def save_results(self, results, filename=None):
        """Save results to JSON file"""
        if filename is None:
            filename = f"testing/AI4I/logs/rate_limit_results_{env}_{int(time.time())}.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Convert defaultdict to dict for JSON serialization
        results["status_codes"] = dict(results["status_codes"])

        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {filename}")
        return filename


def test_nmt_rate_limit():
    """Test NMT endpoint rate limiting"""
    tester = RateLimitTester(base_url, email, password)

    if not tester.login():
        logger.error("Login failed, exiting")
        return

    # NMT test payload
    payload = {
        "input": [{"source": "यह एक परीक्षण वाक्य है"}],
        "config": {
            "serviceId": os.getenv("NMT_SERVICE_ID"),
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "en"
            }
        },
        "controlConfig": {"additionalProp1": {"dataTracking": False}}
    }

    # Test with a specific user ID
    user_id = "test_user_rate_limit_1"

    results = tester.test_rate_limit(
        endpoint="/api/v1/nmt/inference",
        payload=payload,
        user_id=user_id,
        max_requests=150,  # Send 150 requests to test rate limit
        delay=0.1  # 100ms between requests
    )

    tester.print_summary(results)
    tester.save_results(results)


def test_multiple_users():
    """Test rate limiting with multiple different X-User-Id values"""
    tester = RateLimitTester(base_url, email, password)

    if not tester.login():
        logger.error("Login failed, exiting")
        return

    payload = {
        "input": [{"source": "यह एक परीक्षण वाक्य है"}],
        "config": {
            "serviceId": os.getenv("NMT_SERVICE_ID"),
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "en"
            }
        },
        "controlConfig": {"additionalProp1": {"dataTracking": False}}
    }

    # Test with 3 different user IDs to confirm rate limiting is per user
    user_ids = ["rate_test_user_1", "rate_test_user_2", "rate_test_user_3"]
    all_results = []

    for user_id in user_ids:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing with {user_id}")
        logger.info(f"{'='*80}\n")

        results = tester.test_rate_limit(
            endpoint="/api/v1/nmt/inference",
            payload=payload,
            user_id=user_id,
            max_requests=50,  # Send 50 requests per user
            delay=0.1
        )

        tester.print_summary(results)
        all_results.append(results)

        # Small delay between different users
        time.sleep(2)

    # Save combined results
    combined_filename = f"testing/AI4I/logs/rate_limit_multi_user_{env}_{int(time.time())}.json"
    with open(combined_filename, "w") as f:
        json.dump(all_results, f, indent=2)

    logger.info(f"\n✅ Combined results saved to {combined_filename}")


if __name__ == "__main__":
    import sys

    logger.info(f"Rate Limit Tester - Environment: {env}")
    logger.info(f"Base URL: {base_url}")

    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        # Test with multiple users
        test_multiple_users()
    else:
        # Test with single user
        test_nmt_rate_limit()
