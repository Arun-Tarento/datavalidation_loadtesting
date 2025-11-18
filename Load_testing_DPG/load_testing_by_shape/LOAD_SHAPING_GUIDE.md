# Load Shaping Guide - Find Your Server's Capacity

## What is Load Shaping?

Load shaping gradually increases load to find where your server breaks, instead of immediately hitting it with maximum load.

```
Traditional Test:          Load Shaping:
═══════════════            ═══════════════

Users                      Users
  │                          │
50│█████████████           50│         ┌─────
  │█████████████             │        ╱
40│█████████████           40│      ╱
  │█████████████             │     ╱
30│█████████████           30│   ╱
  │█████████████             │  ╱
20│█████████████           20│ ╱
  │█████████████             │╱
10│█████████████           10│
  │                          │
 0└──────────────          0└──────────────────
   Time                       Time

Result: Server dies        Result: Find exact
        immediately                breaking point
```

## Three Load Shapes Available

### 1. **StagesShape** (Default - RECOMMENDED)
**Duration:** 18 minutes
**Best for:** Normal capacity testing
**Pattern:**
```
Users
  60│                   ┌─────┐
    │                  ╱       ╲
  40│           ┌─────┘         ╲
    │          ╱                  ╲
  20│    ┌────┘                    ╲
    │   ╱                           ╲
  10│──┘                             └─
    │
   0└─────────────────────────────────
     0  2  4  6  8 10 12 14 16 18 min

Stages:
├─ 0-2min:  Warm up to 10 users
├─ 2-4min:  Hold at 10 users (baseline)
├─ 4-7min:  Ramp to 20 users (light stress)
├─ 7-9min:  Hold at 20 users
├─ 9-11min: Ramp to 40 users (heavy stress)
├─ 11-13min: Hold at 40 users
├─ 13-15min: Ramp to 60 users (breaking point)
├─ 15-17min: Hold at 60 users (observe failure)
└─ 17-18min: Cool down to 10 users
```

### 2. **ConservativeShape**
**Duration:** 15 minutes
**Best for:** Weak/struggling servers
**Pattern:**
```
Users
  20│                         ┌────
    │                        ╱
  15│                  ┌────┘
    │                 ╱
  10│           ┌────┘
    │          ╱
   5│    ┌───┘
    │   ╱
   2│──┘
    │
   0└──────────────────────────────
     0  2  4  6  8  10 12 14 min

Stages:
├─ 0-3min:  Ramp to 2 users, hold
├─ 3-6min:  Ramp to 5 users, hold
├─ 6-9min:  Ramp to 10 users, hold
├─ 9-12min: Ramp to 15 users, hold
└─ 12-15min: Ramp to 20 users, hold

Very slow, find exact capacity!
```

### 3. **AggressiveShape**
**Duration:** 10 minutes
**Best for:** Quick capacity finding
**Pattern:**
```
Users
 100│               ┌─────
    │              ╱
  50│        ┌────┘
    │       ╱
  25│   ┌──┘
    │  ╱
  10│─┘
    │
   0└──────────────────
     0  2  4  6  8 10 min

Stages:
├─ 0-2.5min: Ramp to 10, hold
├─ 2.5-5min: Ramp to 25, hold
├─ 5-7.5min: Ramp to 50, hold
└─ 7.5-10min: Ramp to 100, hold

Fast testing, find limits quickly!
```

## How to Use

### Step 1: Choose Your Shape

**If your server is:**
- ✅ **Healthy/Unknown:** Use `StagesShape` (default)
- 🐌 **Weak/Struggling:** Use `ConservativeShape`
- ⚡ **Need quick results:** Use `AggressiveShape`

### Step 2: Edit the Script (Optional)

To change shapes, edit the load shape file:

```python
# In asr_load_shape_test.py or nmt_load_shape_test.py
# Line ~160

# Option 1: Default (recommended)
class CustomLoadShape(StagesShape):
    pass

# Option 2: For weak servers
# class CustomLoadShape(ConservativeShape):
#     pass

# Option 3: For quick testing
# class CustomLoadShape(AggressiveShape):
#     pass
```

