# Non-Inference Metrics Guide

**Objective**: Measure API performance **excluding ML/GPU inference time** using Jaeger traces.

---

## 📋 Overview

This guide shows you how to:
1. Run an NMT load test
2. Analyze Jaeger traces to extract non-inference timing metrics
3. Get comprehensive statistics (Min, Max, Avg, Median, P95, P99) for non-ML overhead

**Why this matters**: You want to measure only the API/infrastructure overhead (auth, preprocessing, postprocessing) without the ML model inference time affecting your metrics.

---

## 🔧 Prerequisites

✅ Server-side Jaeger tracing is enabled
✅ Load test captures trace IDs in metrics JSON
✅ Python dependencies installed (`pip install -r requirements.txt`)

---

## 🚀 Step-by-Step Workflow

### Step 1: Run NMT Load Test

Run your load test as usual. The test will automatically capture trace IDs.

```bash
# Staging (default)
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py \
  --users 10 \
  --spawn-rate 1 \
  --run-time 30m \
  --headless

# Sandbox
ENV=sandbox locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py \
  --users 10 \
  --spawn-rate 1 \
  --run-time 30m \
  --headless
```

**What happens:**
- Load test runs for 30 minutes
- Each request's trace ID is captured
- Trace IDs are stored for:
  - All successful requests (up to 200)
  - All failed requests
  - Slow requests (>5s)
- At test end, metrics JSON is saved to: `testing/AI4I/logs/nmt_metrics_staging_{timestamp}.json`

---

### Step 2: Analyze Non-Inference Metrics

After the test completes, run the Jaeger analyzer:

```bash
# Staging
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_*.json \
  --env staging

# Sandbox
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_sandbox_*.json \
  --env sandbox
```

**What happens:**
- Analyzer reads the metrics JSON file
- Selects traces to analyze (prefers slow traces >5s, falls back to successful traces)
- Fetches trace data from Jaeger API for selected requests
- Calculates timing breakdown for each trace:
  - Total time
  - ML inference time
  - Non-inference time (Total - Inference)
- Aggregates statistics across all analyzed traces

---

### Step 3: Review Results

You'll see output like this:

```
================================================================================
JAEGER TRACE ANALYSIS - NON-INFERENCE TIMING METRICS
================================================================================
Load Test Summary:
  Total Requests: 1000
  Successful: 950 (95.00%)
  Failed: 50
  Duration: 1800.00s

📊 ANALYZING 100 TRACES FOR NON-INFERENCE METRICS...
Trace source: successful requests
--------------------------------------------------------------------------------

1. Trace: https://staging.ai4inclusion.org/traces?traceId=abc123...
   Total: 2450ms | Inference: 1850ms | Non-Inference: 600ms
   Top spans: ml.inference (1850ms), auth.validate_token (250ms), nmt.preprocess (150ms)

2. Trace: https://staging.ai4inclusion.org/traces?traceId=def456...
   Total: 3200ms | Inference: 2500ms | Non-Inference: 700ms
   Top spans: ml.inference (2500ms), auth.validate_token (280ms), nmt.preprocess (180ms)

[... more traces ...]

================================================================================
🎯 NON-INFERENCE TIMING METRICS (Excluding ML/GPU Time)
================================================================================
Sample Size: 100 requests

Metric               Total Time           Inference Time       Non-Inference Time
--------------------------------------------------------------------------------
Min                        1250.00ms               950.00ms               300.00ms
Max                        4500.00ms              3200.00ms              1300.00ms
Average                    2450.00ms              1850.00ms               600.00ms
Median                     2400.00ms              1800.00ms               580.00ms
P95                        3200.00ms              2500.00ms               850.00ms
P99                        3800.00ms              2900.00ms              1100.00ms
Std Dev                     520.00ms               380.00ms               140.00ms

================================================================================
📈 PERFORMANCE BREAKDOWN
================================================================================
Average Total Response Time:      2450.00ms
  ├─ ML Inference Time:            1850.00ms (75.5%)
  └─ Non-Inference Time (API):     600.00ms (24.5%)

💡 Non-inference overhead is 24.5% of total response time

================================================================================
📛 FAILED REQUESTS (5 traces)
================================================================================

🔍 Trace: https://staging.ai4inclusion.org/traces?traceId=xyz789...
   Status: 500 | Response Time: 2.34s
   Error: Connection timeout
   Breakdown: Total=2340ms, Inference=0ms, Non-Inference=2340ms
```

