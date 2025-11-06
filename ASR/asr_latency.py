"""
ASR Load Testing Script with Locust Integration
Tests the latency of ASR service at https://core-v1.ai4inclusion.org/

Usage:
    # Web UI mode (default)
    locust -f ASR/asr_latency.py --host=https://core-v1.ai4inclusion.org

    # Headless mode
    locust -f ASR/asr_latency.py --host=https://core-v1.ai4inclusion.org --headless -u 10 -r 2 --run-time 60s

    # With custom host
    locust -f ASR/asr_latency.py --host=https://your-custom-host
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


class ASRConfig:
    """Configuration handler for ASR load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "")
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

        # ASR Service Configuration
        self.service_id = os.getenv("ASR_SERVICE_ID", "ai4bharat/indictasr")
        self.source_language = os.getenv("ASR_SOURCE_LANGUAGE", "hi")
        self.control_config = self._parse_control_config()

        # Audio Configuration
        self.audio_format = os.getenv("AUDIO_FORMAT", "wav")
        self.sampling_rate = int(os.getenv("SAMPLING_RATE", "16000"))
        self.transcription_format = os.getenv("TRANSCRIPTION_FORMAT", "transcript")
        self.best_token_count = int(os.getenv("BEST_TOKEN_COUNT", "0"))

        # Load audio samples
        self.audio_samples = self._load_audio_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("ASR_CONTROL_CONFIG", "{}")
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in ASR_CONTROL_CONFIG, using empty dict")
            return {}

    def _load_audio_samples(self) -> List[str]:
        """Load audio samples from JSON file"""
        audio_file_path = os.getenv("AUDIO_SAMPLES_FILE", "ASR/audio_samples.json")
        try:
            with open(audio_file_path, 'r') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                if samples:
                    print(f"Loaded {len(samples)} audio samples from {audio_file_path}")
                return samples
        except FileNotFoundError:
            print(f"Error: Audio samples file not found at {audio_file_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in audio samples file")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("ASR_SERVICE_ID is required in .env file")
        if not self.source_language:
            raise ValueError("ASR_SOURCE_LANGUAGE is required in .env file")
        if not self.audio_samples:
            raise ValueError("No audio samples found. Please check audio_samples.json")

    def build_payload(self, audio_content: str) -> Dict[str, Any]:
        """Build the API payload"""
        return {
            "audio": [
                {
                    "audioContent": audio_content,
                    # "audioUri": audio_uri
                }
            ],
            "config": {
                "serviceId": self.service_id,
                "language": {
                    "sourceLanguage": self.source_language
                },
                "audioFormat": self.audio_format,
                "samplingRate": self.sampling_rate,
                "transcriptionFormat": self.transcription_format,
                "bestTokenCount": self.best_token_count
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

    def get_random_audio_sample(self) -> str:
        """Get a random audio sample from the loaded samples"""
        return random.choice(self.audio_samples)


# Initialize global configuration
config = ASRConfig()


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
        self.config = config
        print(f"Starting ASR User - Service: {self.config.service_id}, Language: {self.config.source_language}")

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

        # Get headers
        headers = self.config.get_headers()

        # Send request with Locust's built-in metrics tracking
        with self.client.post(
            "/api/v1/asr/inference",
            json=payload,
            headers=headers,
            catch_response=True,
            name="ASR Request"
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
    print("ASR LATENCY LOAD TEST STARTED")
    print("="*70)
    print(f"Service ID: {config.service_id}")
    print(f"Source Language: {config.source_language}")
    print(f"Audio Format: {config.audio_format}")
    print(f"Sampling Rate: {config.sampling_rate}")
    print(f"Audio Samples Loaded: {len(config.audio_samples)}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("\n" + "="*70)
    print("ASR LATENCY LOAD TEST COMPLETED")
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
            "audio_format": config.audio_format,
            "sampling_rate": config.sampling_rate,
            "transcription_format": config.transcription_format
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
    filename = "asr_latency_locust_results.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to {filename}")


# Custom shape classes for advanced load patterns
class StepLoadShape:
    """
    Example custom load shape - increases users in steps
    To use: locust -f asr_latency.py --host=... --shape=StepLoadShape
    """
    pass


if __name__ == "__main__":
    """
    This allows running the script directly, but Locust should be run via CLI:
    locust -f ASR/asr_latency.py --host=http://core-v1.ai4inclusion.org:8080
    """
    import sys
    print("\n" + "="*70)
    print("ASR Latency Load Testing with Locust")
    print("="*70)
    print("\nTo run this test, use the Locust CLI:")
    print("\n1. Web UI mode (recommended):")
    print("   locust -f ASR/asr_latency.py --host=https://core-v1.ai4inclusion.org")
    print("   Then open http://localhost:8089 in your browser")
    print("\n2. Headless mode:")
    print("   locust -f ASR/asr_latency.py --host=https://core-v1.ai4inclusion.org \\")
    print("          --headless -u 10 -r 2 --run-time 60s")
    print("\n3. Distributed mode (master):")
    print("   locust -f ASR/asr_latency.py --host=https://core-v1.ai4inclusion.org --master")
    print("\n4. Distributed mode (worker):")
    print("   locust -f ASR/asr_latency.py --worker --master-host=<master-ip>")
    print("\nOptions:")
    print("  -u, --users       Number of concurrent users")
    print("  -r, --spawn-rate  Spawn rate (users per second)")
    print("  --run-time        Test duration (e.g., 60s, 10m, 1h)")
    print("  --headless        Run without web UI")
    print("  --csv             Save results to CSV files")
    print("  --html            Generate HTML report")
    print("\n" + "="*70 + "\n")
