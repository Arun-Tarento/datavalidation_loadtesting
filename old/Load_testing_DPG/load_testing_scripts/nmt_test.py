"""
NMT Load Testing Script with Locust Integration for DPG
Tests the latency of NMT service at http://13.204.164.186/

Usage:
    # Web UI mode (default)
    locust -f load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186

    # Headless mode
    locust -f load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186 --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f load_testing_scripts/nmt_load_test.py --host=http://your-custom-host
"""

import os
import json
import random
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Global tracking variables
first_failure_time: Optional[float] = None
throughput_samples = []  # List of (timestamp, rps) tuples
payload_sizes = []  # List of payload sizes in bytes
input_char_counts = []  # List of input text character counts
error_tracking = {}  # Dictionary to track errors by type/status code
retry_count = 0  # Total number of automatic retries
retry_failures = 0  # Number of retry attempts that also failed


class RetryTrackingAdapter(HTTPAdapter):
    """Custom HTTP Adapter that tracks retry attempts"""

    def __init__(self, *args, **kwargs):
        # Custom Retry class that tracks attempts
        class TrackedRetry(Retry):
            def increment(self, method=None, url=None, response=None, error=None, _pool=None, _stacktrace=None):
                """Override increment to count retries"""
                global retry_count, retry_failures
                # Only count if we're actually going to retry (not on the first attempt)
                if self.total is not None and self.total > 0:
                    retry_count += 1
                    # Track if this retry was also a failure
                    if response is not None and response.status >= 400:
                        retry_failures += 1
                    elif error is not None:
                        retry_failures += 1
                return super().increment(method, url, response, error, _pool, _stacktrace)

        # Configure retry strategy with tracking
        retry_strategy = TrackedRetry(
            total=3,  # Maximum 3 retries
            backoff_factor=0.3,  # Wait 0.3s, 0.6s, 1.2s between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            raise_on_status=False  # Don't raise immediately, allow retries
        )
        super().__init__(max_retries=retry_strategy, *args, **kwargs)


