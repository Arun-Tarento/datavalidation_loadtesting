# NMT Load Testing - Timing Breakdown Guide

This guide explains how to analyze and exclude inference time from your NMT load tests.

## Quick Start

### 1. Check what timing data the server provides

```bash
ENV=sandbox python testing/AI4I/loadtesting/NMT/check_timing_headers.py
```

This will show if the API returns headers like:
- `X-Inference-Time` - Time spent in ML model
- `Server-Timing` - Standard header with detailed breakdown
- `X-Processing-Time` - Total server processing time

### 2. Analyze timing breakdown (single request)

```bash
ENV=sandbox ./testing/AI4I/loadtesting/analyze_request_timing.sh
```

This uses `curl` to show detailed network-level timing:
- DNS lookup
- TCP connection establishment
- TLS handshake
- Request transmission
- **TTFB (Time To First Byte)** ← Total server processing
- Response download

### 3. Statistical analysis (multiple requests)

```bash
ENV=sandbox python testing/AI4I/loadtesting/visualize_timing.py --requests 100
```

This makes 100 requests and shows:
- Average, P95, max for each layer
- Breakdown of inference vs non-inference time
- Percentage distribution of where time is spent

### 4. Load test with detailed timing

```bash
ENV=sandbox locust -f testing/AI4I/loadtesting/nmt_loadtesting_with_timing.py \
  --users 10 --spawn-rate 1 --run-time 10m
```

This enhanced load test captures timing breakdowns and saves them to JSON.

---

## Understanding the Layers

### Client-Side Measurement (HTTP/Network Layer)

```
┌─────────────────────────────────────────────────────────────┐
│                    Total Request Time                        │
├──────────────┬──────────────────────────────────────────────┤
│   Network    │            Server Processing                  │
│   Overhead   │                                               │
│              │                                               │
│ DNS + TCP +  │         TTFB (Time To First Byte)            │
│ TLS + Send   │                                               │
└──────────────┴──────────────────────────────────────────────┘
```

**Network Overhead:**
- DNS lookup: Resolving domain name (cached after first request)
- TCP connection: 3-way handshake (reused with keep-alive)
- TLS handshake: SSL/TLS negotiation (reused with keep-alive)
- Request send: Transmitting HTTP request

**TTFB (Time To First Byte):**
- Total server processing time
- Includes everything the server does before sending response
- This is what you want to break down further

### Server-Side Breakdown (If API Provides Headers)

```
┌─────────────────────────────────────────────────────────────┐
│              TTFB (Total Server Processing)                  │
├──────────────┬─────────────────┬──────────────┬─────────────┤
│ Auth/        │  Pre-           │  Inference   │ Post-        │
│ Validation   │  Processing     │  (ML Model)  │ Processing   │
└──────────────┴─────────────────┴──────────────┴─────────────┘
```

**What you want to measure (excluding inference):**
- Auth/Validation: Token verification, rate limiting checks
- Pre-processing: Input validation, text normalization
- Post-processing: Result formatting, response construction

**What you want to exclude:**
- Inference: Actual ML model execution time

---

## Calculation Methods

### If Server Provides `X-Inference-Time` Header

```python
# From a single request:
total_time = time.perf_counter() measurement
ttfb = response.elapsed.total_seconds()
inference_time = float(response.headers['X-Inference-Time'])  # May be in ms or seconds

network_overhead = total_time - ttfb
non_inference_server = ttfb - inference_time

# Time excluding inference:
time_without_inference = network_overhead + non_inference_server
```

### If Server DOES NOT Provide Timing Headers

You can only measure:
- **Total response time** (client-side)
- **TTFB** (server processing)
- **Network overhead** (total - TTFB)

In this case, you cannot separate inference from other server processing.

**Workaround:**
1. Contact the API team to add `X-Inference-Time` header
2. Or use APM tools (if you have backend access)
3. Or estimate based on known model performance

---

## Example Scenarios

### Scenario 1: Server provides inference time header

```bash
$ ENV=sandbox ./testing/AI4I/loadtesting/analyze_request_timing.sh

TIMING BREAKDOWN:
  DNS Lookup:        0.005s
  TCP Connection:    0.120s
  TLS Handshake:     0.285s
  TTFB (Server):     2.450s  ← Total server processing
  Total Time:        2.455s

RESPONSE HEADERS:
  X-Inference-Time: 2100  ← Inference took 2.1 seconds

CALCULATION:
  Network overhead:     0.285s (DNS + TCP + TLS)
  Server processing:    2.450s (TTFB)
    ├─ Inference:       2.100s (from header)
    └─ Non-inference:   0.350s (auth + validation + pre/post)

  Time without inference: 0.285s + 0.350s = 0.635s
```

