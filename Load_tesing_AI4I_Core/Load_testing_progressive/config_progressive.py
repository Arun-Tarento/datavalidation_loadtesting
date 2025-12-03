"""
Configuration and User classes for Progressive Load Testing (AI4I Core API)
This module provides configuration for progressive load testing of various services
"""

import os
import json
import random
from typing import Dict, Any, List
from dotenv import load_dotenv
from locust import HttpUser, task, between

# Load environment variables
load_dotenv(override=True)


class ASRConfig:
    """Configuration handler for ASR load testing with AI4I Core API"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Base URL
        self.base_url = os.getenv("ASR_BASE_URL", "https://core-v1.ai4inclusion.org")

        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # ASR Service Configuration
        self.service_id = os.getenv("ASR_SERVICE_ID", "asr_am_ensemble")
        self.source_language = os.getenv("ASR_SOURCE_LANGUAGE", "hi")
        self.source_script = os.getenv("ASR_SOURCE_SCRIPT", "Deva")
        self.audio_format = os.getenv("ASR_AUDIO_FORMAT", "wav")
        self.encoding = os.getenv("ASR_ENCODING", "base64")
        self.sampling_rate = int(os.getenv("ASR_SAMPLING_RATE", "16000"))
        self.transcription_format = os.getenv("ASR_TRANSCRIPTION_FORMAT", "transcript")
        self.best_token_count = int(os.getenv("ASR_BEST_TOKEN_COUNT", "0"))

        # Parse list and dict configurations
        self.preprocessors = self._parse_list_config("ASR_PREPROCESSORS", ["vad", "denoise"])
        self.postprocessors = self._parse_list_config("ASR_POSTPROCESSORS", ["lm", "punctuation"])
        self.control_config = self._parse_control_config()

        # Load ASR samples
        self.asr_samples = self._load_asr_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("ASR_CONTROL_CONFIG", '{"dataTracking":false}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            print(f"WARNING: Failed to parse ASR_CONTROL_CONFIG, using default")
            return {"dataTracking": False}

    def _parse_list_config(self, key: str, default: List[str]) -> List[str]:
        """Parse list configuration from environment variable"""
        config_str = os.getenv(key, "")
        if not config_str:
            return default
        try:
            return json.loads(config_str)
        except json.JSONDecodeError:
            print(f"WARNING: Failed to parse {key}, using default: {default}")
            return default

    def _load_asr_samples(self) -> List[str]:
        """Load ASR audio samples from JSON file"""
        # Get file path from environment variable
        file_path = os.getenv("ASR_SAMPLES_FILE", "load_testing_test_samples/asr/audio_samples.json.example")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to Load_tesing_AI4I_Core, then up to root
            parent_dir = os.path.dirname(script_dir)  # Load_tesing_AI4I_Core
            root_dir = os.path.dirname(parent_dir)    # datavalidation_loadtesting
            file_path = os.path.join(root_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                if not samples:
                    print(f"WARNING: No audio_samples found in {file_path}")
                return samples
        except FileNotFoundError:
            print(f"ERROR: ASR samples file not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON from {file_path}: {e}")
            return []
        except Exception as e:
            print(f"ERROR loading ASR samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.asr_samples:
            raise ValueError("No ASR audio samples found. Please check ASR_SAMPLES_FILE path in .env")
        if not self.service_id:
            raise ValueError("ASR_SERVICE_ID is required in .env file")

    def build_payload(self, audio_content: str) -> Dict[str, Any]:
        """Build the API payload for AI4I Core ASR endpoint"""
        payload = {
            "audio": [
                {
                    "audioContent": audio_content
                }
            ],
            "config": {
                "language": {
                    "sourceLanguage": self.source_language
                },
                "serviceId": self.service_id,
                "audioFormat": self.audio_format,
                "samplingRate": self.sampling_rate,
                "transcriptionFormat": self.transcription_format,
                "bestTokenCount": self.best_token_count,
                "encoding": self.encoding,
                "preProcessors": self.preprocessors,
                "postProcessors": self.postprocessors
            },
            "controlConfig": self.control_config
        }
        return payload

    def get_headers(self) -> Dict[str, str]:
        """Get API headers for authentication"""
        return {
            "accept": "application/json",
            "x-auth-source": self.x_auth_source,
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }

    def get_random_audio_sample(self) -> str:
        """Get a random audio sample from the loaded samples"""
        if not self.asr_samples:
            raise ValueError("No audio samples available")
        return random.choice(self.asr_samples)


class ASRUser(HttpUser):
    """Locust User class for ASR load testing with AI4I Core API"""

    # Set host from environment variable
    host = os.getenv("ASR_BASE_URL", "http://core-v1.ai4inclusion.org:8080")

    # Set wait time between requests
    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = ASRConfig()

    @task
    def asr_request(self):
        """Task to send ASR request to AI4I Core endpoint"""
        try:
            # Get random audio sample
            audio_content = self.config.get_random_audio_sample()

            # Build payload and headers
            payload = self.config.build_payload(audio_content)
            headers = self.config.get_headers()

            # Send POST request
            with self.client.post(
                "/api/v1/asr/inference",
                json=payload,
                headers=headers,
                timeout=120,
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        # Validate response structure
                        if "output" in response_data:
                            response.success()
                        else:
                            response.failure(f"Invalid response structure: {response.text[:200]}")
                    except json.JSONDecodeError:
                        response.failure(f"Invalid JSON response: {response.text[:200]}")
                else:
                    response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"ERROR in asr_request: {e}")