class NMTConfig:
    """Configuration handler for NMT load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        print("NMTConfig.__init__() starting...")

        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

        # NMT Service Configuration
        self.service_id = os.getenv("NMT_SERVICE_ID", "ai4bharat/indictrans--gpu-t4")
        self.source_language = os.getenv("NMT_SOURCE_LANGUAGE", "hi")
        self.source_script = os.getenv("NMT_SOURCE_SCRIPT", "Deva")
        self.target_language = os.getenv("NMT_TARGET_LANGUAGE", "ta")
        self.target_script = os.getenv("NMT_TARGET_SCRIPT", "Taml")
        self.control_config = self._parse_control_config()

        # Load NMT samples
        print("About to call _load_nmt_samples()...")
        self.nmt_samples = self._load_nmt_samples()
        print(f"_load_nmt_samples() returned: {len(self.nmt_samples)} samples")

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("NMT_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in NMT_CONTROL_CONFIG, using default")
            return {"dataTracking": True}

    def _load_nmt_samples(self) -> List[Dict[str, str]]:
        """Load NMT samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("NMT_SAMPLES_FILE", "load_testing_test_samples/nmt/nmt_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels to the project root
            parent_dir = os.path.dirname(script_dir)
            project_root = os.path.dirname(parent_dir)
            file_path = os.path.join(project_root, file_path)

        print(f"\n=== LOADING NMT SAMPLES ===")
        print(f"Path: {file_path}")
        print(f"Exists: {os.path.exists(file_path)}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("nmt_samples", [])
                print(f"Loaded: {len(samples)} samples")
                print(f"=== DONE ===\n")
                return samples
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"=== FAILED ===\n")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("NMT_SERVICE_ID is required in .env file")
        if not self.source_language:
            raise ValueError("NMT_SOURCE_LANGUAGE is required in .env file")
        if not self.target_language:
            raise ValueError("NMT_TARGET_LANGUAGE is required in .env file")
        if not self.nmt_samples:
            raise ValueError("No NMT samples found. Please check nmt_samples.json")

    def build_payload(self, source_text: str) -> Dict[str, Any]:
        """Build the API payload for DPG endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "serviceId": self.service_id,
                "language": {
                    "sourceLanguage": self.source_language,
                    "sourceScriptCode": self.source_script,
                    "targetLanguage": self.target_language,
                    "targetScriptCode": self.target_script
                }
            },
            "input": [
                {
                    "source": source_text
                }
            ]
        }

    def get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "accept": "application/json",
            "x-auth-source": self.x_auth_source,
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }

    def get_random_nmt_sample(self) -> str:
        """Get a random NMT sample from the loaded samples"""
        sample = random.choice(self.nmt_samples)
        return sample.get("source", "")


class NMTUser(HttpUser):
    """Locust User class for NMT load testing"""

    # Wait time between tasks (in seconds)
    # Can be configured via environment variable
    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        try:
            # Reload .env to get fresh config
            load_dotenv(override=True)
            self.config = NMTConfig()  # Create fresh config for each user

            # Install retry tracking adapter
            adapter = RetryTrackingAdapter()
            self.client.mount("http://", adapter)
            self.client.mount("https://", adapter)

            print(f"Starting NMT User - Service: {self.config.service_id}, "
                  f"Language: {self.config.source_language} ({self.config.source_script}) -> "
                  f"{self.config.target_language} ({self.config.target_script})")
        except Exception as e:
            print(f"ERROR in NMT User on_start: {e}")
            import traceback
            traceback.print_exc()
            raise

    @task
    def nmt_request(self):
        """
        Task to send NMT request
        This is the main load testing task that will be executed repeatedly
        """
        # Get random NMT sample
        source_text = self.config.get_random_nmt_sample()

        # Build payload
        payload = self.config.build_payload(source_text)

        # Track payload size
        global payload_sizes, input_char_counts
        payload_size = len(json.dumps(payload).encode('utf-8'))
        payload_sizes.append(payload_size)

        # Track input character count
        input_char_counts.append(len(source_text))

        # Get headers
        headers = self.config.get_headers()

        # Query parameters
        params = {"serviceId": self.config.service_id}

        # Send request with Locust's built-in metrics tracking
        try:
            with self.client.post(
            "/services/inference/translation",
            params=params,
            json=payload,
            headers=headers,
            catch_response=True,
            name="NMT Translation Request",
            timeout=60  # Increased timeout for translation under load
        ) as response:

                if response.status_code != 200:
                    # HTTP 0 typically means timeout or connection issue
                    if response.status_code == 0:
                        error_key = "TIMEOUT_OR_CONNECTION_FAILURE"
                    else:
                        error_key = f"HTTP_{response.status_code}"
                    self._track_failure(error_key)
                    response.failure(f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No response text'}")
                    return

                # JSON parse
                try:
                    data = response.json()
                except ValueError as e:
                    self._track_failure("JSON_PARSE_ERROR")
                    response.failure("Response not valid JSON")
                    return

                # Validate 'output' exists and is a non-empty list
                output = data.get("output")
                if not isinstance(output, list) or len(output) == 0:
                    self._track_failure("MISSING_OUTPUT_ARRAY")
                    response.failure("Missing or empty 'output' array in response")
                    return

                # Validate first output element is a dict with a non-empty translated text field
                first = output[0]
                if not isinstance(first, dict):
                    self._track_failure("INVALID_OUTPUT_FORMAT")
                    response.failure("Invalid output[0] format; expected object")
                    return

                # Common keys to look for in NMT responses (be permissive)
                translated_text = (
                    first.get("target")
                    or first.get("translation")
                    or first.get("translatedText")
                    or first.get("text")
                    or first.get("output")
                )

                if not isinstance(translated_text, str) or not translated_text.strip():
                    self._track_failure("EMPTY_TRANSLATION")
                    response.failure("Empty or missing translated text in output[0]")
                    return

            # Optional: basic sanity checks (length ratio, identical source->target detection)
            try:
                src = payload.get("input", [{}])[0].get("source", "")
                if isinstance(src, str) and src.strip():
                    # if translation equals source exactly, mark as warning/failure (adjust as needed)
                    if str(translated_text).strip() == str(src).strip():
                        self._track_failure("IDENTICAL_SOURCE_TARGET")
                        response.failure("Translated text identical to source (possible failure)")
                        return
                    # optional: extremely short translations may indicate an error
                    if len(str(translated_text).split()) < 1:
                        self._track_failure("TRANSLATION_TOO_SHORT")
                        response.failure("Translated text too short")
                        return
            except Exception:
                # don't crash  treat as non-fatal unless you want to enforce stricter checks
                pass

                # All checks passed -> success
                response.success()

        except Exception as e:
            # Catch connection errors, timeouts, etc.
            import requests.exceptions
            error_type = type(e).__name__

            # Distinguish between different exception types and mark as failure in Locust
            if isinstance(e, requests.exceptions.Timeout):
                self._track_failure("CLIENT_TIMEOUT")
                # Fire a request_failure event so Locust counts it
                self.environment.events.request.fire(
                    request_type="POST",
                    name="NMT Translation Request",
                    response_time=None,
                    response_length=0,
                    exception=e,
                )
            elif isinstance(e, requests.exceptions.ConnectionError):
                self._track_failure("CLIENT_CONNECTION_ERROR")
                self.environment.events.request.fire(
                    request_type="POST",
                    name="NMT Translation Request",
                    response_time=None,
                    response_length=0,
                    exception=e,
                )
            else:
                self._track_failure(f"CLIENT_EXCEPTION_{error_type}")
                self.environment.events.request.fire(
                    request_type="POST",
                    name="NMT Translation Request",
                    response_time=None,
                    response_length=0,
                    exception=e,
                )
            # Don't re-raise - we've already tracked it
            # This prevents Locust from retrying and allows the test to continue

    def _track_failure(self, error_type: str):
        """Track failures by error type/status code"""
        global first_failure_time, error_tracking

        # Track first failure timestamp
        if first_failure_time is None:
            first_failure_time = time.time()

        # Track error by type
        if error_type not in error_tracking:
            error_tracking[error_type] = 0
        error_tracking[error_type] += 1


# Locust event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    global first_failure_time, throughput_samples, payload_sizes, input_char_counts, error_tracking, retry_count, retry_failures
    # Reset global tracking variables
    first_failure_time = None
    throughput_samples = []
    payload_sizes = []
    input_char_counts = []
    error_tracking = {}
    retry_count = 0
    retry_failures = 0

    # Create config instance for display
    load_dotenv(override=True)
    test_config = NMTConfig()
    print("\n" + "="*70)
    print("NMT LOAD TEST STARTED - DPG")
    print("="*70)
    print(f"Service ID: {test_config.service_id}")
    print(f"Source Language: {test_config.source_language} ({test_config.source_script})")
    print(f"Target Language: {test_config.target_language} ({test_config.target_script})")
    print(f"NMT Samples Loaded: {len(test_config.nmt_samples)}")
    print("="*70 + "\n")

    # Start periodic throughput tracking
    def track_throughput(environment):
        """Periodically sample throughput"""
        import threading
        stop_event = threading.Event()

        def sample_loop():
            try:
                while not stop_event.is_set() and environment.runner.state not in ["stopped", "stopping"]:
                    try:
                        stats = environment.stats.total
                        current_time = time.time()
                        current_rps = stats.current_rps if hasattr(stats, 'current_rps') else stats.total_rps
                        throughput_samples.append((current_time, current_rps))
                    except Exception as e:
                        # Silently continue if stats access fails
                        pass
                    # Use shorter sleep intervals for more responsive shutdown
                    for _ in range(4):  # 4 x 0.5s = 2 seconds total
                        if stop_event.is_set() or environment.runner.state in ["stopped", "stopping"]:
                            break
                        time.sleep(0.5)
            except Exception:
                pass  # Thread exits silently on any error

        # Store stop event for cleanup
        environment._throughput_stop_event = stop_event
        thread = threading.Thread(target=sample_loop, daemon=True)
        thread.start()
        return thread

    track_throughput(environment)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    global error_tracking, retry_count, retry_failures

    # Signal throughput thread to stop
    if hasattr(environment, '_throughput_stop_event'):
        environment._throughput_stop_event.set()

    print("\n" + "="*70)
    print("NMT LOAD TEST COMPLETED - DPG")
    print("="*70)

    # Get statistics
    stats = environment.stats

    # Print summary
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Automatic Retries: {retry_count}")
    print(f"  └─ Retry attempts that also failed: {retry_failures}")
    print(f"Actual Server Requests: {stats.total.num_requests + retry_count}")

    if stats.total.num_requests > 0:
        print(f"Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.2f}%")

        # Print error breakdown if there are failures
        if (stats.total.num_failures > 0 or error_tracking) and error_tracking:
            # Categorize errors
            client_errors = {}
            server_errors = {}
            for error_type, count in error_tracking.items():
                if error_type.startswith("CLIENT_") or error_type in ["REQUEST_TIMEOUT", "CONNECTION_ERROR", "TIMEOUT_OR_CONNECTION_FAILURE"]:
                    client_errors[error_type] = count
                else:
                    server_errors[error_type] = count

            total_client = sum(client_errors.values())
            total_server = sum(server_errors.values())

            print(f"\nError Breakdown:")
            print(f"  Total Errors: {total_client + total_server}")
            print(f"  ├─ Client-Side Errors: {total_client} ({(total_client/stats.total.num_requests*100):.2f}% of total requests)")
            print(f"  └─ Server-Side Errors: {total_server} ({(total_server/stats.total.num_requests*100):.2f}% of total requests)")

            if client_errors:
                print(f"\n  Client-Side Errors (timeouts, connection issues):")
                print(f"    {'Error Type':<28} {'Count':>8} {'% of Total':>12}")
                print(f"    {'-'*28} {'-'*8} {'-'*12}")
                for error_type, count in sorted(client_errors.items(), key=lambda x: x[1], reverse=True):
                    pct_total = (count / stats.total.num_requests) * 100
                    print(f"    {error_type:<28} {count:>8} {pct_total:>11.2f}%")

            if server_errors:
                print(f"\n  Server-Side Errors (HTTP errors, validation failures):")
                print(f"    {'Error Type':<28} {'Count':>8} {'% of Total':>12}")
                print(f"    {'-'*28} {'-'*8} {'-'*12}")
                for error_type, count in sorted(server_errors.items(), key=lambda x: x[1], reverse=True):
                    pct_total = (count / stats.total.num_requests) * 100
                    print(f"    {error_type:<28} {count:>8} {pct_total:>11.2f}%")

    print(f"\nResponse Time Statistics (milliseconds):")
    print(f"  Min:     {stats.total.min_response_time:.2f}")
    print(f"  Max:     {stats.total.max_response_time:.2f}")
    print(f"  Median:  {stats.total.median_response_time:.2f}")
    print(f"  Average: {stats.total.avg_response_time:.2f}")
    print(f"  P95:     {stats.total.get_response_time_percentile(0.95):.2f}")
    print(f"  P99:     {stats.total.get_response_time_percentile(0.99):.2f}")

    print(f"\nRequests per second: {stats.total.total_rps:.2f}")
    print(f"Average Content Size: {stats.total.avg_content_length:.2f} bytes")

    print("="*70 + "\n")

    # Save detailed results to JSON (only on master in distributed mode)
    if not isinstance(environment.runner, WorkerRunner):
        save_results_to_json(environment)


def save_results_to_json(environment):
    """Save test results to JSON file"""
    global first_failure_time, throughput_samples, payload_sizes, input_char_counts, error_tracking, retry_count, retry_failures
    stats = environment.stats

    # Create config instance for saving results
    load_dotenv(override=True)
    save_config = NMTConfig()

    # Calculate error rate
    error_rate = (stats.total.num_failures / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0

    # Calculate average payload size
    avg_payload_size = sum(payload_sizes) / len(payload_sizes) if payload_sizes else 0

    # Calculate input character count statistics
    if input_char_counts:
        avg_input_chars = sum(input_char_counts) / len(input_char_counts)
        sorted_chars = sorted(input_char_counts)
        median_input_chars = sorted_chars[len(sorted_chars) // 2] if sorted_chars else 0
    else:
        avg_input_chars = 0
        median_input_chars = 0

    # Calculate retry statistics
    actual_server_requests = stats.total.num_requests + retry_count
    retry_rate = (retry_count / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0
    retry_failure_rate = (retry_failures / retry_count * 100) if retry_count > 0 else 0

    # Calculate error breakdown with percentages - distinguish client vs server errors
    error_breakdown = {}
    server_errors = {}
    client_errors = {}
    total_failures = stats.total.num_failures

    if total_failures > 0 or error_tracking:
        for error_type, count in error_tracking.items():
            error_detail = {
                "count": count,
                "percentage_of_failures": round((count / total_failures) * 100, 2) if total_failures > 0 else 0,
                "percentage_of_total_requests": round((count / stats.total.num_requests) * 100, 2) if stats.total.num_requests > 0 else 0
            }
            error_breakdown[error_type] = error_detail

            # Categorize as client or server error
            if error_type.startswith("CLIENT_") or error_type in ["REQUEST_TIMEOUT", "CONNECTION_ERROR", "TIMEOUT_OR_CONNECTION_FAILURE"]:
                client_errors[error_type] = error_detail
            elif error_type.startswith("HTTP_"):
                server_errors[error_type] = error_detail
            else:
                # JSON/validation errors could be either, but let's categorize as server for now
                server_errors[error_type] = error_detail

    # Calculate totals
    total_client_errors = sum(e["count"] for e in client_errors.values())
    total_server_errors = sum(e["count"] for e in server_errors.values())

    # Calculate throughput statistics
    throughput_stats = {}
    if throughput_samples:
        throughput_values = [rps for _, rps in throughput_samples]
        max_rps = max(throughput_values)
        min_rps = min(throughput_values)
        avg_rps = sum(throughput_values) / len(throughput_values)

        # Find when max and min occurred
        max_idx = throughput_values.index(max_rps)
        min_idx = throughput_values.index(min_rps)
        max_time, _ = throughput_samples[max_idx]
        min_time, _ = throughput_samples[min_idx]

        # Get test start time (first sample)
        start_time = throughput_samples[0][0] if throughput_samples else time.time()

        throughput_stats = {
            "average_rps": avg_rps,
            "max_rps": max_rps,
            "max_rps_at_seconds": max_time - start_time,
            "max_rps_timestamp": datetime.fromtimestamp(max_time).isoformat(),
            "min_rps": min_rps,
            "min_rps_at_seconds": min_time - start_time,
            "min_rps_timestamp": datetime.fromtimestamp(min_time).isoformat(),
        }

    # First failure information
    first_failure_info = None
    if first_failure_time:
        # Get test start time from stats
        test_start = environment.stats.start_time
        time_to_first_failure = first_failure_time - test_start
        first_failure_info = {
            "occurred": True,
            "timestamp": datetime.fromtimestamp(first_failure_time).isoformat(),
            "seconds_after_start": time_to_first_failure
        }
    else:
        first_failure_info = {
            "occurred": False,
            "timestamp": None,
            "seconds_after_start": None
        }

    output = {
        "test_config": {
            "service_id": save_config.service_id,
            "source_language": save_config.source_language,
            "source_script": save_config.source_script,
            "target_language": save_config.target_language,
            "target_script": save_config.target_script
        },
        "statistics": {
            "total_requests": stats.total.num_requests,
            "failed_requests": stats.total.num_failures,
            "success_rate": ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0,
            "error_rate_percentage": round(error_rate, 2),
            "error_breakdown": error_breakdown,
            "error_categorization": {
                "client_side_errors": {
                    "total_count": total_client_errors,
                    "percentage_of_total_requests": round((total_client_errors / stats.total.num_requests * 100), 2) if stats.total.num_requests > 0 else 0,
                    "details": client_errors
                },
                "server_side_errors": {
                    "total_count": total_server_errors,
                    "percentage_of_total_requests": round((total_server_errors / stats.total.num_requests * 100), 2) if stats.total.num_requests > 0 else 0,
                    "details": server_errors
                },
                "explanation": {
                    "client_side": "Timeouts, connection errors - requests that never reached the server or didn't get a response",
                    "server_side": "HTTP errors (4xx, 5xx), JSON parse errors - server responded but with an error"
                }
            },
            "retry_statistics": {
                "automatic_retries": retry_count,
                "retry_failures": retry_failures,
                "retry_failure_rate_percentage": round(retry_failure_rate, 2),
                "actual_server_requests": actual_server_requests,
                "retry_rate_percentage": round(retry_rate, 2),
                "retry_multiplier": round(actual_server_requests / stats.total.num_requests, 2) if stats.total.num_requests > 0 else 1.0
            },
            "first_failure": first_failure_info,
            "average_payload_size_bytes": round(avg_payload_size, 2),
            "input_text_statistics": {
                "average_characters": round(avg_input_chars, 2),
                "median_characters": median_input_chars
            },
            "response_time_ms": {
                "min": stats.total.min_response_time,
                "max": stats.total.max_response_time,
                "median": stats.total.median_response_time,
                "average": stats.total.avg_response_time,
                "p95": stats.total.get_response_time_percentile(0.95),
                "p99": stats.total.get_response_time_percentile(0.99)
            },
            "requests_per_second": stats.total.total_rps,
            "average_content_size_bytes": stats.total.avg_content_length,
            "throughput": throughput_stats if throughput_stats else {
                "average_rps": stats.total.total_rps,
                "max_rps": None,
                "max_rps_at_seconds": None,
                "max_rps_timestamp": None,
                "min_rps": None,
                "min_rps_at_seconds": None,
                "min_rps_timestamp": None
            }
        },
        "detailed_stats": {}
    }

    # Add per-endpoint statistics
    for name, stat in stats.entries.items():
        # Convert tuple keys to strings for JSON serialization
        name_str = name[1] if isinstance(name, tuple) and len(name) > 1 else str(name)
        if name_str != "Aggregated":
            output["detailed_stats"][name_str] = {
                "num_requests": stat.num_requests,
                "num_failures": stat.num_failures,
                "min_response_time": stat.min_response_time,
                "max_response_time": stat.max_response_time,
                "median_response_time": stat.median_response_time,
                "avg_response_time": stat.avg_response_time
            }

    # Save to file in Load_testing_DPG/load_testing_results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    results_dir = os.path.join(parent_dir, "load_testing_results")
    os.makedirs(results_dir, exist_ok=True)

    filename = os.path.join(results_dir, "nmt_load_test_results.json")
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to {filename}")


if __name__ == "__main__":
    """
    This allows running the script directly, but Locust should be run via CLI:
    locust -f load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186
    """
    import sys
    print("\n" + "="*70)
    print("NMT Load Testing with Locust - DPG")
    print("="*70)
    print("\nTo run this test, use the Locust CLI:")
    print("\n1. Web UI mode (recommended):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f Load_testing_DPG/load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186 \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186 --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/nmt_load_test.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