---

## 📊 Understanding the Metrics

### Non-Inference Timing Metrics

These are the key metrics you care about:

| Metric | What It Measures |
|--------|------------------|
| **Min** | Fastest non-inference time (best case API overhead) |
| **Max** | Slowest non-inference time (worst case API overhead) |
| **Average** | Typical non-inference time across requests |
| **Median** | Middle value (50th percentile) |
| **P95** | 95% of requests complete within this time |
| **P99** | 99% of requests complete within this time |
| **Std Dev** | Variation in non-inference times |

### Performance Breakdown

Shows you what percentage of total response time is:
- **ML Inference** (GPU/model processing) - What you want to exclude
- **Non-Inference** (API overhead) - What you want to measure

**Example Interpretation:**
```
Average Total Response Time:      2450.00ms
  ├─ ML Inference Time:            1850.00ms (75.5%)
  └─ Non-Inference Time (API):     600.00ms (24.5%)
```

This means:
- Total request takes 2.45 seconds on average
- 1.85 seconds (75.5%) is ML model processing
- **0.6 seconds (24.5%) is API overhead** ← This is what you're measuring!

---

## 🎯 Advanced Usage

### Analyze More Traces (Better Accuracy)

By default, the analyzer samples 100 slow traces. To analyze more:

```bash
# Analyze 200 traces
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_*.json \
  --sample-size 200
```

**Trade-off:**
- More traces = better statistical accuracy
- More traces = longer analysis time (API calls to Jaeger)

### Analyze Single Trace

To debug a specific slow request:

```bash
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --trace-id e6887e0d7ba9f00d00414608926747f7 \
  --env staging
```

Output:
```json
{
  "trace_id": "e6887e0d7ba9f00d00414608926747f7",
  "total_duration_ms": 2450,
  "inference_duration_ms": 1850,
  "non_inference_duration_ms": 600,
  "inference_percentage": 75.51,
  "non_inference_percentage": 24.49,
  "span_count": 12,
  "spans": [
    {"name": "ml.inference", "duration_ms": 1850},
    {"name": "auth.validate_token", "duration_ms": 250},
    {"name": "nmt.preprocess", "duration_ms": 150},
    ...
  ]
}
```

---

## 🔍 What the Analyzer Detects as "Inference"

The analyzer identifies ML inference spans by looking for these keywords in span names:

- `ml.inference`
- `model.predict`
- `inference`
- `gpu`

If your server uses different span names, the detection may not work correctly.

**To verify:**
1. Open a trace URL in Jaeger UI
2. Look at span names
3. Check if ML/GPU spans are labeled with one of the above keywords

---

## 🐛 Troubleshooting

### Issue: "No traces available for analysis"

**Cause:** No trace IDs were captured during the load test

**Solutions:**
1. Check that the server returns trace IDs in response headers (`X-Trace-Id` or `traceparent`)
2. Verify that `nmt_loadtesting.py` extracts trace IDs from response headers
3. Check that metrics JSON file contains `successful_traces`, `slow_traces`, or `failed_traces` arrays

**Note:** The analyzer automatically uses successful traces if no slow traces exist, so this issue should be rare.

---

### Issue: "ERROR: Trace not found in Jaeger"

**Cause:** Trace ID exists in metrics but not in Jaeger (race condition or trace expired)

**Solutions:**
1. Run analyzer immediately after test completes
2. Check Jaeger retention settings
3. Verify trace URL in browser manually

---

