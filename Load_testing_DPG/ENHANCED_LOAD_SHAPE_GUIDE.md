# Enhanced Load Shape Testing Guide

## 🎯 What's New?

The **enhanced load shape tests** capture detailed per-stage metrics to give you deep insights into:
- ✅ **Error rates** at each load level
- ✅ **Latency breakdown** (min, max, median, avg, P95, P99) per stage
- ✅ **Payload sizes** per stage
- ✅ **Throughput** (requests/second) per stage
- ✅ **Breaking point detection** - Automatic identification of where server fails
- ✅ **Capacity recommendations** - Automated suggestions for production limits

---

## 📊 Sample JSON Output Structure

```json
{
  "test_info": {
    "test_type": "load_shaping",
    "service": "NMT (Translation)",
    "test_date": "2025-01-17T14:30:00",
    "total_duration_seconds": 1080
  },
  "test_config": {
    "service_id": "ai4bharat/indictrans--gpu-t4",
    "source_language": "hi",
    "target_language": "ta"
  },
  "overall_statistics": {
    "total_requests": 2450,
    "failed_requests": 234,
    "success_rate_percentage": 90.45,
    "error_rate_percentage": 9.55,
    "overall_latency_ms": {
      "min": 145.2,
      "max": 45230.8,
      "median": 3456.7,
      "average": 5234.5,
      "p95": 12345.6,
      "p99": 23456.7
    }
  },
  "stage_by_stage_metrics": {
    "Stage 1: Warm-up (10 users)": {
      "duration_seconds": 120,
      "start_time": "2025-01-17T14:30:00",
      "end_time": "2025-01-17T14:32:00",
      "requests": {
        "total": 234,
        "successful": 234,
        "failed": 0,
        "success_rate_percentage": 100.0,
        "error_rate_percentage": 0.0
      },
      "latency_ms": {
        "min": 145.2,
        "max": 3456.7,
        "median": 2345.6,
        "average": 2456.8,
        "p95": 3123.4,
        "p99": 3345.6
      },
      "throughput": {
        "requests_per_second": 1.95,
        "average_content_size_bytes": 1234.5
      }
    },
    "Stage 2: Baseline (10 users)": {
      "duration_seconds": 120,
      "requests": {
        "total": 245,
        "successful": 245,
        "failed": 0,
        "success_rate_percentage": 100.0,
        "error_rate_percentage": 0.0
      },
      "latency_ms": {
        "min": 152.3,
        "max": 3678.9,
        "median": 2456.7,
        "average": 2567.8,
        "p95": 3234.5,
        "p99": 3456.7
      },
      "throughput": {
        "requests_per_second": 2.04,
        "average_content_size_bytes": 1245.6
      }
    },
    "Stage 3: Light Stress (20 users)": {
      "duration_seconds": 180,
      "requests": {
        "total": 478,
        "successful": 476,
        "failed": 2,
        "success_rate_percentage": 99.58,
        "error_rate_percentage": 0.42
      },
      "latency_ms": {
        "min": 178.9,
        "max": 5678.9,
        "median": 3456.7,
        "average": 3678.9,
        "p95": 4567.8,
        "p99": 5234.5
      },
      "throughput": {
        "requests_per_second": 2.66,
        "average_content_size_bytes": 1267.8
      }
    },
    "Stage 5: Heavy Stress (40 users)": {
      "duration_seconds": 120,
      "requests": {
        "total": 456,
        "successful": 398,
        "failed": 58,
        "success_rate_percentage": 87.28,
        "error_rate_percentage": 12.72
      },
      "latency_ms": {
        "min": 234.5,
        "max": 25678.9,
        "median": 8956.7,
        "average": 10234.5,
        "p95": 18567.8,
        "p99": 22345.6
      },
      "throughput": {
        "requests_per_second": 3.80,
        "average_content_size_bytes": 1289.4
      }
    },
    "Stage 7: Breaking Point (60 users)": {
      "duration_seconds": 120,
      "requests": {
        "total": 423,
        "successful": 248,
        "failed": 175,
        "success_rate_percentage": 58.63,
        "error_rate_percentage": 41.37
      },
      "latency_ms": {
        "min": 345.6,
        "max": 45230.8,
        "median": 15678.9,
        "average": 18234.5,
        "p95": 35678.9,
        "p99": 42345.6
      },
      "throughput": {
        "requests_per_second": 3.53,
        "average_content_size_bytes": 1234.5
      }
    }
  },
  "capacity_analysis": {
    "healthy_stages": [
      {
        "stage": "Stage 1: Warm-up (10 users)",
        "error_rate": 0.0,
        "avg_latency_ms": 2456.8,
        "p95_latency_ms": 3123.4
      },
      {
        "stage": "Stage 2: Baseline (10 users)",
        "error_rate": 0.0,
        "avg_latency_ms": 2567.8,
        "p95_latency_ms": 3234.5
      },
      {
        "stage": "Stage 3: Light Stress (20 users)",
        "error_rate": 0.42,
        "avg_latency_ms": 3678.9,
        "p95_latency_ms": 4567.8
      }
    ],
    "degraded_stages": [
      {
        "stage": "Stage 5: Heavy Stress (40 users)",
        "error_rate": 12.72,
        "avg_latency_ms": 10234.5,
        "p95_latency_ms": 18567.8
      }
    ],
    "failed_stages": [
      {
        "stage": "Stage 7: Breaking Point (60 users)",
        "error_rate": 41.37,
        "avg_latency_ms": 18234.5,
        "p95_latency_ms": 35678.9
      }
    ],
    "breaking_point": "Stage 5: Heavy Stress (40 users)",
    "max_healthy_capacity": 20
  },
  "recommendations": {
    "production_capacity": "14 concurrent users (70% of max tested: 20)",
    "scaling_needed": false,
    "optimization_priority": [
      "System performing well within tested range"
    ],
    "action_items": [
      "Set production max concurrent users to 14"
    ]
  }
}
```