### Step 3: Run the Test

**For NMT:**
```bash
locust -f Load_testing_DPG/load_testing_scripts/nmt_load_shape_test.py \
       --host=http://13.204.164.186
```

**For ASR:**
```bash
locust -f Load_testing_DPG/load_testing_scripts/asr_load_shape_test.py \
       --host=http://13.204.164.186:8000
```

### Step 4: Open Web UI

1. Open browser: http://localhost:8089
2. Click "Start Swarming"
3. **DO NOT** specify users or spawn rate (load shape controls this!)
4. Watch the test run automatically

## What to Watch For

### During the Test

Monitor these metrics in **real-time**:

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| **Response Time (P95)** | <5s | 5-15s | >15s |
| **Error Rate** | <1% | 1-5% | >5% |
| **Requests/sec** | Increasing steadily | Plateauing | Decreasing |
| **Active Users** | Matching stage | - | - |

### In Grafana

Watch these during the test:

```
1. CPU Usage
   ├─ <70% = Good
   ├─ 70-90% = Warning
   └─ >90% = Critical

2. Memory Usage
   ├─ <80% = Good
   ├─ 80-95% = Warning
   └─ >95% = Critical

3. Response Time (P99)
   ├─ <10s = Good
   ├─ 10-30s = Warning
   └─ >30s = Critical

4. Error Rate
   ├─ <1% = Good
   ├─ 1-10% = Warning
   └─ >10% = Critical
```

## Interpreting Results

### Example: Finding Breaking Point

```
Test Results:
═════════════════════════════════════════════════════════

Stage 1 (10 users):
  ├─ Response Time P95: 2.5s ✅
  ├─ Error Rate: 0% ✅
  ├─ RPS: 8.5 ✅
  └─ Status: HEALTHY

Stage 2 (20 users):
  ├─ Response Time P95: 4.2s ✅
  ├─ Error Rate: 0.2% ✅
  ├─ RPS: 16.8 ✅
  └─ Status: GOOD

Stage 3 (40 users):
  ├─ Response Time P95: 12.5s ⚠️
  ├─ Error Rate: 2.5% ⚠️
  ├─ RPS: 28.3 ⚠️
  └─ Status: DEGRADED

Stage 4 (60 users):
  ├─ Response Time P95: 45.2s ❌
  ├─ Error Rate: 35% ❌
  ├─ RPS: 15.2 ❌ (decreasing!)
  └─ Status: FAILING

Conclusion:
═══════════
✅ Server capacity: ~20-25 concurrent users
⚠️ Degradation starts: ~30-35 users
❌ Complete failure: ~50+ users

Recommendation: Run production with max 20 users
```

## What Metrics Tell You

### Response Time Trends

```
Response Time Over Stages:
═══════════════════════════════════════

Time (s)
  50│                          ┌──── BREAKING!
    │                         ╱
  30│                   ┌────┘
    │                  ╱
  15│            ┌────┘             DEGRADING
    │           ╱
   5│    ┌────┘                     HEALTHY
    │───┘
   0└──────────────────────────────
    10  20  30  40  50  60  Users

✅ Flat line = Healthy
⚠️ Gentle slope = Approaching limit
❌ Steep increase = Past capacity!
```

### Error Rate Trends

```
Error Rate Over Stages:
═══════════════════════════════════════

Rate (%)
 100│                          ┌──── DEATH SPIRAL!
    │                         ╱
  50│                    ┌───┘
    │                   ╱
  10│            ┌─────┘             FAILING
    │           ╱
   1│     ╱────┘                     WARNING
    │────┘
   0└──────────────────────────────
    10  20  30  40  50  60  Users

✅ <1% = Healthy
⚠️ 1-10% = Warning zone
❌ >10% = Failing
```

### RPS (Throughput) Trends

