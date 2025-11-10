# AI4Bharat Core Load Testing Suite

Load testing suite for AI4Bharat Core services including ASR (Automatic Speech Recognition), NMT (Neural Machine Translation), and TTS (Text-to-Speech).

## Table of Contents
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Test Results](#test-results)
- [Documentation](#documentation)
- [Project Structure](#project-structure)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. **Create and activate a virtual environment** (recommended):
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate on Linux/Mac
   source venv/bin/activate

   # Activate on Windows
   venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   cd "/home/arun/Doc 2/Auto/Load_tesing_AI4I_Core"
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   - Update the `.env` file with your credentials
   - Ensure you have a valid authentication token

## Configuration

The `.env` file contains all configuration parameters:

```bash
# Authentication
AUTH_TOKEN="Bearer your_token_here"
X_AUTH_SOURCE=YOUR_TOKEN

# Service Configuration
ASR_SERVICE_ID=asr_am_ensemble
NMT_SERVICE_ID=indictrans-v2-all
TTS_SERVICE_ID=indic-tts-coqui-indo_aryan

# Test Configuration
MIN_WAIT_TIME=1
MAX_WAIT_TIME=3
```

## Usage

### Web UI Mode (Recommended)

Navigate to the project directory and run:

```bash
cd "/home/arun/Doc 2/Auto/Load_tesing_AI4I_Core"

# For NMT (Translation) Load Testing
locust -f Load_testing_scripts/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org

# For ASR (Speech Recognition) Load Testing
locust -f Load_testing_scripts/asr_latency.py \
  --host=https://core-v1.ai4inclusion.org

# For TTS (Text-to-Speech) Load Testing
locust -f Load_testing_scripts/tts_latency.py \
  --host=https://core-v1.ai4inclusion.org
```

Then open your browser to `http://localhost:8089` to access the Locust web interface.

### Headless Mode

For automated testing without the web interface:

```bash
# Example: 10 concurrent users, spawn rate of 2 users/second, run for 60 seconds
locust -f Load_testing_scripts/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --headless -u 10 -r 2 --run-time 60s
```

### Distributed Mode

For large-scale load testing across multiple machines:

**Master Node:**
```bash
locust -f Load_testing_scripts/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org \
  --master
```

**Worker Nodes:**
```bash
locust -f Load_testing_scripts/nmt_latency.py \
  --worker --master-host=<master-ip>
```

### Command Line Options

- `-u, --users`: Number of concurrent users (default: 1)
- `-r, --spawn-rate`: Rate to spawn users at (users per second)
- `--run-time`: Stop after the specified time (e.g., 60s, 10m, 1h)
- `--headless`: Run without web UI
- `--csv=PREFIX`: Save results to CSV files with given prefix
- `--html=FILE`: Generate HTML report
- `--host=URL`: Override the host URL

## Test Results

Results are automatically saved to the `load_testing_results/` directory:

- `asr_latency_locust_results.json` - ASR test results
- `nmt_latency_locust_results.json` - NMT test results
- `tts_latency_locust_results.json` - TTS test results

### Result Format

Each JSON result file contains:
- **test_config**: Service configuration used
- **statistics**: Performance metrics including:
  - Total requests and failures
  - Success rate
  - Response time statistics (min, max, median, average, P95, P99)
  - Requests per second
  - Throughput analysis (average, min, max RPS over time)
  - First failure information

### Understanding Metrics

**Key Metrics Explained:**

1. **`requests_per_second`**: Overall average RPS (total requests / total time)
2. **`average_rps`**: Time-weighted average of RPS sampled every 2 seconds
3. **`max_rps`**: Peak RPS achieved during the test
4. **Response Time Percentiles**:
   - **P95**: 95% of requests completed within this time
   - **P99**: 99% of requests completed within this time

## Documentation

Detailed documentation for each service is available in the `load_testing_Readme/` directory:

- [ASR Load Testing Guide](load_testing_Readme/asr.md)
- [NMT Load Testing Guide](load_testing_Readme/nmt.md)
- [TTS Load Testing Guide](load_testing_Readme/tts.md)

## Project Structure

```
Load_tesing_AI4I_Core/
├── .env                          # Environment configuration
├── requirements.txt              # Python dependencies
├── load_testing_Readme.md        # This file
├── Load_testing_scripts/         # Load testing scripts
│   ├── asr_latency.py           # ASR load testing
│   ├── nmt_latency.py           # NMT load testing
│   └── tts_latency.py           # TTS load testing
├── load_testing_Readme/          # Detailed documentation
│   ├── asr.md
│   ├── nmt.md
│   └── tts.md
└── load_testing_results/         # Test results (auto-generated)
    ├── asr_latency_locust_results.json
    ├── nmt_latency_locust_results.json
    └── tts_latency_locust_results.json

../load_testing_test_samples/     # Test data (at parent directory)
├── asr/                          # Audio samples for ASR
├── nmt/                          # Text samples for NMT
└── tts/                          # Text samples for TTS
```

## Troubleshooting

### Issue: "No audio samples found" or "No NMT samples found"

**Solution**: Clear cached environment variables and restart your terminal:
```bash
unset AUDIO_SAMPLES_FILE NMT_SAMPLES_FILE TTS_SAMPLES_FILE
```

### Issue: Connection errors

**Solution**:
1. Verify your `AUTH_TOKEN` in the `.env` file is valid
2. Check network connectivity to `https://core-v1.ai4inclusion.org`
3. Ensure firewall/proxy settings allow HTTPS connections

### Issue: Locust not found

**Solution**: Make sure you've installed the requirements:
```bash
pip install -r requirements.txt
```

## Best Practices

1. **Start Small**: Begin with low user counts (5-10) and short durations
2. **Monitor Performance**: Watch response times and error rates in real-time
3. **Gradual Ramp-up**: Increase load gradually to find breaking points
4. **Document Results**: Save and compare results across test runs
5. **Clean Environment**: Clear environment variables before each test session

## Quick Start

```bash
# 1. Install dependencies
cd "/home/arun/Doc 2/Auto/Load_tesing_AI4I_Core"
pip install -r requirements.txt

# 2. Clear environment cache (if running previously)
unset AUDIO_SAMPLES_FILE NMT_SAMPLES_FILE TTS_SAMPLES_FILE

# 3. Run a load test
locust -f Load_testing_scripts/nmt_latency.py \
  --host=https://core-v1.ai4inclusion.org

# 4. Open browser to http://localhost:8089
```

## Support

For issues or questions:
- Check the detailed documentation in `load_testing_Readme/`
- Review the Locust documentation: https://docs.locust.io/
- Verify your `.env` configuration

## License

This project is part of the AI4Bharat initiative.