### Issue: "Non-inference time is 100%"

**Cause:** Analyzer didn't detect any ML inference spans

**Possible reasons:**
1. ML inference spans use different names (not `ml.inference`, `model.predict`, etc.)
2. Request failed before reaching ML layer
3. Server-side instrumentation issue

**Solution:**
- Open trace in Jaeger UI and check span names
- Update detection logic in `jaeger_analyzer.py:106` if needed

---

## 📁 Output Files

### Metrics JSON (Auto-generated by Load Test)
**Location:** `testing/AI4I/logs/nmt_metrics_staging_{timestamp}.json`

**Contents:**
```json
{
  "total_requests": 1000,
  "successful": 950,
  "failed": 50,
  "success_rate": "95.00%",
  "response_times": {...},
  "successful_traces": [
    {"trace_id": "...", "status_code": 200, "response_time": 2.45}
  ],
  "failed_traces": [
    {"trace_id": "...", "status_code": 500, "response_time": 2.34}
  ],
  "slow_traces": [
    {"trace_id": "...", "status_code": 200, "response_time": 8.92}
  ]
}
```

This file is the input for the analyzer.

---

## 🎯 Best Practices

### 1. Run Regular Analysis

After each significant load test:
```bash
# Quick analysis (default 100 traces)
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_*.json

# Comprehensive analysis (200 traces)
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_*.json \
  --sample-size 200
```

### 2. Compare Environments

```bash
# Test staging
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --run-time 30m --headless
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_*.json

# Test sandbox
ENV=sandbox locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --run-time 30m --headless
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_sandbox_*.json \
  --env sandbox
```

Compare non-inference P95/P99 between environments.

### 3. Monitor Trends Over Time

Save analyzer output for trend analysis:

```bash
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_*.json \
  > analysis_results_$(date +%Y%m%d_%H%M%S).txt
```

Then compare results week-over-week to detect performance regressions.

---

## 🔗 Related Documentation

- [JAEGER_CLIENT_INTEGRATION_GUIDE.md](JAEGER_CLIENT_INTEGRATION_GUIDE.md) - Overview of Jaeger integration
- [JAEGER_IMPLEMENTATION_GUIDE.md](JAEGER_IMPLEMENTATION_GUIDE.md) - Server-side setup reference
- [check_timing_headers.py](check_timing_headers.py) - Verify timing headers from API
- [../CLAUDE.md](../../../CLAUDE.md) - Full project documentation

---

## ⚡ Quick Reference

### Complete Workflow (Copy-Paste)

```bash
# 1. Run load test
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py \
  --users 10 --spawn-rate 1 --run-time 30m --headless

# 2. Wait for test to complete...

# 3. Analyze non-inference metrics
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_*.json \
  --env staging

# 4. Review the output for non-inference P95/P99
```

### Key Metrics to Report

When sharing results, focus on:

| Metric | Value | What It Means |
|--------|-------|---------------|
| Non-Inference P95 | 850ms | 95% of API overhead is ≤850ms |
| Non-Inference P99 | 1100ms | 99% of API overhead is ≤1100ms |
| Non-Inference Avg | 600ms | Average API overhead |
| Non-Inference % | 24.5% | API overhead as % of total time |

---

## 💡 Tips

1. **Run analyzer immediately** after test completes - traces may expire
2. **Use --headless** mode in Locust to avoid manual intervention
3. **Sample 100-200 traces** for good statistical accuracy
4. **Compare P95/P99** across test runs to detect regressions
5. **Save output** to files for historical comparison

---

## 🎉 Success Criteria

You'll know it's working when:
- ✅ Metrics JSON contains `successful_traces` (or `slow_traces`) with trace IDs
- ✅ Analyzer successfully fetches traces from Jaeger
- ✅ Non-inference metrics show reasonable times (100ms-2s typical)
- ✅ Performance breakdown shows inference vs non-inference split
- ✅ You can click trace URLs to see detailed breakdown in Jaeger UI
