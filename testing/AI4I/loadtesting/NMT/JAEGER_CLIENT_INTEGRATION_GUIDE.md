# Jaeger Client Integration Guide

Now that server-side Jaeger tracing is implemented, this guide shows you how to **leverage it in your load tests**.

## 🎯 What's Been Done

✅ **Server-side Jaeger is live**
- Traces accessible at: `https://staging.ai4inclusion.org/traces?traceId={trace_id}`
- Example: https://staging.ai4inclusion.org/traces?traceId=e6887e0d7ba9f00d00414608926747f7

✅ **Client-side integration added**
- Load tests now extract trace IDs from response headers
- Failed requests log their trace URLs automatically
- Slow requests (>5s) are tracked with trace IDs
- Metrics JSON includes trace IDs for debugging

## 📊 How It Works Now

### 1. Running Load Tests (Same as Before)

```bash
# Run NMT load test on staging
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 30m

# Run on sandbox
ENV=sandbox locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 30m
```

### 2. What's New in the Logs

**Before:**
```
NMT failed: 500 (2.34s)
```

**After:**
```
NMT failed: 500 (2.34s) trace=https://staging.ai4inclusion.org/traces?traceId=abc123...
```

Now you can **click the trace URL** and see exactly what happened inside the server!

### 3. Metrics JSON Now Includes Trace IDs

After test completes, check `testing/AI4I/logs/nmt_metrics_staging_{timestamp}.json`:

```json
{
  "total_requests": 1000,
  "successful": 950,
  "failed": 50,
  "failed_traces": [
    {
      "trace_id": "abc123...",
      "status_code": 500,
      "response_time": 2.34,
      "error": "Connection timeout"
    }
  ],
  "slow_traces": [
    {
      "trace_id": "def456...",
      "status_code": 200,
      "response_time": 8.92
    }
  ]
}
```

## 🔍 Analyzing Traces

### Option 1: Manual Analysis (Jaeger UI)

1. **Run load test**
   ```bash
   locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 10m
   ```

2. **Check logs for failed/slow requests**
   ```
   grep "trace=" locust.log | grep "failed\|slow"
   ```

3. **Open trace URL in browser**
   ```
   https://staging.ai4inclusion.org/traces?traceId=e6887e0d7ba9f00d00414608926747f7
   ```

4. **Analyze timing breakdown in Jaeger UI**
   - See span timeline
   - Identify which spans are slow (auth, validation, inference, postprocessing)
   - Separate ML inference time from other processing

### Option 2: Automated Analysis (Python Script)

Use the new `jaeger_analyzer.py` utility:

#### Analyze Single Trace
```bash
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --trace-id e6887e0d7ba9f00d00414608926747f7 \
  --env staging
```

**Output:**
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
    {"name": "nmt.postprocess", "duration_ms": 100}
  ]
}
```

#### Analyze Entire Load Test
```bash
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_1770898352.json \
  --env staging
```

**Output:**
```
================================================================================
JAEGER TRACE ANALYSIS
================================================================================

📛 FAILED REQUESTS (5 traces)
--------------------------------------------------------------------------------

🔍 Trace: https://staging.ai4inclusion.org/traces?traceId=abc123...
   Status: 500 | Response Time: 2.34s
   Total: 2340ms | Inference: 0ms (0%) | Non-Inference: 2340ms (100%)

🐌 SLOW REQUESTS (15 traces)
--------------------------------------------------------------------------------

🔍 Trace: https://staging.ai4inclusion.org/traces?traceId=def456...
   Status: 200 | Response Time: 8.92s
   Total: 8920ms | Inference: 6500ms (72.88%) | Non-Inference: 2420ms (27.12%)
   Top spans:
     - ml.inference: 6500ms
     - auth.validate_token: 1200ms
     - nmt.preprocess: 800ms
     - db.query: 250ms
     - nmt.postprocess: 170ms

📊 NON-INFERENCE TIMING STATISTICS
--------------------------------------------------------------------------------
   Min:    450ms
   Max:    2420ms
   Avg:    1250ms
   Median: 1100ms
   StdDev: 520ms
```

## 🎯 Key Use Cases

### 1. Debug Failed Requests
```bash
# Run test
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 50 --spawn-rate 5 --run-time 30m

# Check for failures in logs
grep "NMT failed" locust.log

# Click trace URL to see exact failure point in Jaeger UI
```

### 2. Analyze Slow Requests
```bash
# After test completes, analyze slow traces
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_*.json
```

This shows you:
- Which requests were slow (>5s)
- How much time was ML inference vs other processing
- Which specific spans caused delays (auth, validation, preprocessing, etc.)

### 3. Compare Environments
```bash
# Run on staging
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --run-time 10m
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_*.json

