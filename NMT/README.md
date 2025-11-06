# NMT Latency Load Testing with Locust

This directory contains a Locust-based load testing script for measuring NMT (Neural Machine Translation) service latency with advanced load testing capabilities including web UI, distributed testing, and real-time metrics.

## Files

- `nmt_latency.py` - Locust load testing script
- `nmt_samples.json` - JSON file containing sample texts for translation
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
# Authentication (shared with ASR)
AUTH_TOKEN = "Bearer your_access_token"
X_AUTH_SOURCE = YOUR_TOKEN
USERNAME = your_username
PASSWORD = your_password

# NMT Service Configuration
NMT_SERVICE_ID = indictrans-v2-all
NMT_SOURCE_LANGUAGE = hi
NMT_TARGET_LANGUAGE = ta
NMT_CONTROL_CONFIG = {"dataTracking":false}

# NMT Samples File Path
NMT_SAMPLES_FILE = NMT/nmt_samples.json

# Wait time between requests (optional)
MIN_WAIT_TIME = 1
MAX_WAIT_TIME = 3
```

### 3. Add Translation Samples

Edit `NMT/nmt_samples.json` and add your sample texts:

```json
{
  "nmt_samples": [
    {
      "source": "आर्टिफिशियल इंटेलिजेंस के क्षेत्र में भारत की तरक्की कमाल की है।"
    },
    {
      "source": "देश का बढ़ता AI इकोसिस्टम रिसर्च के प्रति मज़बूत कमिटमेंट को दिखाता है।"
    },
    {
      "source": "भारत में प्रौद्योगिकी का विकास तेजी से हो रहा है।"
    }
  ]
}
```

## Usage

### 1. Web UI Mode (Recommended)

Start Locust with web interface:

```bash
locust -f NMT/nmt_latency.py --host=https://core-v1.ai4inclusion.org
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
locust -f NMT/nmt_latency.py \
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
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless \
  -u 20 \
  -r 5 \
  --run-time 2m \
  --html=nmt_report.html
```

#### CSV Reports
```bash
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless \
  -u 20 \
  -r 5 \
  --run-time 2m \
  --csv=nmt_results
```

This creates:
- `nmt_results_stats.csv` - Request statistics
- `nmt_results_stats_history.csv` - Time series data
- `nmt_results_failures.csv` - Failure log

### 4. Distributed Load Testing

For high-scale testing across multiple machines:

**Start Master:**
```bash
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --master
```

**Start Workers (on same or different machines):**
```bash
locust -f NMT/nmt_latency.py \
  --worker \
  --master-host=<master-ip-address>
```

You can start multiple workers to scale the load generation.

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_TOKEN` | Bearer token for Authorization header | Required |
| `X_AUTH_SOURCE` | Token for x-auth-source header | Required |
| `USERNAME` | Username | Optional |
| `PASSWORD` | Password | Optional |
| `NMT_SERVICE_ID` | NMT Service ID | indictrans-v2-all |
| `NMT_SOURCE_LANGUAGE` | Source language code | hi |
| `NMT_TARGET_LANGUAGE` | Target language code | ta |
| `NMT_CONTROL_CONFIG` | Control config (JSON) | {"dataTracking":false} |
| `NMT_SAMPLES_FILE` | NMT samples file path | NMT/nmt_samples.json |
| `MIN_WAIT_TIME` | Min wait between requests (sec) | 1 |
| `MAX_WAIT_TIME` | Max wait between requests (sec) | 3 |

### Locust CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--host` | Target host URL | `--host=https://core-v1.ai4inclusion.org` |
| `-u, --users` | Number of concurrent users | `-u 100` |
| `-r, --spawn-rate` | Users spawned per second | `-r 10` |
| `--run-time` | Test duration | `--run-time 10m` |
| `--headless` | Run without web UI | `--headless` |
| `--html` | Generate HTML report | `--html=report.html` |
| `--csv` | Save CSV results | `--csv=results` |
| `--master` | Run as master (distributed) | `--master` |
| `--worker` | Run as worker (distributed) | `--worker` |
| `--master-host` | Master node hostname | `--master-host=192.168.1.100` |

