"""
Transliteration Load Testing Script with Locust Integration for DPG
Tests the latency of Transliteration service at http://13.204.164.186:8000/

Usage:
    # Web UI mode (default)
    locust -f load_testing_scripts/transliteration_test.py --host=http://13.204.164.186:8000

    # Headless mode
    locust -f load_testing_scripts/transliteration_test.py --host=http://13.204.164.186:8000 --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f load_testing_scripts/transliteration_test.py --host=http://your-custom-host
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


class TransliterationConfig:
    """Configuration handler for Transliteration load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        print("TransliterationConfig.__init__() starting...")

        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

        # Transliteration Service Configuration
        self.service_id = os.getenv("TRANSLITERATION_SERVICE_ID", "ai4bharat-transliteration")
        self.source_language = os.getenv("TRANSLITERATION_SOURCE_LANGUAGE", "en")
        self.source_script = os.getenv("TRANSLITERATION_SOURCE_SCRIPT", "Latn")
        self.target_language = os.getenv("TRANSLITERATION_TARGET_LANGUAGE", "hi")
        self.target_script = os.getenv("TRANSLITERATION_TARGET_SCRIPT", "Deva")
        self.is_sentence = os.getenv("TRANSLITERATION_IS_SENTENCE", "true").lower() == "true"
        self.num_suggestions = int(os.getenv("TRANSLITERATION_NUM_SUGGESTIONS", "0"))
        self.control_config = self._parse_control_config()

        # Load Transliteration samples
        print("About to call _load_transliteration_samples()...")
        self.transliteration_samples = self._load_transliteration_samples()
        print(f"_load_transliteration_samples() returned: {len(self.transliteration_samples)} samples")

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("TRANSLITERATION_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in TRANSLITERATION_CONTROL_CONFIG, using default")
            return {"dataTracking": True}

    def _load_transliteration_samples(self) -> List[Dict[str, str]]:
        """Load Transliteration samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("TRANSLITERATION_SAMPLES_FILE", "load_testing_test_samples/transliteration/transliteration_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels to the project root
            parent_dir = os.path.dirname(script_dir)
            project_root = os.path.dirname(parent_dir)
            file_path = os.path.join(project_root, file_path)

        print(f"\n=== LOADING TRANSLITERATION SAMPLES ===")
        print(f"Path: {file_path}")
        print(f"Exists: {os.path.exists(file_path)}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("transliteration_samples", [])
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
            raise ValueError("TRANSLITERATION_SERVICE_ID is required in .env file")
        if not self.source_language:
            raise ValueError("TRANSLITERATION_SOURCE_LANGUAGE is required in .env file")
        if not self.target_language:
            raise ValueError("TRANSLITERATION_TARGET_LANGUAGE is required in .env file")
        if not self.transliteration_samples:
            raise ValueError("No Transliteration samples found. Please check transliteration_samples.json")

    def build_payload(self, source_text: str) -> Dict[str, Any]:
        """Build the API payload for DPG Transliteration endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "serviceId": self.service_id,
                "language": {
                    "sourceLanguage": self.source_language,
                    "sourceScriptCode": self.source_script,
                    "targetLanguage": self.target_language,
                    "targetScriptCode": self.target_script
                },
                "isSentence": self.is_sentence,
                "numSuggestions": self.num_suggestions
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

    def get_random_transliteration_sample(self) -> str:
        """Get a random Transliteration sample from the loaded samples"""
        sample = random.choice(self.transliteration_samples)
        return sample.get("source", "")


