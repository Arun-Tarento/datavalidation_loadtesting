"""
TTS Load Testing Script with Locust Integration
Tests the latency of TTS service at https://core-v1.ai4inclusion.org/

Usage:
    # Web UI mode (default)
    locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org

    # Headless mode
    locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f Load_testing_scripts/tts_latency.py --host=https://your-custom-host
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

# Load environment variables
load_dotenv()

# Global tracking variables
first_failure_time: Optional[float] = None
throughput_samples = []  # List of (timestamp, rps) tuples
payload_sizes = []  # List of payload sizes in bytes


class TTSConfig:
    """Configuration handler for TTS load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "")
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

        # TTS Service Configuration
        self.service_id = os.getenv("TTS_SERVICE_ID", "indic-tts-coqui-indo_aryan")
        self.source_language = os.getenv("TTS_SOURCE_LANGUAGE", "hi")
        self.gender = os.getenv("TTS_GENDER", "female")
        self.sampling_rate = int(os.getenv("TTS_SAMPLING_RATE", "22050"))
        self.audio_format = os.getenv("TTS_AUDIO_FORMAT", "wav")
        self.control_config = self._parse_control_config()

        # Load TTS samples
        self.tts_samples = self._load_tts_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("TTS_CONTROL_CONFIG", '{"dataTracking":false}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in TTS_CONTROL_CONFIG, using default")
            return {"dataTracking": False}

    def _load_tts_samples(self) -> List[Dict[str, str]]:
        """Load TTS samples from JSON file"""
        tts_file_path = os.getenv("TTS_SAMPLES_FILE", "load_testing_test_samples/tts/tts_samples.json")

        # Convert to absolute path if it's relative
        if not os.path.isabs(tts_file_path):
            # Get the directory of this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels to the project root
            parent_dir = os.path.dirname(script_dir)
            project_root = os.path.dirname(parent_dir)
            tts_file_path = os.path.join(project_root, tts_file_path)

        try:
            with open(tts_file_path, 'r') as f:
                data = json.load(f)
                samples = data.get("tts_samples", [])
                if samples:
                    print(f"Loaded {len(samples)} TTS samples from {tts_file_path}")
                return samples
        except FileNotFoundError:
            print(f"Error: TTS samples file not found at {tts_file_path}")
            print(f"Current working directory: {os.getcwd()}")
            return []
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in TTS samples file")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("TTS_SERVICE_ID is required in .env file")
        if not self.source_language:
            raise ValueError("TTS_SOURCE_LANGUAGE is required in .env file")
        if not self.tts_samples:
            raise ValueError("No TTS samples found. Please check tts_samples.json")

    def build_payload(self, source_text: str) -> Dict[str, Any]:
        """Build the API payload"""
        return {
            "input": [
                {
                    "source": source_text
                }
            ],
            "config": {
                "language": {
                    "sourceLanguage": self.source_language
                },
                "serviceId": self.service_id,
                "gender": self.gender,
                "samplingRate": self.sampling_rate,
                "audioFormat": self.audio_format
            },
            "controlConfig": self.control_config
        }

    def get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "x-auth-source": self.x_auth_source,
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }

    def get_random_tts_sample(self) -> str:
        """Get a random TTS sample from the loaded samples"""
        sample = random.choice(self.tts_samples)
        return sample.get("source", "")


# Initialize global configuration (will be created fresh in each user)
# config = TTSConfig()  # Commented out to avoid caching