# Run on sandbox
ENV=sandbox locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --run-time 10m
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_sandbox_*.json \
  --env sandbox
```

Compare non-inference timings between environments.

## 📝 Understanding Trace Data

### Example Jaeger Trace Breakdown

```
Request Timeline (2.45s total):
┌────────────────────────────────────────────────────────────┐
│ HTTP Request                                       [2450ms]│
│  ├─ auth.validate_token                            [250ms]│ ← Auth overhead
│  ├─ middleware.rate_limit                           [50ms]│ ← Rate limiting check
│  ├─ nmt.validate_input                              [80ms]│ ← Input validation
│  ├─ nmt.preprocess                                 [150ms]│ ← Text preprocessing
│  ├─ ml.inference                                  [1850ms]│ ← ML MODEL (exclude this)
│  ├─ nmt.postprocess                                [100ms]│ ← Postprocessing
│  └─ response.serialize                              [20ms]│ ← JSON serialization
└────────────────────────────────────────────────────────────┘

Total:          2450ms
Inference:      1850ms (75.5%)  ← Time spent in ML model
Non-Inference:   600ms (24.5%)  ← API overhead (auth, preprocessing, etc.)
```

### What to Look For

**🟢 Good Non-Inference Times:**
- Auth: 50-100ms
- Preprocessing: 50-200ms
- Postprocessing: 20-100ms
- **Total non-inference: <500ms**

**🔴 Red Flags:**
- Auth >500ms → Token validation slow, check Redis/DB
- Preprocessing >1s → Text normalization bottleneck
- Rate limiting >100ms → Rate limiter misconfigured
- DB queries >500ms → Database performance issue

## 🚀 Next Steps

### 1. Integrate into ASR and TTS Load Tests

Apply the same pattern to other services:

```bash
# Update asr_loadtesting.py
# Update tts_loadtesting.py
```

Same changes needed:
1. Extract trace ID from response headers
2. Pass `trace_id` to `metrics.record_request()`
3. Log trace URLs for failures

### 2. Create Dashboards (Future)

Export Jaeger metrics to Grafana for real-time monitoring:
- Non-inference P95/P99 over time
- Slow span detection
- Failure rate by span

### 3. Add Custom Trace Attributes (Future)

In server code, add more context to spans:

```python
span.set_attribute("user.id", user_id)
span.set_attribute("input.length", len(input_text))
span.set_attribute("model.version", "v2.3")
```

Then filter in Jaeger:
```
service=ai4i-nmt-api AND user.id=test_user_1
```

## ❓ FAQ

**Q: How do I know if the server is returning trace IDs?**

Check response headers:
```bash
curl -I https://staging.ai4inclusion.org/api/v1/nmt/inference \
  -H "Authorization: Bearer $TOKEN" | grep -i trace
```

Look for:
- `X-Trace-Id: abc123...`
- `traceparent: 00-abc123...-def456...-01`

**Q: What if trace ID is not in response?**

The server might use W3C Trace Context (`traceparent` header) instead of `X-Trace-Id`. The code handles both:
```python
trace_id = response.headers.get("X-Trace-Id") or \
           response.headers.get("traceparent", "").split("-")[1]
```

**Q: Can I generate my own trace IDs?**

Yes! Send a custom trace ID in request:
```python
headers = {
    "Authorization": f"Bearer {token}",
    "X-Trace-Id": "my-custom-trace-id-123"
}
```

The server should propagate it through all spans.

**Q: How many traces should I analyze?**

- **For debugging:** Analyze all failed traces
- **For performance:** Analyze top 10-20 slowest traces
- **For patterns:** Analyze random sample of 100 traces

**Q: Can I query Jaeger programmatically?**

Yes! The `jaeger_analyzer.py` script uses the Jaeger API:
```
GET https://staging.ai4inclusion.org/api/traces/{trace_id}
```

You can extend it to query by service, operation, tags, etc.

## 📚 Resources

- [W3C Trace Context Spec](https://www.w3.org/TR/trace-context/)
- [Jaeger Query API Docs](https://www.jaegertracing.io/docs/latest/apis/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

## 🎉 Benefits You Now Have

✅ **Instant failure debugging** - Click trace URL in logs to see exact error location
✅ **Performance bottleneck identification** - See which layers are slow (auth, preprocessing, inference)
✅ **Non-inference metrics** - Separate API overhead from ML model time
✅ **Automated analysis** - Run `jaeger_analyzer.py` on metrics files
✅ **Historical tracking** - All traces stored with timestamps and metadata
