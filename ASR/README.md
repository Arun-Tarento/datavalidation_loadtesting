# ASR Latency Load Testing with Locust

This directory contains a Locust-based load testing script for measuring ASR (Automatic Speech Recognition) service latency with advanced load testing capabilities including web UI, distributed testing, and real-time metrics.

## Files

- `asr_latency.py` - Locust load testing script
- `audio_samples.json` - JSON file containing base64 encoded audio samples
- `requirements.txt` - Python dependencies
- `README.md` - This documentation file

## Features

- **Web UI**: Interactive web interface to control and monitor tests
- **Real-time Metrics**: Live latency statistics (min, max, median, P95, P99)
- **Distributed Testing**: Scale across multiple machines
- **Flexible Load Patterns**: Control users, spawn rate, and duration
- **Detailed Reports**: JSON, CSV, and HTML report generation
- **Event Hooks**: Custom reporting at test start/stop

## Setup

### 1. Install Dependencies

```bash
pip install -r ASR/requirements.txt
```

This will install:
- `locust` - Load testing framework
- `python-dotenv` - Environment variable management
- `requests` - HTTP library

### 2. Configure Environment Variables

Update the `.env` file in the project root:

```env
# ASR Latency Load Testing Configuration
ASR_BASE_URL = https://core-v1.ai4inclusion.org
AUTH_TOKEN = your_actual_auth_token
USERNAME = your_username
PASSWORD = your_password

# ASR Service Configuration
ASR_SERVICE_ID = ai4bharat/indictasr
ASR_SOURCE_LANGUAGE = hi
ASR_CONTROL_CONFIG = {}

# Audio Configuration
AUDIO_FORMAT = wav
SAMPLING_RATE = 16000
TRANSCRIPTION_FORMAT = transcript
BEST_TOKEN_COUNT = 0

# Audio Samples File Path
AUDIO_SAMPLES_FILE = ASR/audio_samples.json

# Wait time between requests (optional)
MIN_WAIT_TIME = 1
MAX_WAIT_TIME = 3
```

### 3. Add Audio Samples

Edit `ASR/audio_samples.json` and replace placeholder strings with actual base64 encoded audio content:

```json
{
  "audio_samples": [
    "actual_base64_encoded_audio_1",
    "actual_base64_encoded_audio_2",
    "actual_base64_encoded_audio_3"
  ]
}
```

## Usage

### 1. Web UI Mode (Recommended)

Start Locust with web interface:

```bash
locust -f ASR/asr_latency.py --host=https://core-v1.ai4inclusion.org
```

Then open your browser to **http://localhost:8089**

In the web UI:
1. Set number of users (concurrent virtual users)
2. Set spawn rate (users started per second)
3. Click "Start Swarming"
4. Monitor real-time statistics, charts, and response times
5. Stop test when desired

### 2. Headless Mode (No Web UI)

Run automated test without browser:

```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless \
  -u 10 \
  -r 2 \
  --run-time 60s
```

Parameters:
- `-u 10`: 10 concurrent users
- `-r 2`: Spawn 2 users per second
- `--run-time 60s`: Run for 60 seconds

### 3. Generate Reports

#### HTML Report
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless \
  -u 20 \
  -r 5 \
  --run-time 2m \
  --html=asr_report.html
```

#### CSV Reports
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless \
  -u 20 \
  -r 5 \
  --run-time 2m \
  --csv=asr_results
```

This creates:
- `asr_results_stats.csv` - Request statistics
- `asr_results_stats_history.csv` - Time series data
- `asr_results_failures.csv` - Failure log

### 4. Distributed Load Testing

For high-scale testing across multiple machines:

**Start Master:**
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --master
```

**Start Workers (on same or different machines):**
```bash
locust -f ASR/asr_latency.py \
  --worker \
  --master-host=<master-ip-address>
```

You can start multiple workers to scale the load generation.

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ASR_BASE_URL` | Base URL of ASR service | Required |
| `AUTH_TOKEN` | Authentication token | Required |
| `USERNAME` | Username | Optional |
| `PASSWORD` | Password | Optional |
| `ASR_SERVICE_ID` | ASR Service ID | ai4bharat/indictasr |
| `ASR_SOURCE_LANGUAGE` | Source language code | hi |
| `ASR_CONTROL_CONFIG` | Control config (JSON) | {} |
| `AUDIO_FORMAT` | Audio format | wav |
| `SAMPLING_RATE` | Sampling rate in Hz | 16000 |
| `TRANSCRIPTION_FORMAT` | Transcription format | transcript |
| `BEST_TOKEN_COUNT` | Best token count | 0 |
| `AUDIO_SAMPLES_FILE` | Audio samples file path | ASR/audio_samples.json |
| `MIN_WAIT_TIME` | Min wait between requests (sec) | 1 |
| `MAX_WAIT_TIME` | Max wait between requests (sec) | 3 |

### Locust CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--host` | Target host URL | `--host=http://example.com:8080` |
| `-u, --users` | Number of concurrent users | `-u 100` |
| `-r, --spawn-rate` | Users spawned per second | `-r 10` |
| `--run-time` | Test duration | `--run-time 10m` |
| `--headless` | Run without web UI | `--headless` |
| `--html` | Generate HTML report | `--html=report.html` |
| `--csv` | Save CSV results | `--csv=results` |
| `--master` | Run as master (distributed) | `--master` |
| `--worker` | Run as worker (distributed) | `--worker` |
| `--master-host` | Master node hostname | `--master-host=192.168.1.100` |
| `--expect-workers` | Wait for N workers before starting | `--expect-workers=4` |
| `--tags` | Run tasks with specific tags | `--tags tag1 tag2` |
| `--exclude-tags` | Exclude tasks with tags | `--exclude-tags slow` |

