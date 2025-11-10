# NMT (Neural Machine Translation) Load Testing

## Overview
This module contains load testing scripts for the NMT service at `https://core-v1.ai4inclusion.org/api/v1/nmt/inference`.

## Script Location
- Main script: `Load_testing_scripts/nmt_latency.py`

## Test Samples
- Location: `test_samples/nmt/nmt_samples.json`
- Format: JSON file containing text samples for translation
- Can be overridden via environment variable: `NMT_SAMPLES_FILE`

### Sample Format
```json
{
  "nmt_samples": [
    {
      "source": "Text to be translated"
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

# NMT Service Configuration
NMT_SERVICE_ID="indictrans-v2-all"
NMT_SOURCE_LANGUAGE="hi"
NMT_TARGET_LANGUAGE="ta"
NMT_CONTROL_CONFIG='{"dataTracking":false}'

# Test Configuration
MIN_WAIT_TIME="1"
MAX_WAIT_TIME="3"
NMT_SAMPLES_FILE="test_samples/nmt/nmt_samples.json"
```

## Usage

### 1. Web UI Mode (Recommended)
```bash
cd "/home/arun/Doc 2/Auto"
locust -f Load_testing_scripts/nmt_latency.py --host=https://core-v1.ai4inclusion.org
```
Then open http://localhost:8089 in your browser.

### 2. Headless Mode
```bash
locust -f Load_testing_scripts/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 10 -r 2 --run-time 60s
```

### 3. Distributed Mode (Master)
```bash
locust -f Load_testing_scripts/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --master
```

### 4. Distributed Mode (Worker)
```bash
locust -f Load_testing_scripts/nmt_latency.py \
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
Test results are saved to: `results/nmt_latency_locust_results.json`

### Result Format
```json
{
  "test_config": {
    "service_id": "indictrans-v2-all",
    "source_language": "hi",
    "target_language": "ta"
  },
  "statistics": {
    "total_requests": 100,
    "failed_requests": 0,
    "success_rate": 100.0,
    "error_rate_percentage": 0.0,
    "response_time_ms": {
      "min": 50.2,
      "max": 500.5,
      "median": 150.3,
      "average": 180.7,
      "p95": 300.4,
      "p99": 400.2
    },
    "requests_per_second": 15.5,
    "throughput": {...}
  }
}
```

## API Endpoint
- **URL**: `/api/v1/nmt/inference`
- **Method**: POST
- **Timeout**: 30 seconds (default)

### Request Payload
```json
{
  "input": [
    {
      "source": "Text to be translated"
    }
  ],
  "config": {
    "language": {
      "sourceLanguage": "hi",
      "targetLanguage": "ta"
    },
    "serviceId": "indictrans-v2-all"
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
      "target": "Translated text in target language"
    }
  ]
}
```

## Validation
The script performs several validation checks:
1. Response status code is 200
2. Response is valid JSON
3. Output array exists and is non-empty
4. Translated text is present and non-empty
5. Translated text is different from source text
6. Translated text meets minimum length requirements

## Supported Language Pairs
The NMT service supports translation between multiple Indian languages. Common pairs include:
- Hindi (hi) ↔ Tamil (ta)
- Hindi (hi) ↔ Telugu (te)
- Hindi (hi) ↔ Bengali (bn)
- And many more...

Configure via `NMT_SOURCE_LANGUAGE` and `NMT_TARGET_LANGUAGE` environment variables.

## Notes
- The script creates fresh configuration for each user to avoid caching issues
- Environment variables are reloaded on each user start
- Absolute paths are used for reliable file access
- Failed requests are tracked with timestamp information