---

## 🚀 How to Run

### For NMT (Translation):
```bash
locust -f Load_testing_DPG/load_testing_scripts/nmt_load_shape_test_enhanced.py \
       --host=http://13.204.164.186
```

### For ASR (Speech Recognition):
```bash
locust -f Load_testing_DPG/load_testing_scripts/asr_load_shape_test_enhanced.py \
       --host=http://13.204.164.186:8000
```

Then:
1. Open http://localhost:8089
2. Click "Start Swarming"
3. Watch the test run automatically through all stages

---

## 📈 What You'll See During the Test

### Real-time Console Output

```
======================================================================
🔄 Stage 1: Warm-up (10 users)
Time: 0s | Target Users: 10 | Spawn Rate: 1/s
======================================================================

... test running ...

──────────────────────────────────────────────────────────────────────
📊 Stage 1: Warm-up (10 users) - COMPLETED
Duration: 120s | Requests: 234 | Failures: 0
Success Rate: 100.00% | Error Rate: 0.00%
Latency - Avg: 2457ms | P95: 3123ms | P99: 3346ms
Throughput: 1.95 req/s
──────────────────────────────────────────────────────────────────────

======================================================================
🔄 Stage 2: Baseline (10 users)
Time: 120s | Target Users: 10 | Spawn Rate: 1/s
======================================================================

... and so on for each stage ...
```

### Final Summary

```
======================================================================
📊 NMT LOAD SHAPE TEST COMPLETED
======================================================================

🔍 OVERALL TEST SUMMARY:
Total Requests: 2450
Total Failures: 234
Overall Success Rate: 90.45%
Overall Error Rate: 9.55%

🎯 CAPACITY ANALYSIS:
Breaking Point: Stage 5: Heavy Stress (40 users)
Max Healthy Load: ~20 concurrent users
Recommendation: Run production with max 14 users

======================================================================

✅ Detailed results saved to: Load_testing_DPG/load_testing_results/nmt_load_shape_results_20250117_143000.json

📊 Key Findings:
   Max Healthy Capacity: 20 concurrent users
   Breaking Point: Stage 5: Heavy Stress (40 users)
   Recommended Production Capacity: 14 concurrent users (70% of max tested: 20)
```

---

## 🔍 Understanding the Results

### Stage Classification

The test automatically classifies each stage into:

| Classification | Criteria | What It Means |
|----------------|----------|---------------|
| **Healthy** | Error rate < 1% AND P95 latency < 5s | Server handling load well |
| **Degraded** | Error rate 1-10% OR P95 latency 5-15s | Server struggling but functional |
| **Failed** | Error rate > 10% OR P95 latency > 15s | Server overloaded, unacceptable performance |

### Capacity Metrics

```
max_healthy_capacity: The highest user count with healthy performance
breaking_point: First stage where server degrades
production_capacity: Recommended limit (70% of max for safety margin)
```

### Example Interpretation

```json
{
  "max_healthy_capacity": 20,
  "breaking_point": "Stage 5: Heavy Stress (40 users)",
  "production_capacity": "14 concurrent users"
}
```

**Translation:**
- ✅ Server works perfectly up to 20 users
- ⚠️ Starts degrading at 40 users
- 🎯 **Recommendation:** Limit production to 14 users (30% headroom for spikes)

---

## 📊 Key Metrics Explained

### Error Rate per Stage

```
Stage 1 (10 users):  0.00%  ✅ Perfect
Stage 2 (10 users):  0.00%  ✅ Perfect
Stage 3 (20 users):  0.42%  ✅ Healthy (< 1%)
Stage 4 (20 users):  1.25%  ⚠️ Warning (1-10%)
Stage 5 (40 users):  12.72% ❌ Failing (> 10%)
Stage 7 (60 users):  41.37% ❌ Critical (> 40%)
```

**Insight:** Server capacity is ~20 users

### Latency Trends per Stage

```
Stage         Avg Latency    P95 Latency    P99 Latency
Stage 1:      2.5s          3.1s           3.3s         ✅
Stage 2:      2.6s          3.2s           3.5s         ✅
Stage 3:      3.7s          4.6s           5.2s         ✅
Stage 4:      6.8s          9.2s           11.5s        ⚠️
Stage 5:      10.2s         18.6s          22.3s        ❌
Stage 7:      18.2s         35.7s          42.3s        ❌
```