class TransliterationUser(HttpUser):
    """Locust User class for Transliteration load testing"""

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
            self.config = TransliterationConfig()  # Create fresh config for each user
            # Install retry tracking adapter
            adapter = RetryTrackingAdapter()
            self.client.mount("http://", adapter)
            self.client.mount("https://", adapter)
            print(f"Starting Transliteration User - Service: {self.config.service_id}, "
                  f"Language: {self.config.source_language} ({self.config.source_script}) -> "
                  f"{self.config.target_language} ({self.config.target_script})")
        except Exception as e:
            print(f"ERROR in Transliteration User on_start: {e}")
            import traceback
            traceback.print_exc()
            raise

    @task
    def transliteration_request(self):
        """
        Task to send Transliteration request
        This is the main load testing task that will be executed repeatedly
        """
        # Get random Transliteration sample
        source_text = self.config.get_random_transliteration_sample()

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
        with self.client.post(
            "/services/inference/transliteration",
            params=params,
            json=payload,
            headers=headers,
            catch_response=True,
            name="Transliteration Request",
            timeout=250  # Increased timeout for transliteration under load
        ) as response:

            if response.status_code != 200:
                self._track_failure()
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
                return

            # JSON parse
            try:
                data = response.json()
            except ValueError:
                self._track_failure()
                response.failure("Response not valid JSON")
                return

            # Validate 'output' exists and is a non-empty list
            output = data.get("output")
            if not isinstance(output, list) or len(output) == 0:
                self._track_failure()
                response.failure("Missing or empty 'output' array in response")
                return

            # Validate first output element is a dict with non-empty transliterated text field
            first = output[0]
            if not isinstance(first, dict):
                self._track_failure()
                response.failure("Invalid output[0] format; expected object")
                return

            # Get the transliterated text (target field contains array of transliterations)
            transliterated_array = first.get("target", [])

            # Validate target is a list with at least one element
            if not isinstance(transliterated_array, list) or len(transliterated_array) == 0:
                self._track_failure()
                response.failure("Empty or missing 'target' array in output[0]")
                return

            # Get the first transliteration from the array
            transliterated_text = transliterated_array[0] if len(transliterated_array) > 0 else ""

            # Validate the transliterated text is a non-empty string
            if not isinstance(transliterated_text, str) or not transliterated_text.strip():
                self._track_failure()
                response.failure("Empty or invalid transliterated text in target[0]")
                return

            # Optional: basic sanity checks
            try:
                src = payload.get("input", [{}])[0].get("source", "")
                if isinstance(src, str) and src.strip():
                    # Check if transliteration has reasonable length
                    if len(str(transliterated_text).strip()) < 1:
                        self._track_failure()
                        response.failure("Transliterated text too short")
                        return
            except Exception:
                # Don't crash - treat as non-fatal unless you want to enforce stricter checks
                pass

            # All checks passed -> success
            response.success()

    def _track_failure(self):
        """Track the first failure timestamp"""
        global first_failure_time
        if first_failure_time is None:
            first_failure_time = time.time()


# Locust event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    global first_failure_time, throughput_samples, payload_sizes, input_char_counts, retry_count
    # Reset global tracking variables
    first_failure_time = None
    throughput_samples = []
    payload_sizes = []
    input_char_counts = []
    retry_count = 0
    retry_failures = 0

    # Create config instance for display
    load_dotenv(override=True)
    test_config = TransliterationConfig()
    print("\n" + "="*70)
    print("TRANSLITERATION LOAD TEST STARTED - DPG")
    print("="*70)
    print(f"Service ID: {test_config.service_id}")
    print(f"Source Language: {test_config.source_language} ({test_config.source_script})")
    print(f"Target Language: {test_config.target_language} ({test_config.target_script})")
    print(f"Is Sentence: {test_config.is_sentence}")
    print(f"Num Suggestions: {test_config.num_suggestions}")
    print(f"Transliteration Samples Loaded: {len(test_config.transliteration_samples)}")
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
    global retry_count, retry_failures
    global retry_count
    # Signal throughput thread to stop
    if hasattr(environment, '_throughput_stop_event'):
        environment._throughput_stop_event.set()

    print("\n" + "="*70)
    print("TRANSLITERATION LOAD TEST COMPLETED - DPG")
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

        print(f"\nResponse Time Statistics (milliseconds):")
        print(f"  Min:     {stats.total.min_response_time:.2f}")
        print(f"  Max:     {stats.total.max_response_time:.2f}")
        print(f"  Median:  {stats.total.median_response_time:.2f}")
        print(f"  Average: {stats.total.avg_response_time:.2f}")
        print(f"  P95:     {stats.total.get_response_time_percentile(0.95):.2f}")
        print(f"  P99:     {stats.total.get_response_time_percentile(0.99):.2f}")

        print(f"\nRequests per second: {stats.total.total_rps:.2f}")
        print(f"Average Content Size: {stats.total.avg_content_length:.2f} bytes")
    else:
        print("No requests were made during the test")

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
    save_config = TransliterationConfig()

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
            "target_script": save_config.target_script,
            "is_sentence": save_config.is_sentence,
            "num_suggestions": save_config.num_suggestions
        },
        "statistics": {
            "total_requests": stats.total.num_requests,
            "failed_requests": stats.total.num_failures,
            "success_rate": ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0,
            "error_rate_percentage": round(error_rate, 2),
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

    filename = os.path.join(results_dir, "transliteration_load_test_results.json")
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to {filename}")


if __name__ == "__main__":
    """
    This allows running the script directly, but Locust should be run via CLI:
    locust -f load_testing_scripts/transliteration_test.py --host=http://13.204.164.186:8000
    """
    import sys
    print("\n" + "="*70)
    print("Transliteration Load Testing with Locust - DPG")
    print("="*70)
    print("\nTo run this test, use the Locust CLI:")
    print("\n1. Web UI mode (recommended):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/transliteration_test.py --host=http://13.204.164.186:8000")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f Load_testing_DPG/load_testing_scripts/transliteration_test.py --host=http://13.204.164.186:8000 \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/transliteration_test.py --host=http://13.204.164.186:8000 --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/transliteration_test.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
