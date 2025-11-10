# TTS (Text-to-Speech) Load Testing

## Overview
This module contains load testing scripts for the TTS service at `https://core-v1.ai4inclusion.org/api/v1/tts/inference`.

## Script Location
- Main script: `Load_testing_scripts/tts_latency.py`

## Test Samples
- Location: `test_samples/tts/tts_samples.json`
- Format: JSON file containing text samples for speech synthesis
- Can be overridden via environment variable: `TTS_SAMPLES_FILE`

### Sample Format
```json
{
  "tts_samples": [
    {
      "source": "Text to be converted to speech"
    }
  ]
}
```

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:

```bash
# Authentication
AUTH_TOKEN="your_auth_token_here"
X_AUTH_SOURCE="YOUR_TOKEN"
USERNAME="your_username"
PASSWORD="your_password"

# TTS Service Configuration
TTS_SERVICE_ID="indic-tts-coqui-indo_aryan"
TTS_SOURCE_LANGUAGE="hi"
TTS_GENDER="female"
TTS_SAMPLING_RATE="22050"
TTS_AUDIO_FORMAT="wav"
TTS_CONTROL_CONFIG='{"dataTracking":false}'

# Test Configuration
MIN_WAIT_TIME="1"
MAX_WAIT_TIME="3"
TTS_SAMPLES_FILE="test_samples/tts/tts_samples.json"
```

## Usage

### 1. Web UI Mode (Recommended)
```bash
cd "/home/arun/Doc 2/Auto"
locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org
```
Then open http://localhost:8089 in your browser.

### 2. Headless Mode
```bash
locust -f Load_testing_scripts/tts_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 10 -r 2 --run-time 60s
```

### 3. Distributed Mode (Master)
```bash
locust -f Load_testing_scripts/tts_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --master
```

### 4. Distributed Mode (Worker)
```bash
locust -f Load_testing_scripts/tts_latency.py \
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
Test results are saved to: `results/tts_latency_locust_results.json`

### Result Format
```json
{
  "test_config": {
    "service_id": "indic-tts-coqui-indo_aryan",
    "source_language": "hi",
    "gender": "female",
    "sampling_rate": 22050,
    "audio_format": "wav"
  },
  "statistics": {
    "total_requests": 100,
    "failed_requests": 0,
    "success_rate": 100.0,
    "error_rate_percentage": 0.0,
    "response_time_ms": {
      "min": 200.2,
      "max": 3000.5,
      "median": 1000.3,
      "average": 1200.7,
      "p95": 2000.4,
      "p99": 2500.2
    },
    "requests_per_second": 3.5,
    "throughput": {...}
  }
}
```

## API Endpoint
- **URL**: `/api/v1/tts/inference`
- **Method**: POST
- **Timeout**: 60 seconds (default)

### Request Payload
```json
{
  "input": [
    {
      "source": "Text to be converted to speech"
    }
  ],
  "config": {
    "language": {
      "sourceLanguage": "hi"
    },
    "serviceId": "indic-tts-coqui-indo_aryan",
    "gender": "female",
    "samplingRate": 22050,
    "audioFormat": "wav"
  },
  "controlConfig": {
    "dataTracking": false
  }
}
```

### Response Format
```json
{
  "output": [
    {
      "audioContent": "base64_encoded_audio_data"
    }
  ]
}
```

## Validation
The script performs several validation checks:
1. Response status code is 200
2. Response is valid JSON
3. Output array exists and is non-empty
4. Audio content is present and non-empty
5. Audio content meets minimum length requirements (> 100 characters for base64)

## Voice Options
- **Gender**: male, female
- **Languages**: Multiple Indian languages supported
- **Audio Format**: WAV (recommended), other formats may be supported
- **Sampling Rate**: 22050 Hz (default), adjustable

Configure via environment variables:
- `TTS_GENDER`
- `TTS_SOURCE_LANGUAGE`
- `TTS_AUDIO_FORMAT`
- `TTS_SAMPLING_RATE`

## Supported Languages
The TTS service supports multiple Indian languages. Configure via `TTS_SOURCE_LANGUAGE` environment variable.

Common languages:
- Hindi (hi)
- Tamil (ta)
- Telugu (te)
- Bengali (bn)
- And many more...

## Test Scripts
Additional test script for debugging:
- `test_tts_minimal.py`: Minimal TTS test with timeout

## Notes
- The script creates fresh configuration for each user to avoid caching issues
- Environment variables are reloaded on each user start
- Absolute paths are used for reliable file access
- Audio output is base64-encoded
- TTS requests may take longer than NMT requests due to audio generation
- Failed requests are tracked with timestamp information
- Throughput tracking samples RPS every 2 seconds for detailed analysis
