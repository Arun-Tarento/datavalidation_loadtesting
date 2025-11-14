"""
ASR Load Testing Script with Locust Integration for DPG
Tests the latency of ASR service at http://13.204.164.186:8000/

Usage:
    # Web UI mode (default)
    locust -f load_testing_scripts/asr_test.py --host=http://13.204.164.186:8000

    # Headless mode
    locust -f load_testing_scripts/asr_test.py --host=http://13.204.164.186:8000 --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f load_testing_scripts/asr_test.py --host=http://your-custom-host
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


class ASRConfig:
    """Configuration handler for ASR load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        print("ASRConfig.__init__() starting...")

        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

        # ASR Service Configuration
        self.service_id = os.getenv("ASR_SERVICE_ID", "ai4bharat/indictasr")
        self.source_language = os.getenv("ASR_SOURCE_LANGUAGE", "hi")
        self.source_script = os.getenv("ASR_SOURCE_SCRIPT", "Deva")
        self.audio_format = os.getenv("ASR_AUDIO_FORMAT", "wav")
        self.encoding = os.getenv("ASR_ENCODING", "base64")
        self.sampling_rate = int(os.getenv("ASR_SAMPLING_RATE", "0"))
        self.transcription_format = os.getenv("ASR_TRANSCRIPTION_FORMAT", "transcript")
        self.best_token_count = int(os.getenv("ASR_BEST_TOKEN_COUNT", "0"))
        self.preprocessors = self._parse_list_config("ASR_PREPROCESSORS", [])
        self.postprocessors = self._parse_list_config("ASR_POSTPROCESSORS", [])
        self.control_config = self._parse_control_config()

        # Load ASR samples
        print("About to call _load_asr_samples()...")
        self.asr_samples = self._load_asr_samples()
        print(f"_load_asr_samples() returned: {len(self.asr_samples)} samples")

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("ASR_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in ASR_CONTROL_CONFIG, using default")
            return {"dataTracking": True}

    def _parse_list_config(self, key: str, default: List[str]) -> List[str]:
        """Parse list configuration from environment variable"""
        config_str = os.getenv(key, "")
        if not config_str:
            return default
        try:
            return json.loads(config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {key}, using default")
            return default

    def _load_asr_samples(self) -> List[str]:
        """Load ASR audio samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("ASR_SAMPLES_FILE", "load_testing_test_samples/ASR/audio_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels to the project root
            parent_dir = os.path.dirname(script_dir)
            project_root = os.path.dirname(parent_dir)
            file_path = os.path.join(project_root, file_path)

        print(f"\n=== LOADING ASR SAMPLES ===")
        print(f"Path: {file_path}")
        print(f"Exists: {os.path.exists(file_path)}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                print(f"Loaded: {len(samples)} audio samples")
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
            raise ValueError("ASR_SERVICE_ID is required in .env file")
        if not self.source_language:
            raise ValueError("ASR_SOURCE_LANGUAGE is required in .env file")
        if not self.asr_samples:
            raise ValueError("No ASR audio samples found. Please check audio_samples.json")

    def build_payload(self, audio_content: str) -> Dict[str, Any]:
        """Build the API payload for DPG ASR endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "audioFormat": self.audio_format,
                "language": {
                    "sourceLanguage": self.source_language,
                    "sourceScriptCode": self.source_script
                },
                "encoding": self.encoding,
                "samplingRate": self.sampling_rate,
                "serviceId": self.service_id,
                "preProcessors": self.preprocessors,
                "postProcessors": self.postprocessors,
                "transcriptionFormat": {
                    "value": self.transcription_format
                },
                "bestTokenCount": self.best_token_count
            },
            "audio": [
                {
                    "audioContent": audio_content
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

    def get_random_audio_sample(self) -> str:
        """Get a random audio sample from the loaded samples"""
        return random.choice(self.asr_samples)


class ASRUser(HttpUser):
    """Locust User class for ASR load testing"""

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
            self.config = ASRConfig()  # Create fresh config for each user

            # Install retry tracking adapter
            adapter = RetryTrackingAdapter()
            self.client.mount("http://", adapter)
            self.client.mount("https://", adapter)

            print(f"Starting ASR User - Service: {self.config.service_id}, "
                  f"Language: {self.config.source_language} ({self.config.source_script})")
        except Exception as e:
            print(f"ERROR in ASR User on_start: {e}")
            import traceback
            traceback.print_exc()
            raise

    @task
    def asr_request(self):
        """
        Task to send ASR request
        This is the main load testing task that will be executed repeatedly
        """
        # Get random audio sample
        audio_content = self.config.get_random_audio_sample()

        # Build payload
        payload = self.config.build_payload(audio_content)

        # Track payload size
        global payload_sizes
        payload_size = len(json.dumps(payload).encode('utf-8'))
        payload_sizes.append(payload_size)

        # Get headers
        headers = self.config.get_headers()

        # Query parameters
        params = {"serviceId": self.config.service_id}

        # Send request with Locust's built-in metrics tracking
        try:
            with self.client.post(
                "/services/inference/asr",
                params=params,
                json=payload,
                headers=headers,
                catch_response=True,
                name="ASR Transcription Request",
                timeout=250  # Increased timeout for audio processing under load
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

                # Validate first output element is a dict with non-empty 'source' field (transcript)
                first = output[0]
                if not isinstance(first, dict):
                    self._track_failure("INVALID_OUTPUT_FORMAT")
                    response.failure("Invalid output[0] format; expected object")
                    return

                # Get the transcript (source field contains the transcription)
                transcript = first.get("source", "")
                if not isinstance(transcript, str) or not transcript.strip():
                    self._track_failure("EMPTY_TRANSCRIPT")
                    response.failure("Empty or missing 'source' (transcript) in output[0]")
                    return

                # All checks passed -> success
                response.success()

        except Exception as e:
            # Catch connection errors, timeouts, etc.
            import requests.exceptions
            error_type = type(e).__name__

            # Distinguish between different exception types
            if isinstance(e, requests.exceptions.Timeout):
                self._track_failure("REQUEST_TIMEOUT")
            elif isinstance(e, requests.exceptions.ConnectionError):
                self._track_failure("CONNECTION_ERROR")
            else:
                self._track_failure(f"EXCEPTION_{error_type}")
            raise

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
    global first_failure_time, throughput_samples, payload_sizes, error_tracking, retry_count, retry_failures
    # Reset global tracking variables
    first_failure_time = None
    throughput_samples = []
    payload_sizes = []
    error_tracking = {}
    retry_count = 0
    retry_failures = 0

    # Create config instance for display
    load_dotenv(override=True)
    test_config = ASRConfig()
    print("\n" + "="*70)
    print("ASR LOAD TEST STARTED - DPG")
    print("="*70)
    print(f"Service ID: {test_config.service_id}")
    print(f"Source Language: {test_config.source_language} ({test_config.source_script})")
    print(f"Audio Format: {test_config.audio_format}")
    print(f"Sampling Rate: {test_config.sampling_rate}")
    print(f"ASR Samples Loaded: {len(test_config.asr_samples)}")
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
    print("ASR LOAD TEST COMPLETED - DPG")
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
        if stats.total.num_failures > 0 and error_tracking:
            print(f"\nError Breakdown:")
            print(f"  {'Error Type':<30} {'Count':>8} {'% of Failures':>15} {'% of Total':>12}")
            print(f"  {'-'*30} {'-'*8} {'-'*15} {'-'*12}")
            for error_type, count in sorted(error_tracking.items(), key=lambda x: x[1], reverse=True):
                pct_failures = (count / stats.total.num_failures) * 100
                pct_total = (count / stats.total.num_requests) * 100
                print(f"  {error_type:<30} {count:>8} {pct_failures:>14.2f}% {pct_total:>11.2f}%")

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
    global first_failure_time, throughput_samples, payload_sizes, error_tracking, retry_count, retry_failures
    stats = environment.stats

    # Create config instance for saving results
    load_dotenv(override=True)
    save_config = ASRConfig()

    # Calculate error rate
    error_rate = (stats.total.num_failures / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0

    # Calculate average payload size
    avg_payload_size = sum(payload_sizes) / len(payload_sizes) if payload_sizes else 0

    # Calculate retry statistics
    actual_server_requests = stats.total.num_requests + retry_count
    retry_rate = (retry_count / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0
    retry_failure_rate = (retry_failures / retry_count * 100) if retry_count > 0 else 0

    # Calculate error breakdown with percentages
    error_breakdown = {}
    total_failures = stats.total.num_failures
    if total_failures > 0:
        for error_type, count in error_tracking.items():
            error_breakdown[error_type] = {
                "count": count,
                "percentage_of_failures": round((count / total_failures) * 100, 2),
                "percentage_of_total_requests": round((count / stats.total.num_requests) * 100, 2)
            }

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
            "audio_format": save_config.audio_format,
            "sampling_rate": save_config.sampling_rate
        },
        "statistics": {
            "total_requests": stats.total.num_requests,
            "failed_requests": stats.total.num_failures,
            "success_rate": ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0,
            "error_rate_percentage": round(error_rate, 2),
            "error_breakdown": error_breakdown,
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

    filename = os.path.join(results_dir, "asr_load_test_results.json")
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to {filename}")


if __name__ == "__main__":
    """
    This allows running the script directly, but Locust should be run via CLI:
    locust -f load_testing_scripts/asr_test.py --host=http://13.204.164.186:8000
    """
    import sys
    print("\n" + "="*70)
    print("ASR Load Testing with Locust - DPG")
    print("="*70)
    print("\nTo run this test, use the Locust CLI:")
    print("\n1. Web UI mode (recommended):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/asr_test.py --host=http://13.204.164.186:8000")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f Load_testing_DPG/load_testing_scripts/asr_test.py --host=http://13.204.164.186:8000 \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/asr_test.py --host=http://13.204.164.186:8000 --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f Load_testing_DPG/load_testing_scripts/asr_test.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
