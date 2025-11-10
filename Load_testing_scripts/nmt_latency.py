"""
NMT Load Testing Script with Locust Integration
Tests the latency of NMT service at https://core-v1.ai4inclusion.org/

Usage:
    # Web UI mode (default)
    locust -f Load_testing_scripts/nmt_latency.py --host=https://core-v1.ai4inclusion.org

    # Headless mode
    locust -f Load_testing_scripts/nmt_latency.py --host=https://core-v1.ai4inclusion.org --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f Load_testing_scripts/nmt_latency.py --host=https://your-custom-host
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


class NMTConfig:
    """Configuration handler for NMT load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        print("NMTConfig.__init__() starting...")

        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "")
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

        # NMT Service Configuration
        self.service_id = os.getenv("NMT_SERVICE_ID", "indictrans-v2-all")
        self.source_language = os.getenv("NMT_SOURCE_LANGUAGE", "hi")
        self.target_language = os.getenv("NMT_TARGET_LANGUAGE", "ta")
        self.control_config = self._parse_control_config()

        # Load NMT samples
        print("About to call _load_nmt_samples()...")
        self.nmt_samples = self._load_nmt_samples()
        print(f"_load_nmt_samples() returned: {len(self.nmt_samples)} samples")

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("NMT_CONTROL_CONFIG", '{"dataTracking":false}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in NMT_CONTROL_CONFIG, using default")
            return {"dataTracking": False}

    def _load_nmt_samples(self) -> List[Dict[str, str]]:
        """Load NMT samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("NMT_SAMPLES_FILE", "test_samples/nmt/nmt_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
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
        """Build the API payload"""
        return {
            "input": [
                {
                    "source": source_text
                }
            ],
            "config": {
                "language": {
                    "sourceLanguage": self.source_language,
                    "targetLanguage": self.target_language
                },
                "serviceId": self.service_id
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

    def get_random_nmt_sample(self) -> str:
        """Get a random NMT sample from the loaded samples"""
        sample = random.choice(self.nmt_samples)
        return sample.get("source", "")


# Initialize global configuration (will be created fresh in each user)
# config = NMTConfig()  # Commented out to avoid caching


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
            print(f"Starting NMT User - Service: {self.config.service_id}, "
                  f"Language: {self.config.source_language} -> {self.config.target_language}")
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
        global payload_sizes
        payload_size = len(json.dumps(payload).encode('utf-8'))
        payload_sizes.append(payload_size)

        # Get headers
        headers = self.config.get_headers()

        # Send request with Locust's built-in metrics tracking
        with self.client.post(
            "/api/v1/nmt/inference",
            json=payload,
            headers=headers,
            catch_response=True,
            name="NMT Request"
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

            # Validate first output element is a dict with a non-empty translated text field
            first = output[0]
            if not isinstance(first, dict):
                self._track_failure()
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
                self._track_failure()
                response.failure("Empty or missing translated text in output[0]")
                return

            # Optional: basic sanity checks (length ratio, identical source->target detection)
            try:
                src = payload.get("input", [{}])[0].get("source", "")
                if isinstance(src, str) and src.strip():
                    # if translation equals source exactly, mark as warning/failure (adjust as needed)
                    if str(translated_text).strip() == str(src).strip():
                        self._track_failure()
                        response.failure("Translated text identical to source (possible failure)")
                        return
                    # optional: extremely short translations may indicate an error
                    if len(str(translated_text).split()) < 1:
                        self._track_failure()
                        response.failure("Translated text too short")
                        return
            except Exception:
                # don't crash — treat as non-fatal unless you want to enforce stricter checks
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
    test_config = NMTConfig()
    print("\n" + "="*70)
    print("NMT LATENCY LOAD TEST STARTED")
    print("="*70)
    print(f"Service ID: {test_config.service_id}")
    print(f"Source Language: {test_config.source_language}")
    print(f"Target Language: {test_config.target_language}")
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
    # Signal throughput thread to stop
    if hasattr(environment, '_throughput_stop_event'):
        environment._throughput_stop_event.set()

    print("\n" + "="*70)
    print("NMT LATENCY LOAD TEST COMPLETED")
    print("="*70)

    # Get statistics
    stats = environment.stats

    # Print summary
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
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
    save_config = NMTConfig()

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
            "target_language": save_config.target_language
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
    os.makedirs("results", exist_ok=True)
    filename = "results/nmt_latency_locust_results.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to {filename}")


if __name__ == "__main__":
    """
    This allows running the script directly, but Locust should be run via CLI:
    locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org
    """
    import sys
    print("\n" + "="*70)
    print("NMT Latency Load Testing with Locust")
    print("="*70)
    print("\nTo run this test, use the Locust CLI:")
    print("\n1. Web UI mode (recommended):")
    print("   locust -f Load_testing_scripts/nmt_latency.py --host=https://core-v1.ai4inclusion.org")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f Load_testing_scripts/nmt_latency.py --host=https://core-v1.ai4inclusion.org \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f Load_testing_scripts/nmt_latency.py --host=https://core-v1.ai4inclusion.org --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f Load_testing_scripts/nmt_latency.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