## API Details

### Endpoint
```
POST {ASR_BASE_URL}/api/v1/asr/inference
```

### Headers
```json
{
  "x-auth-source": "{AUTH_TOKEN}",
  "Content-Type": "application/json"
}
```

### Payload Structure
```json
{
  "audio": [
    {
      "audioContent": "base64_encoded_string",
      "audioUri": ""
    }
  ],
  "config": {
    "serviceId": "ai4bharat/indictasr",
    "language": {
      "sourceLanguage": "hi"
    },
    "audioFormat": "wav",
    "samplingRate": 16000,
    "transcriptionFormat": "transcript",
    "bestTokenCount": 0
  },
  "controlConfig": {}
}
```

## Output and Metrics

### Console Output

When test starts:
```
======================================================================
ASR LATENCY LOAD TEST STARTED
======================================================================
Service ID: ai4bharat/indictasr
Source Language: hi
Audio Format: wav
Sampling Rate: 16000
Audio Samples Loaded: 5
======================================================================
```

When test completes:
```
======================================================================
ASR LATENCY LOAD TEST COMPLETED
======================================================================

Total Requests: 150
Failed Requests: 2
Success Rate: 98.67%

Response Time Statistics (milliseconds):
  Min:     156.23
  Max:     456.78
  Median:  234.50
  Average: 245.67
  P95:     389.12
  P99:     445.23

Requests per second: 12.50
Average Content Size: 1024.50 bytes
======================================================================

Detailed results saved to asr_latency_locust_results.json
```

### JSON Results File

`asr_latency_locust_results.json` contains:
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
    "total_requests": 150,
    "failed_requests": 2,
    "success_rate": 98.67,
    "response_time_ms": {
      "min": 156.23,
      "max": 456.78,
      "median": 234.50,
      "average": 245.67,
      "p95": 389.12,
      "p99": 445.23
    },
    "requests_per_second": 12.50,
    "average_content_size_bytes": 1024.50
  },
  "detailed_stats": {}
}
```

### Web UI Metrics

The Locust web UI at http://localhost:8089 provides:

1. **Statistics Tab**:
   - Request count, failure rate
   - Response time percentiles
   - Requests per second
   - Response size statistics

2. **Charts Tab**:
   - Real-time response time graphs
   - RPS (requests per second) over time
   - Number of users over time

3. **Failures Tab**:
   - List of all failures with error messages
   - Failure counts by error type

4. **Exceptions Tab**:
   - Python exceptions if any occurred

5. **Download Data**:
   - Download statistics as CSV
   - Download exceptions log

## Example Test Scenarios

### 1. Quick Smoke Test
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 5 -r 1 --run-time 30s
```

### 2. Load Test (100 users)
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 100 -r 10 --run-time 5m \
  --html=load_test_report.html
```

### 3. Stress Test (500 users)
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 500 -r 50 --run-time 10m \
  --csv=stress_test
```

### 4. Endurance Test (2 hours)
```bash
locust -f ASR/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 50 -r 5 --run-time 2h \
  --html=endurance_report.html
```

## Troubleshooting

### Common Issues

1. **"AUTH_TOKEN is required"**
   - Solution: Set `AUTH_TOKEN` in `.env` file

2. **"No audio samples found"**
   - Solution: Add base64 encoded audio to `audio_samples.json`

3. **Connection refused**
   - Solution: Verify `ASR_BASE_URL` is correct and accessible
   - Check if service is running

4. **High failure rate**
   - Check auth token validity
   - Verify audio content format
   - Check service capacity

5. **Locust command not found**
   - Solution: `pip install locust`

### Performance Tips

1. **For high load**: Use distributed mode with multiple workers
2. **Avoid bottlenecks**: Run master/workers on different machines
3. **Monitor resources**: Check CPU/memory on load generators
4. **Network**: Ensure good network connectivity to target service

## Advanced Usage

### Custom Load Shapes

You can create custom load patterns by extending `LoadTestShape` class:

```python
from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    Step load pattern: increases users in steps
    """
    step_time = 30  # seconds per step
    step_load = 10  # users per step
    spawn_rate = 2
    time_limit = 300  # total time in seconds

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.time_limit:
            return None

        current_step = run_time // self.step_time
        return (current_step * self.step_load, self.spawn_rate)
```

Use with:
```bash
locust -f ASR/asr_latency.py --host=... --shape=StepLoadShape
```

### Multiple Task Types

Add more tasks by adding methods with `@task` decorator:

```python
@task(3)  # Weight: 3x more likely than weight 1
def asr_request(self):
    # existing implementation

@task(1)  # Weight: 1
def health_check(self):
    self.client.get("/health")
```

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Locust API Reference](https://docs.locust.io/en/stable/api.html)
- [Writing a locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html)

## Notes

- Audio samples are randomly selected for each request
- Results are automatically saved to JSON after test completion
- The script assumes user is authenticated with valid token
- For production testing, start with low user count and gradually increase
