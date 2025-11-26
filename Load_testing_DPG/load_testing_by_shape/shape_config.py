"""
Configuration and User classes for Load Shape Testing
This module provides self-contained configuration for load_testing_by_shape folder
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
    """Configuration handler for ASR load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

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
        self.asr_samples = self._load_asr_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("ASR_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _parse_list_config(self, key: str, default: List[str]) -> List[str]:
        """Parse list configuration from environment variable"""
        config_str = os.getenv(key, "")
        if not config_str:
            return default
        try:
            return json.loads(config_str)
        except json.JSONDecodeError:
            return default

    def _load_asr_samples(self) -> List[str]:
        """Load ASR audio samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("ASR_SAMPLES_FILE", "load_testing_test_samples/ASR/audio_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to Load_testing_DPG, then up to Auto
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading ASR samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
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


class NMTConfig:
    """Configuration handler for NMT load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # NMT Service Configuration
        self.service_id = os.getenv("NMT_SERVICE_ID", "ai4bharat/indictrans--gpu-t4")
        self.source_language = os.getenv("NMT_SOURCE_LANGUAGE", "hi")
        self.source_script = os.getenv("NMT_SOURCE_SCRIPT", "Deva")
        self.target_language = os.getenv("NMT_TARGET_LANGUAGE", "ta")
        self.target_script = os.getenv("NMT_TARGET_SCRIPT", "Taml")
        self.control_config = self._parse_control_config()

        # Load NMT samples
        self.nmt_samples = self._load_nmt_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("NMT_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_nmt_samples(self) -> List[Dict[str, str]]:
        """Load NMT samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("NMT_SAMPLES_FILE", "load_testing_test_samples/nmt/nmt_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to Load_testing_DPG, then up to Auto
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("nmt_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading NMT samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
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


class ASRUser(HttpUser):
    """Locust User class for ASR load testing"""

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
        """Task to send ASR request"""
        audio_content = self.config.get_random_audio_sample()
        payload = self.config.build_payload(audio_content)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/asr",
            params=params,
            json=payload,
            headers=headers,
            timeout=120,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class NMTUser(HttpUser):
    """Locust User class for NMT load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = NMTConfig()

    @task
    def nmt_request(self):
        """Task to send NMT translation request"""
        source_text = self.config.get_random_nmt_sample()
        payload = self.config.build_payload(source_text)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/translation",
            params=params,
            json=payload,
            headers=headers,
            timeout=60,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class TTSConfig:
    """Configuration handler for TTS load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # TTS Service Configuration
        self.service_id = os.getenv("TTS_SERVICE_ID", "ai4bharat/indictts--gpu-t4")
        self.source_language = os.getenv("TTS_SOURCE_LANGUAGE", "hi")
        self.source_script = os.getenv("TTS_SOURCE_SCRIPT", "Deva")
        self.gender = os.getenv("TTS_GENDER", "male")
        self.sampling_rate = int(os.getenv("TTS_SAMPLING_RATE", "16000"))
        self.audio_format = os.getenv("TTS_AUDIO_FORMAT", "wav")
        self.control_config = self._parse_control_config()

        # Load TTS samples
        self.tts_samples = self._load_tts_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("TTS_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_tts_samples(self) -> List[Dict[str, str]]:
        """Load TTS samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("TTS_SAMPLES_FILE", "load_testing_test_samples/tts/tts_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to Load_testing_DPG, then up to Auto
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("tts_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading TTS samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.tts_samples:
            raise ValueError("No TTS samples found. Please check tts_samples.json")

    def build_payload(self, source_text: str) -> Dict[str, Any]:
        """Build the API payload for DPG TTS endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "serviceId": self.service_id,
                "gender": self.gender,
                "samplingRate": self.sampling_rate,
                "audioFormat": self.audio_format,
                "language": {
                    "sourceLanguage": self.source_language,
                    "sourceScriptCode": self.source_script
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

    def get_random_tts_sample(self) -> str:
        """Get a random TTS sample from the loaded samples"""
        sample = random.choice(self.tts_samples)
        return sample.get("source", "")


class TTSUser(HttpUser):
    """Locust User class for TTS load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = TTSConfig()

    @task
    def tts_request(self):
        """Task to send TTS request"""
        source_text = self.config.get_random_tts_sample()
        payload = self.config.build_payload(source_text)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/tts",
            params=params,
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class NERConfig:
    """Configuration handler for NER load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # NER Service Configuration
        self.service_id = os.getenv("NER_SERVICE_ID", "bhashini/ai4bharat/indic-ner")
        self.control_config = self._parse_control_config()

        # Load NER samples
        self.ner_samples = self._load_ner_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("NER_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_ner_samples(self) -> List[Dict[str, str]]:
        """Load NER samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("NER_SAMPLES_FILE", "load_testing_test_samples/ner/ner_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to Load_testing_DPG, then up to Auto
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("ner_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading NER samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.ner_samples:
            raise ValueError("No NER samples found. Please check ner_samples.json")

    def build_payload(self, source_text: str, language: str) -> Dict[str, Any]:
        """Build the API payload for DPG NER endpoint"""
        return {
            "input": [
                {
                    "source": source_text
                }
            ],
            "config": {
                "language": {
                    "sourceLanguage": language
                },
                "serviceId": self.service_id
            },
            "controlConfig": self.control_config
        }

    def get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "accept": "application/json",
            "x-auth-source": self.x_auth_source,
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }

    def get_random_ner_sample(self) -> Dict[str, str]:
        """Get a random NER sample from the loaded samples"""
        return random.choice(self.ner_samples)


class NERUser(HttpUser):
    """Locust User class for NER load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = NERConfig()

    @task
    def ner_request(self):
        """Task to send NER request"""
        sample = self.config.get_random_ner_sample()
        source_text = sample.get("source", "")
        language = sample.get("language", "hi")

        payload = self.config.build_payload(source_text, language)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/ner",
            params=params,
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class OCRConfig:
    """Configuration handler for OCR load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # OCR Service Configuration
        self.service_id = os.getenv("OCR_SERVICE_ID", "ai4bharat/surya-ocr-v1--gpu--t4")
        self.control_config = self._parse_control_config()

        # Load OCR samples
        self.ocr_samples = self._load_ocr_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("OCR_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_ocr_samples(self) -> List[Dict[str, str]]:
        """Load OCR samples from JSON file"""
        # Get file path - use environment variable or default
        file_path = os.getenv("OCR_SAMPLES_FILE", "load_testing_test_samples/ocr/ocr_samples.json")

        # Make it absolute if it's relative
        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to Load_testing_DPG, then up to Auto
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("ocr_samples", [])
                # Filter out placeholder samples
                valid_samples = [s for s in samples if s.get("imageContent") != "PLACEHOLDER_BASE64_IMAGE_HERE"]
                return valid_samples
        except Exception as e:
            print(f"ERROR loading OCR samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.ocr_samples:
            raise ValueError("No valid OCR samples found. Please check ocr_samples.json")

    def build_payload(self, image_content: str, language: str) -> Dict[str, Any]:
        """Build the API payload for DPG OCR endpoint"""
        return {
            "pipelineTasks": [
                {
                    "taskType": "ocr",
                    "config": {
                        "serviceId": self.service_id,
                        "language": {
                            "sourceLanguage": language
                        }
                    }
                }
            ],
            "inputData": {
                "image": [
                    {
                        "imageContent": image_content
                    }
                ]
            },
            "controlConfig": self.control_config
        }

    def get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "accept": "application/json",
            "x-auth-source": self.x_auth_source,
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }

    def get_random_ocr_sample(self) -> Dict[str, str]:
        """Get a random OCR sample from the loaded samples"""
        return random.choice(self.ocr_samples)


class OCRUser(HttpUser):
    """Locust User class for OCR load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = OCRConfig()

    @task
    def ocr_request(self):
        """Task to send OCR request"""
        sample = self.config.get_random_ocr_sample()
        image_content = sample.get("imageContent", "")
        language = sample.get("language", "hi")

        payload = self.config.build_payload(image_content, language)
        headers = self.config.get_headers()

        with self.client.post(
            "/services/inference/pipeline/ocr",
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# TRANSLITERATION Configuration and User
# ============================================================================

class TransliterationConfig:
    """Configuration handler for Transliteration load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

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
        self.transliteration_samples = self._load_transliteration_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("TRANSLITERATION_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_transliteration_samples(self) -> List[Dict[str, str]]:
        """Load Transliteration samples from JSON file"""
        file_path = os.getenv("TRANSLITERATION_SAMPLES_FILE", "load_testing_test_samples/transliteration/transliteration_samples.json")

        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("transliteration_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading Transliteration samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("TRANSLITERATION_SERVICE_ID is required in .env file")
        if not self.transliteration_samples:
            raise ValueError("No Transliteration samples found")

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

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = TransliterationConfig()

    @task
    def transliteration_request(self):
        """Task to send Transliteration request"""
        source_text = self.config.get_random_transliteration_sample()
        payload = self.config.build_payload(source_text)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/transliteration",
            params=params,
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# TLD (Text Language Detection) Configuration and User
# ============================================================================

class TLDConfig:
    """Configuration handler for TLD load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # TLD Service Configuration
        self.service_id = os.getenv("TLD_SERVICE_ID", "ai4bharat-indiclid")
        self.control_config = self._parse_control_config()

        # Load TLD samples
        self.tld_samples = self._load_tld_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("TLD_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_tld_samples(self) -> List[Dict[str, str]]:
        """Load TLD samples from JSON file"""
        file_path = os.getenv("TLD_SAMPLES_FILE", "load_testing_test_samples/tld/tld_samples.json")

        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("tld_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading TLD samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("TLD_SERVICE_ID is required in .env file")
        if not self.tld_samples:
            raise ValueError("No TLD samples found")

    def build_payload(self, source_text: str) -> Dict[str, Any]:
        """Build the API payload for DPG TLD endpoint"""
        return {
            "pipelineTasks": [
                {
                    "taskType": "txt-lang-detection",
                    "config": {
                        "serviceId": self.service_id
                    }
                }
            ],
            "inputData": {
                "input": [
                    {
                        "source": source_text
                    }
                ],
                "audio": [
                    {}
                ],
                "image": [
                    {}
                ]
            },
            "controlConfig": self.control_config
        }

    def get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "accept": "application/json",
            "x-auth-source": self.x_auth_source,
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }

    def get_random_tld_sample(self) -> Dict[str, str]:
        """Get a random TLD sample from the loaded samples"""
        return random.choice(self.tld_samples)


class TLDUser(HttpUser):
    """Locust User class for TLD load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = TLDConfig()

    @task
    def tld_request(self):
        """Task to send TLD request"""
        sample = self.config.get_random_tld_sample()
        source_text = sample.get("source", "")
        payload = self.config.build_payload(source_text)
        headers = self.config.get_headers()

        with self.client.post(
            "/services/inference/pipeline",
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# SPEAKER DIARIZATION Configuration and User
# ============================================================================

class SpeakerDiarizationConfig:
    """Configuration handler for Speaker Diarization load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # Speaker Diarization Service Configuration
        self.service_id = os.getenv("SPEAKER_DIARIZATION_SERVICE_ID", "ai4bharat/speaker-diarization")
        self.control_config = self._parse_control_config()

        # Load Speaker Diarization samples
        self.speaker_diarization_samples = self._load_speaker_diarization_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("SPEAKER_DIARIZATION_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_speaker_diarization_samples(self) -> List[str]:
        """Load Speaker Diarization samples from JSON file"""
        file_path = os.getenv("SPEAKER_DIARIZATION_SAMPLES_FILE", "load_testing_test_samples/speakerdiarization/speakerdiarization.json.example")

        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading Speaker Diarization samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("SPEAKER_DIARIZATION_SERVICE_ID is required in .env file")
        if not self.speaker_diarization_samples:
            raise ValueError("No Speaker Diarization samples found")

    def build_payload(self, audio_content: str) -> Dict[str, Any]:
        """Build the API payload for DPG Speaker Diarization endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "serviceId": self.service_id
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

    def get_random_speaker_diarization_sample(self) -> str:
        """Get a random Speaker Diarization sample from the loaded samples"""
        return random.choice(self.speaker_diarization_samples)


class SpeakerDiarizationUser(HttpUser):
    """Locust User class for Speaker Diarization load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = SpeakerDiarizationConfig()

    @task
    def speaker_diarization_request(self):
        """Task to send Speaker Diarization request"""
        audio_content = self.config.get_random_speaker_diarization_sample()
        payload = self.config.build_payload(audio_content)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/speaker-diarization",
            params=params,
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# LANGUAGE DIARIZATION Configuration and User
# ============================================================================

class LanguageDiarizationConfig:
    """Configuration handler for Language Diarization load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # Language Diarization Service Configuration
        self.service_id = os.getenv("LANGUAGE_DIARIZATION_SERVICE_ID", "ai4bharat/language-diarization")
        self.control_config = self._parse_control_config()

        # Load Language Diarization samples
        self.language_diarization_samples = self._load_language_diarization_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("LANGUAGE_DIARIZATION_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_language_diarization_samples(self) -> List[str]:
        """Load Language Diarization samples from JSON file"""
        file_path = os.getenv("LANGUAGE_DIARIZATION_SAMPLES_FILE", "load_testing_test_samples/languagediarization/languagediarization.json.example")

        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading Language Diarization samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("LANGUAGE_DIARIZATION_SERVICE_ID is required in .env file")
        if not self.language_diarization_samples:
            raise ValueError("No Language Diarization samples found")

    def build_payload(self, audio_content: str) -> Dict[str, Any]:
        """Build the API payload for DPG Language Diarization endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "serviceId": self.service_id
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

    def get_random_language_diarization_sample(self) -> str:
        """Get a random Language Diarization sample from the loaded samples"""
        return random.choice(self.language_diarization_samples)


class LanguageDiarizationUser(HttpUser):
    """Locust User class for Language Diarization load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = LanguageDiarizationConfig()

    @task
    def language_diarization_request(self):
        """Task to send Language Diarization request"""
        audio_content = self.config.get_random_language_diarization_sample()
        payload = self.config.build_payload(audio_content)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/language-diarization",
            params=params,
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# AUDIO LANGUAGE DETECTION (ALD) Configuration and User
# ============================================================================

class AudioLanguageDetectionConfig:
    """Configuration handler for Audio Language Detection (ALD) load testing"""

    def __init__(self):
        """Load configuration from environment variables"""
        # Authentication
        self.auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
        self.x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")

        # Audio Language Detection Service Configuration
        self.service_id = os.getenv("ALD_SERVICE_ID", "ai4bharat/audio-lang-detection")
        self.control_config = self._parse_control_config()

        # Load Audio Language Detection samples
        self.ald_samples = self._load_ald_samples()

        # Validate configuration
        self._validate_config()

    def _parse_control_config(self) -> Dict[str, Any]:
        """Parse controlConfig from environment variable"""
        control_config_str = os.getenv("ALD_CONTROL_CONFIG", '{"dataTracking":true}')
        try:
            return json.loads(control_config_str)
        except json.JSONDecodeError:
            return {"dataTracking": True}

    def _load_ald_samples(self) -> List[str]:
        """Load Audio Language Detection samples from JSON file"""
        file_path = os.getenv("ALD_SAMPLES_FILE", "load_testing_test_samples/ald/ald.json.example")

        if not os.path.isabs(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)  # Load_testing_DPG
            auto_dir = os.path.dirname(parent_dir)    # Auto
            file_path = os.path.join(auto_dir, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                samples = data.get("audio_samples", [])
                return samples
        except Exception as e:
            print(f"ERROR loading Audio Language Detection samples: {e}")
            return []

    def _validate_config(self):
        """Validate required configurations"""
        if not self.auth_token:
            raise ValueError("AUTH_TOKEN is required in .env file")
        if not self.service_id:
            raise ValueError("ALD_SERVICE_ID is required in .env file")
        if not self.ald_samples:
            raise ValueError("No Audio Language Detection samples found")

    def build_payload(self, audio_content: str) -> Dict[str, Any]:
        """Build the API payload for DPG Audio Language Detection endpoint"""
        return {
            "controlConfig": self.control_config,
            "config": {
                "serviceId": self.service_id
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

    def get_random_ald_sample(self) -> str:
        """Get a random Audio Language Detection sample from the loaded samples"""
        return random.choice(self.ald_samples)


class AudioLanguageDetectionUser(HttpUser):
    """Locust User class for Audio Language Detection (ALD) load testing"""

    wait_time = between(
        float(os.getenv("MIN_WAIT_TIME", "1")),
        float(os.getenv("MAX_WAIT_TIME", "3"))
    )

    def on_start(self):
        """Called when a simulated user starts"""
        load_dotenv(override=True)
        self.config = AudioLanguageDetectionConfig()

    @task
    def ald_request(self):
        """Task to send Audio Language Detection request"""
        audio_content = self.config.get_random_ald_sample()
        payload = self.config.build_payload(audio_content)
        headers = self.config.get_headers()
        params = {"serviceId": self.config.service_id}

        with self.client.post(
            "/services/inference/audio-lang-detection",
            params=params,
            json=payload,
            headers=headers,
            timeout=250,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