### Scenario 2: Server does NOT provide inference time

```bash
$ ENV=sandbox ./testing/AI4I/loadtesting/analyze_request_timing.sh

TIMING BREAKDOWN:
  TTFB (Server):     2.450s  ← Server processing (can't break down further)
  Total Time:        2.455s

(no timing headers found)

RESULT: You can only measure total TTFB, not individual components
```

---

## Modifying Load Test to Exclude Inference

### Option 1: Use the enhanced load test

The file `nmt_loadtesting_with_timing.py` automatically:
- Captures server timing headers (if available)
- Calculates non-inference time
- Reports breakdown in test summary
- Saves detailed metrics to JSON

### Option 2: Modify metrics to subtract inference

If your server provides `X-Inference-Time`, modify the load test:

```python
# In nmt_loadtesting.py, after line 160:

# Parse server timing headers
inference_time = None
if 'X-Inference-Time' in response.headers:
    try:
        # Convert to seconds if needed
        inference_time = float(response.headers['X-Inference-Time'])
        if inference_time > 50:  # Likely milliseconds
            inference_time /= 1000
    except ValueError:
        pass

# Calculate time without inference
elapsed_without_inference = elapsed
if inference_time:
    elapsed_without_inference = elapsed - inference_time

# Record both metrics
metrics.record_request(status_code, elapsed)  # Original
metrics.record_request_no_inference(status_code, elapsed_without_inference)  # New
```

### Option 3: Focus analysis on specific percentiles

When analyzing results, calculate:

```python
# If you know average inference time is ~2s:
estimated_inference = 2.0
non_inference_times = [t - estimated_inference for t in response_times]

# Then analyze non_inference_times for bottlenecks
```

---

## Recommended Workflow

1. **First, discover what timing data is available:**
   ```bash
   ENV=sandbox python testing/AI4I/loadtesting/NMT/check_timing_headers.py
   ```

2. **Understand the baseline with statistical analysis:**
   ```bash
   ENV=sandbox python testing/AI4I/loadtesting/visualize_timing.py --requests 100
   ```

   This shows you:
   - What percentage of time is inference vs non-inference
   - Whether you should even bother excluding it (if inference is 95% of time, other layers are negligible)

3. **Run load tests with detailed timing:**
   ```bash
   ENV=sandbox locust -f testing/AI4I/loadtesting/nmt_loadtesting_with_timing.py \
     --users 10 --spawn-rate 1 --run-time 30m --headless
   ```

4. **Analyze saved JSON metrics:**
   ```bash
   cat testing/AI4I/logs/nmt_timing_breakdown_sandbox_*.json | jq
   ```

---

## Key Metrics to Track

For load testing **excluding inference**, focus on:

1. **Network latency** (should be consistent)
   - If this varies widely, indicates network issues

2. **Non-inference server time** (auth, validation, pre/post-processing)
   - Should scale linearly with load
   - If this increases with more users, indicates server bottleneck

3. **Connection reuse**
   - First request: High (DNS + TCP + TLS)
   - Subsequent: Low (connection reused)

4. **Rate limiting overhead**
   - Token refresh frequency
   - Auth validation time

---

## Troubleshooting

### "No timing headers found"

The API doesn't expose internal timing. Solutions:
1. Request the backend team to add `Server-Timing` or `X-Inference-Time` headers
2. Use only client-side TTFB measurement (includes all server processing)
3. Use APM tools if you have backend access (New Relic, DataDog, etc.)

### "Inference time seems wrong (too high or low)"

Check units:
- Could be in milliseconds (typically 500-5000ms)
- Could be in seconds (typically 0.5-5s)
- The script auto-detects if value > 50 (assumes ms)

### "Want to measure GPU vs CPU time"

This requires:
- Backend instrumentation (can't measure from client)
- APM tools with GPU monitoring
- Or custom logging in the inference service

---

## Files Created

| File | Purpose |
|------|---------|
| `check_timing_headers.py` | One-shot test to see what headers server returns |
| `analyze_request_timing.sh` | Detailed curl-based timing for single request |
| `visualize_timing.py` | Statistical analysis across multiple requests |
| `nmt_loadtesting_with_timing.py` | Enhanced load test with timing breakdowns |
| `TIMING_ANALYSIS_GUIDE.md` | This guide |

---

## Next Steps

1. Run `check_timing_headers.py` to see what data your API provides
2. Run `visualize_timing.py` to understand the breakdown
3. Decide if you need to exclude inference:
   - If inference is > 90% of time: Other layers are negligible anyway
   - If inference is < 50% of time: Worth analyzing non-inference components
4. Use `nmt_loadtesting_with_timing.py` for detailed load testing