```
Requests/Second Over Stages:
═══════════════════════════════════════

RPS
  40│       ┌────────┐
    │      ╱          ╲                IDEAL: Keeps increasing
  30│     ╱            ╲
    │    ╱              ╲──────        BAD: Plateaus or drops!
  20│   ╱
    │  ╱
  10│─┘
    │
   0└──────────────────────────────
    10  20  30  40  50  60  Users

If RPS drops as users increase:
❌ Server is OVERLOADED!
```

## Recommended Actions Based on Results

### Scenario 1: Early Failure (Fails at <10 users)

```
Symptoms:
├─ Errors start immediately
├─ Response time always high
└─ Can't handle even light load

Actions:
1. Check server health (not load issue)
2. Review application logs for errors
3. Check database connectivity
4. Verify service configuration
```

### Scenario 2: Gradual Degradation (Degrades 10-30 users)

```
Symptoms:
├─ Works well at low load
├─ Gradually slows down
└─ Errors increase linearly

Actions:
1. Optimize application code
2. Add more resources (CPU/Memory)
3. Scale horizontally (add servers)
4. Optimize database queries
```

### Scenario 3: Sudden Crash (Works until sudden failure)

```
Symptoms:
├─ Fine until specific user count
├─ Sudden spike in errors
└─ Complete failure after threshold

Actions:
1. Check for resource limits (connection pools)
2. Review concurrency limits
3. Check for memory leaks
4. Look for database connection exhaustion
```

## Tips for Best Results

### Before Running

- [ ] Ensure server is healthy (no existing issues)
- [ ] Clear Grafana dashboards
- [ ] Check server has no other load
- [ ] Verify .env file is configured
- [ ] Disable retries (set `total=0` in RetryTrackingAdapter)

### During Test

- [ ] Watch Locust web UI for real-time metrics
- [ ] Monitor Grafana dashboards
- [ ] Note when degradation starts
- [ ] Note when failure begins
- [ ] Take screenshots of key moments

### After Test

- [ ] Review error_categorization in JSON output
- [ ] Check Grafana for resource usage patterns
- [ ] Identify exact breaking point
- [ ] Document findings
- [ ] Plan optimization strategy

## Common Issues

### Issue 1: Test Stops Unexpectedly

**Cause:** Locust process crashed
**Solution:** Check terminal for errors, increase timeout

### Issue 2: No Users Spawning

**Cause:** Load shape returned None
**Solution:** Check stage durations, test should auto-run

### Issue 3: Error Rate 100% From Start

**Cause:** Server already failing or config issue
**Solution:** Fix server first, then test

### Issue 4: Retry Multiplier Still High

**Cause:** Retries still enabled
**Solution:** Set `total=0` in RetryTrackingAdapter

## Expected Output

After the test completes, you'll have:

```
1. JSON Results File:
   └─ Load_testing_DPG/load_testing_results/[service]_load_test_results.json

   Contains:
   ├─ Performance metrics per stage
   ├─ Error breakdown (client vs server)
   ├─ Response time percentiles
   └─ Retry statistics

2. Console Output:
   └─ Stage transitions
   └─ Real-time statistics
   └─ Error breakdown

3. Grafana Data:
   └─ Server metrics timeline
   └─ Correlation with load stages
   └─ Resource usage patterns

4. Locust Charts:
   └─ Response time over time
   └─ RPS over time
   └─ Error rate over time
   └─ User count over time
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `locust -f nmt_load_shape_test.py --host=http://...` | Run NMT load shape test |
| `locust -f asr_load_shape_test.py --host=http://...` | Run ASR load shape test |
| `http://localhost:8089` | Open Locust web UI |
| `Ctrl+C` | Stop test gracefully |

## Next Steps

After finding your server capacity:

1. **Document the limits** (e.g., "Server can handle 25 concurrent users")
2. **Set up monitoring alerts** at 80% of capacity
3. **Plan scaling strategy** (vertical or horizontal)
4. **Optimize bottlenecks** identified during test
5. **Re-test after optimizations** to measure improvement

---

**Happy Load Testing!** 🚀

For questions or issues, check the main README or application logs.