## API Details

### Endpoint
```
POST https://core-v1.ai4inclusion.org/api/v1/nmt/inference
```

### Headers
```json
{
  "x-auth-source": "YOUR_TOKEN",
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

### Payload Structure
```json
{
  "input": [
    {
      "source": "आर्टिफिशियल इंटेलिजेंस के क्षेत्र में भारत की तरक्की कमाल की है।"
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

## Output and Metrics

### Console Output

When test starts:
```
======================================================================
NMT LATENCY LOAD TEST STARTED
======================================================================
Service ID: indictrans-v2-all
Source Language: hi
Target Language: ta
NMT Samples Loaded: 5
======================================================================
```

When test completes:
```
======================================================================
NMT LATENCY LOAD TEST COMPLETED
======================================================================

Total Requests: 150
Failed Requests: 2
Success Rate: 98.67%

Response Time Statistics (milliseconds):
  Min:     256.23
  Max:     856.78
  Median:  434.50
  Average: 445.67
  P95:     689.12
  P99:     745.23

Requests per second: 12.50
Average Content Size: 2048.50 bytes
======================================================================

Detailed results saved to nmt_latency_locust_results.json
```

### JSON Results File

`nmt_latency_locust_results.json` contains:
```json
{
  "test_config": {
    "service_id": "indictrans-v2-all",
    "source_language": "hi",
    "target_language": "ta"
  },
  "statistics": {
    "total_requests": 150,
    "failed_requests": 2,
    "success_rate": 98.67,
    "response_time_ms": {
      "min": 256.23,
      "max": 856.78,
      "median": 434.50,
      "average": 445.67,
      "p95": 689.12,
      "p99": 745.23
    },
    "requests_per_second": 12.50,
    "average_content_size_bytes": 2048.50
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
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 5 -r 1 --run-time 30s
```

### 2. Load Test (100 users)
```bash
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 100 -r 10 --run-time 5m \
  --html=nmt_load_test_report.html
```

### 3. Stress Test (500 users)
```bash
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 500 -r 50 --run-time 10m \
  --csv=nmt_stress_test
```

### 4. Endurance Test (2 hours)
```bash
locust -f NMT/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 50 -r 5 --run-time 2h \
  --html=nmt_endurance_report.html
```

## Troubleshooting

### Common Issues

1. **"AUTH_TOKEN is required"**
   - Solution: Set `AUTH_TOKEN` in `.env` file

2. **"No NMT samples found"**
   - Solution: Add samples to `nmt_samples.json`

3. **Connection refused**
   - Solution: Verify host URL is correct and accessible
   - Check if service is running

4. **High failure rate**
   - Check auth token validity
   - Verify text sample format
   - Check service capacity

5. **"Not authenticated" error**
   - Verify both `AUTH_TOKEN` and `X_AUTH_SOURCE` are set correctly
   - Ensure tokens haven't expired

### Performance Tips

1. **For high load**: Use distributed mode with multiple workers
2. **Avoid bottlenecks**: Run master/workers on different machines
3. **Monitor resources**: Check CPU/memory on load generators
4. **Network**: Ensure good network connectivity to target service

## Language Codes

Common language codes for NMT service:
- `hi` - Hindi
- `ta` - Tamil
- `te` - Telugu
- `bn` - Bengali
- `mr` - Marathi
- `gu` - Gujarati
- `kn` - Kannada
- `ml` - Malayalam
- `pa` - Punjabi
- `en` - English

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Locust API Reference](https://docs.locust.io/en/stable/api.html)
- [Writing a locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html)

## Notes

- NMT samples are randomly selected for each request
- Results are automatically saved to JSON after test completion
- The script assumes user is authenticated with valid tokens
- For production testing, start with low user count and gradually increase
- Longer texts may result in higher latency