**Insight:** Latency spikes at 40 users → Breaking point

### Throughput per Stage

```
Stage         RPS     Trend
Stage 1:      1.95    ──
Stage 2:      2.04    ──
Stage 3:      2.66    ╱
Stage 4:      3.12    ╱
Stage 5:      3.80    ╱  ← Peak throughput
Stage 7:      3.53    ╲  ← Declining (overload!)
```

**Insight:** Throughput peaks at 40 users, then drops → Server saturated

---

## 🎯 Production Recommendations

### Based on Test Results

If your test shows:
```
Max Healthy Capacity: 20 users
```

**Set production limits:**
```
1. Max concurrent users: 14-16 (70-80% of max)
2. Alert threshold: 12 users (60%)
3. Scale-up trigger: 16 users (80%)
```

### Monitoring Setup

```yaml
alerts:
  - name: "Approaching Capacity"
    condition: "active_users > 12"
    action: "Send warning, prepare to scale"

  - name: "At Capacity"
    condition: "active_users > 16"
    action: "Auto-scale or rate limit"

  - name: "Over Capacity"
    condition: "active_users > 20"
    action: "URGENT: Rate limit, shed load"
```

---

## 🔧 Customizing the Test

### Change Load Stages

Edit the `stages` list in the test file:

```python
stages = [
    # Add your own stages
    {"duration": 60, "users": 5, "spawn_rate": 1, "name": "Stage 1: Very Light"},
    {"duration": 120, "users": 5, "spawn_rate": 1, "name": "Stage 1 Hold"},
    {"duration": 180, "users": 10, "spawn_rate": 1, "name": "Stage 2: Light"},
    # ... customize as needed
]
```

### Adjust Health Thresholds

Modify in the `analyze_capacity()` function:

```python
# Current thresholds
is_healthy = error_rate < 5 and avg_latency < 5000  # <5% errors, <5s latency

# For stricter requirements
is_healthy = error_rate < 1 and avg_latency < 3000  # <1% errors, <3s latency

# For more lenient requirements
is_healthy = error_rate < 10 and avg_latency < 10000  # <10% errors, <10s latency
```

---

## 📁 Output Files

Results are saved with timestamps:

```
Load_testing_DPG/load_testing_results/
├── nmt_load_shape_results_20250117_143000.json
├── nmt_load_shape_results_20250117_150000.json
├── asr_load_shape_results_20250117_143000.json
└── asr_load_shape_results_20250117_150000.json
```

Each file contains complete metrics for all stages.

---

## 🚨 Important: Before Running

### 1. Disable Retries

Edit `nmt_test.py` and `asr_test.py` (line ~62):

```python
# Set to 0 for accurate results
retry_strategy = TrackedRetry(
    total=0,  # ← IMPORTANT: Disable retries!
```

### 2. Clear Grafana Dashboards

Reset dashboards to see fresh data for this test.

### 3. Ensure Server Health

Server should be in a known good state before testing.

---

## 💡 Pro Tips

### Tip 1: Compare Tests

Run multiple tests and compare JSON outputs to see:
- Performance improvements after optimization
- Impact of configuration changes
- Stability over time

### Tip 2: Correlate with Grafana

Match timestamps from JSON with Grafana to see:
- CPU/Memory usage at each stage
- Database connection pool at breaking point
- Network I/O patterns

### Tip 3: Use Different Shapes

For weak servers, create a custom conservative shape:
```python
stages = [
    {"duration": 120, "users": 2, "spawn_rate": 1, "name": "Stage 1"},
    {"duration": 240, "users": 5, "spawn_rate": 1, "name": "Stage 2"},
    {"duration": 360, "users": 10, "spawn_rate": 1, "name": "Stage 3"},
]
```

---

## 📊 Analyzing Multiple Runs

### Compare Performance Over Time

```bash
# Run test 1 (baseline)
locust -f nmt_load_shape_test_enhanced.py --host=...
# Results: nmt_load_shape_results_20250117_100000.json

# Make optimizations...

# Run test 2 (after optimization)
locust -f nmt_load_shape_test_enhanced.py --host=...
# Results: nmt_load_shape_results_20250117_140000.json

# Compare:
# - Max healthy capacity: 20 → 35 users (75% improvement!)
# - Breaking point: 40 → 60 users
# - P95 latency at 20 users: 4.5s → 2.8s (38% faster!)
```

---

## 🎓 Next Steps

After running enhanced load shape tests:

1. **✅ Document findings** - Save the JSON, note the breaking point
2. **✅ Set production limits** - Use the recommended capacity
3. **✅ Configure monitoring** - Set up alerts at 60%, 80% capacity
4. **✅ Plan scaling** - Know when to add resources
5. **✅ Optimize bottlenecks** - Focus on stages that degraded
6. **✅ Re-test** - Verify improvements with another test

---

**Happy Load Testing!** 🚀

For questions, check the main LOAD_SHAPING_GUIDE.md or review the JSON output.
