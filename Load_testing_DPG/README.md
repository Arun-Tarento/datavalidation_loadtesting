# Load Testing for DPG - NMT Service

Load testing scripts for the DPG (Digital Public Goods) NMT service at http://13.204.164.186

## Setup

1. Install dependencies:
```bash
pip install locust python-dotenv
```

2. Configure `.env` file with your AUTH_TOKEN

## Running NMT Load Test

### Web UI Mode
```bash
locust -f Load_testing_DPG/load_testing_scripts/nmt_load_test.py --host=http://13.204.164.186
```
Open http://localhost:8089 in your browser

### Headless Mode
```bash
locust -f Load_testing_DPG/load_testing_scripts/nmt_load_test.py \
  --host=http://13.204.164.186 \
  --headless -u 10 -r 2 --run-time 60s
```

## Configuration

Edit `.env` to customize:
- `AUTH_TOKEN`: Your authentication token
- `NMT_SERVICE_ID`: ai4bharat/indictrans--gpu-t4
- `NMT_SOURCE_LANGUAGE`: Source language code (default: hi)
- `NMT_TARGET_LANGUAGE`: Target language code (default: ta)

## Results

Test results are saved to: `load_testing_results/nmt_load_test_results.json`
