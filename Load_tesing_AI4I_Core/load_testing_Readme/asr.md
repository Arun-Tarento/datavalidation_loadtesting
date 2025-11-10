# ASR (Automatic Speech Recognition) Load Testing

## Overview
This module contains load testing scripts for the ASR service at `https://core-v1.ai4inclusion.org/api/v1/asr/inference`.

## Script Location
- Main script: `Load_testing_scripts/asr_latency.py`

## Test Samples
- Location: `test_samples/asr/audio_samples.json`
- Format: JSON file containing base64-encoded audio samples
- Can be overridden via environment variable: `AUDIO_SAMPLES_FILE`

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:

```bash
# Authentication
AUTH_TOKEN="your_auth_token_here"
X_AUTH_SOURCE="YOUR_TOKEN"
USERNAME="your_username"
PASSWORD="your_password"

# ASR Service Configuration
ASR_SERVICE_ID="ai4bharat/indictasr"
ASR_SOURCE_LANGUAGE="hi"
ASR_CONTROL_CONFIG="{}"

# Audio Configuration
AUDIO_FORMAT="wav"
SAMPLING_RATE="16000"
TRANSCRIPTION_FORMAT="transcript"
BEST_TOKEN_COUNT="0"
ASR_ENCODING="base64"
ASR_PREPROCESSORS='["vad", "denoise"]'
ASR_POSTPROCESSORS='["lm", "punctuation"]'

# Test Configuration
MIN_WAIT_TIME="1"
MAX_WAIT_TIME="3"
AUDIO_SAMPLES_FILE="test_samples/asr/audio_samples.json"
```

## Usage

### 1. Web UI Mode (Recommended)
```bash
cd "/home/arun/Doc 2/Auto"
locust -f Load_testing_scripts/asr_latency.py --host=https://core-v1.ai4inclusion.org
```
Then open http://localhost:8089 in your browser.

### 2. Headless Mode
```bash
locust -f Load_testing_scripts/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 10 -r 2 --run-time 60s
```

### 3. Distributed Mode (Master)
```bash
locust -f Load_testing_scripts/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --master
```

### 4. Distributed Mode (Worker)
```bash
locust -f Load_testing_scripts/asr_latency.py \
  --worker --master-host=<master-ip>
```

## Command Line Options
- `-u, --users`: Number of concurrent users
- `-r, --spawn-rate`: Spawn rate (users per second)
- `--run-time`: Test duration (e.g., 60s, 10m, 1h)
- `--headless`: Run without web UI
- `--csv`: Save results to CSV files
- `--html`: Generate HTML report

## Results
Test results are saved to: `results/asr_latency_locust_results.json`

### Result Format
```json
{
  "test_config": {
    "service_id": "ai4bharat/indictasr",
    "source_language": "hi",
    "audio_format": "wav",
    "sampling_rate": 16000,
    "transcription_format": "transcript"
  },
  "statistics": {
    "total_requests": 100,
    "failed_requests": 0,
    "success_rate": 100.0,
    "error_rate_percentage": 0.0,
    "response_time_ms": {
      "min": 150.2,
      "max": 2500.5,
      "median": 800.3,
      "average": 850.7,
      "p95": 1200.4,
      "p99": 1800.2
    },
    "requests_per_second": 5.5,
    "throughput": {...}
  }
}
```

## API Endpoint
- **URL**: `/api/v1/asr/inference`
- **Method**: POST
- **Timeout**: 60 seconds

### Request Payload
```json
{
  "audio": [
    {
      "audioContent": "base64_encoded_audio_data"
    }
  ],
  "config": {
    "language": {
      "sourceLanguage": "hi"
    },
    "serviceId": "ai4bharat/indictasr",
    "audioFormat": "wav",
    "samplingRate": 16000,
    "transcriptionFormat": "transcript",
    "bestTokenCount": 0,
    "encoding": "base64",
    "preProcessors": ["vad", "denoise"],
    "postProcessors": ["lm", "punctuation"]
  },
  "controlConfig": {}
}
```

### Response Format
```json
{
  "output": [
    {
      "source": "transcribed text in source language"
    }
  ]
}
```

## Test Scripts
Additional test scripts for debugging:
- `check_audio.py`: Check audio file properties
- `test_asr_direct.py`: Direct API test
- `test_asr_minimal.py`: Minimal ASR test with timeout
- `test_asr_with_browser_headers.py`: Test with browser-like headers
- `test_single_request.py`: Single request test

## Supported Languages
The ASR service supports multiple Indian languages. Configure via `ASR_SOURCE_LANGUAGE` environment variable.

## Notes
- Audio files must be base64-encoded
- Supported format: WAV
- Recommended sampling rate: 16000 Hz
- The script automatically handles path resolution for sample files