class TTSUser(HttpUser):
    """Locust User class for TTS load testing"""

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
            self.config = TTSConfig()  # Create fresh config for each user
            print(f"Starting TTS User - Service: {self.config.service_id}, "
                  f"Language: {self.config.source_language}, Gender: {self.config.gender}")
        except Exception as e:
            print(f"ERROR in TTS User on_start: {e}")
            import traceback
            traceback.print_exc()
            raise

    @task
    def tts_request(self):
        """
        Task to send TTS request
        This is the main load testing task that will be executed repeatedly
        """
        # Get random TTS sample
        source_text = self.config.get_random_tts_sample()

        # Build payload
        payload = self.config.build_payload(source_text)

        # Track payload size
        global payload_sizes
        payload_size = len(json.dumps(payload).encode('utf-8'))
        payload_sizes.append(payload_size)

        # Get headers
        headers = self.config.get_headers()

        # Send request with Locust's built-in metrics tracking
        with self.client.post(
            "/api/v1/tts/inference",
            json=payload,
            headers=headers,
            catch_response=True,
            name="TTS Request"
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

            # Validate first output element is a dict with audio content
            first = output[0]
            if not isinstance(first, dict):
                self._track_failure()
                response.failure("Invalid output[0] format; expected object")
                return

            # Look for audio content in various possible fields
            audio_content = (
                first.get("audioContent")
                or first.get("audio")
                or first.get("audioUri")
                or first.get("data")
            )

            # Check if audio content exists and is non-empty
            if not audio_content or (isinstance(audio_content, str) and not audio_content.strip()):
                self._track_failure()
                response.failure("Empty or missing audio content in output[0]")
                return

            # Optional: validate audio content is base64 or valid format
            try:
                if isinstance(audio_content, str):
                    # Basic check: base64 encoded audio should be reasonably long
                    if len(audio_content) < 100:
                        self._track_failure()
                        response.failure("Audio content too short (possible error)")
                        return
            except Exception:
                # Don't crash on validation errors
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
    global first_failure_time, throughput_samples, payload_sizes
    # Reset global tracking variables
    first_failure_time = None
    throughput_samples = []
    payload_sizes = []

    # Create config instance for display
    load_dotenv(override=True)
    test_config = TTSConfig()
    print("\n" + "="*70)
    print("TTS LATENCY LOAD TEST STARTED")
    print("="*70)
    print(f"Service ID: {test_config.service_id}")
    print(f"Source Language: {test_config.source_language}")
    print(f"Gender: {test_config.gender}")
    print(f"Sampling Rate: {test_config.sampling_rate}")
    print(f"Audio Format: {test_config.audio_format}")
    print(f"TTS Samples Loaded: {len(test_config.tts_samples)}")
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
    # Signal throughput thread to stop
    if hasattr(environment, '_throughput_stop_event'):
        environment._throughput_stop_event.set()

    print("\n" + "="*70)
    print("TTS LATENCY LOAD TEST COMPLETED")
    print("="*70)

    # Get statistics
    stats = environment.stats

    # Print summary
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")

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
    global first_failure_time, throughput_samples, payload_sizes
    stats = environment.stats

    # Create config instance for saving results
    load_dotenv(override=True)
    save_config = TTSConfig()

    # Calculate error rate
    error_rate = (stats.total.num_failures / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0

    # Calculate average payload size
    avg_payload_size = sum(payload_sizes) / len(payload_sizes) if payload_sizes else 0

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
            "gender": save_config.gender,
            "sampling_rate": save_config.sampling_rate,
            "audio_format": save_config.audio_format
        },
        "statistics": {
            "total_requests": stats.total.num_requests,
            "failed_requests": stats.total.num_failures,
            "success_rate": ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0,
            "error_rate_percentage": round(error_rate, 2),
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

    # Save to file
    os.makedirs("load_testing_results", exist_ok=True)
    filename = "load_testing_results/tts_latency_locust_results.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to {filename}")


if __name__ == "__main__":
    """
    This allows running the script directly, but Locust should be run via CLI:
    locust -f TTS/tts_latency.py --host=https://core-v1.ai4inclusion.org
    """
    import sys
    print("\n" + "="*70)
    print("TTS Latency Load Testing with Locust")
    print("="*70)
    print("\nTo run this test, use the Locust CLI:")
    print("\n1. Web UI mode (recommended):")
    print("   locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f Load_testing_scripts/tts_latency.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
