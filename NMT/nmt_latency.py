"""
NMT Load Testing Script with Locust Integration
Tests the latency of NMT service at https://core-v1.ai4inclusion.org/

Usage:
    # Web UI mode (default)
    locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org

    # Headless mode
    locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f NMT/nmt_latency.py --host=https://your-custom-host
"""

import os
import json
import random
from typing import Dict, Any, List
from dotenv import load_dotenv
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

# Load environment variables
load_dotenv()


class NMTConfig:
    """Configuration handler for NMT load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
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
        self.nmt_samples = self._load_nmt_samples()

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
        nmt_file_path = os.getenv("NMT_SAMPLES_FILE", "NMT/nmt_samples.json")
        try:
            with open(nmt_file_path, 'r') as f:
                data = json.load(f)
                samples = data.get("nmt_samples", [])
                if samples:
                    print(f"Loaded {len(samples)} NMT samples from {nmt_file_path}")
                return samples
        except FileNotFoundError:
            print(f"Error: NMT samples file not found at {nmt_file_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in NMT samples file")
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


# Initialize global configuration
config = NMTConfig()


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
        self.config = config
        print(f"Starting NMT User - Service: {self.config.service_id}, "
              f"Language: {self.config.source_language} -> {self.config.target_language}")

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
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    # Mark as success
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Response is not valid JSON")
            else:
                response.failure(f"Got status code {response.status_code}: {response.text}")


# Locust event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print("\n" + "="*70)
    print("NMT LATENCY LOAD TEST STARTED")
    print("="*70)
    print(f"Service ID: {config.service_id}")
    print(f"Source Language: {config.source_language}")
    print(f"Target Language: {config.target_language}")
    print(f"NMT Samples Loaded: {len(config.nmt_samples)}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
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
    stats = environment.stats

    output = {
        "test_config": {
            "service_id": config.service_id,
            "source_language": config.source_language,
            "target_language": config.target_language
        },
        "statistics": {
            "total_requests": stats.total.num_requests,
            "failed_requests": stats.total.num_failures,
            "success_rate": ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0,
            "response_time_ms": {
                "min": stats.total.min_response_time,
                "max": stats.total.max_response_time,
                "median": stats.total.median_response_time,
                "average": stats.total.avg_response_time,
                "p95": stats.total.get_response_time_percentile(0.95),
                "p99": stats.total.get_response_time_percentile(0.99)
            },
            "requests_per_second": stats.total.total_rps,
            "average_content_size_bytes": stats.total.avg_content_length
        },
        "detailed_stats": {}
    }

    # Add per-endpoint statistics
    for name, stat in stats.entries.items():
        if name != "Aggregated":
            output["detailed_stats"][name] = {
                "num_requests": stat.num_requests,
                "num_failures": stat.num_failures,
                "min_response_time": stat.min_response_time,
                "max_response_time": stat.max_response_time,
                "median_response_time": stat.median_response_time,
                "avg_response_time": stat.avg_response_time
            }

    # Save to file
    filename = "nmt_latency_locust_results.json"
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
    print("   locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f NMT/nmt_latency.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
