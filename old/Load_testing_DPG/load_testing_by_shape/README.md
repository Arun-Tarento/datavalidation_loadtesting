# Load Testing by Shape

This folder contains self-contained load shaping tests that gradually increase load to find server capacity.

## Files

### Test Scripts
- `asr_load_shape_test_with_metrics.py` - ASR (Speech Recognition) load shaping with detailed per-stage metrics
- `nmt_load_shape_test_with_metrics.py` - NMT (Translation) load shaping with detailed per-stage metrics
- `tts_load_shape_test_with_metrics.py` - TTS (Text-to-Speech) load shaping with detailed per-stage metrics
- `ner_load_shape_test_with_metrics.py` - NER (Named Entity Recognition) load shaping with detailed per-stage metrics
- `ocr_load_shape_test_with_metrics.py` - OCR (Optical Character Recognition) load shaping with detailed per-stage metrics
- `transliteration_load_shape_test_with_metrics.py` - Transliteration load shaping with detailed per-stage metrics
- `tld_load_shape_test_with_metrics.py` - TLD (Text Language Detection) load shaping with detailed per-stage metrics

### Configuration
- `shape_config.py` - Configuration classes (ASRConfig, NMTConfig, TTSConfig, NERConfig, OCRConfig, TransliterationConfig, TLDConfig) and User classes (ASRUser, NMTUser, TTSUser, NERUser, OCRUser, TransliterationUser, TLDUser)
- `.env` - Environment variables (uses parent folder's .env)

### Documentation
- `README.md` - This file
- `LOAD_SHAPING_GUIDE.md` - Detailed guide on load shaping concepts

## Self-Contained Design

This folder is **completely independent** and can be delivered standalone:
- ✅ Has its own `shape_config.py` with ASR/NMT Config and User classes
- ✅ Reads from parent `.env` file (or you can create a local one)
- ✅ Saves results to `../load_testing_shape_results/`
- ✅ No dependencies on `load_testing_scripts` folder

## Load Shapes Available

Each test file contains **three load shapes** that you can switch between by commenting/uncommenting:
1. **StagesShapeWithMetrics** (default) - Comprehensive testing, ~18 minutes
2. **ConservativeShapeWithMetrics** - Very slow, ~15 minutes, for weak servers
3. **AggressiveShapeWithMetrics** - Fast testing, ~10 minutes, find limits quickly

## Switching Between Load Shapes

Edit the file and comment/uncomment the desired shape at the bottom:

```python
# Default: StagesShapeWithMetrics (~18 min, comprehensive)
class CustomLoadShape(StagesShapeWithMetrics):
    pass

# Or use ConservativeShapeWithMetrics (~15 min, weak servers)
# class CustomLoadShape(ConservativeShapeWithMetrics):
#     pass

# Or use AggressiveShapeWithMetrics (~10 min, quick testing)
# class CustomLoadShape(AggressiveShapeWithMetrics):
#     pass
```

## Quick Start

### For ASR (Speech Recognition):
```bash
locust -f Load_testing_DPG/load_testing_by_shape/asr_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186:8000
```

### For NMT (Translation):
```bash
locust -f Load_testing_DPG/load_testing_by_shape/nmt_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186
```

### For TTS (Text-to-Speech):
```bash
locust -f Load_testing_DPG/load_testing_by_shape/tts_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186:8000
```

### For NER (Named Entity Recognition):
```bash
locust -f Load_testing_DPG/load_testing_by_shape/ner_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186:8000
```

### For OCR (Optical Character Recognition):
```bash
locust -f Load_testing_DPG/load_testing_by_shape/ocr_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186:8000
```

### For Transliteration:
```bash
locust -f Load_testing_DPG/load_testing_by_shape/transliteration_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186:8000
```

### For TLD (Text Language Detection):
```bash
locust -f Load_testing_DPG/load_testing_by_shape/tld_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186:8000
```

Then open http://localhost:8089 and click "Start"

## Results Location

All test results are automatically saved to:
```
Load_testing_DPG/load_testing_shape_results/
├── asr_load_shape_results_TIMESTAMP.json
├── nmt_load_shape_results_TIMESTAMP.json
├── tts_load_shape_results_TIMESTAMP.json
├── ner_load_shape_results_TIMESTAMP.json
├── ocr_load_shape_results_TIMESTAMP.json
├── transliteration_load_shape_results_TIMESTAMP.json
└── tld_load_shape_results_TIMESTAMP.json
```

## What You'll Get

### Enhanced Tests Output:
- ✅ Per-stage error rates
- ✅ Per-stage latency (min, max, median, avg, P95, P99)
- ✅ Per-stage payload sizes
- ✅ Per-stage throughput (req/s)
- ✅ Automatic breaking point detection
- ✅ Capacity analysis (healthy/degraded/failed stages)
- ✅ Production capacity recommendations

### Sample JSON Output:
```json
{
  "stage_by_stage_metrics": {
    "Stage 1: Warm-up (10 users)": {
      "requests": {
        "total": 234,
        "error_rate_percentage": 0.0
      },
      "latency_ms": {
        "average": 2456.8,
        "p95": 3123.4
      },
      "throughput": {
        "requests_per_second": 1.95
      }
    }
  },
  "capacity_analysis": {
    "max_healthy_capacity": 20,
    "breaking_point": "Stage 5: Heavy Stress (40 users)"
  },
  "recommendations": {
    "production_capacity": "14 concurrent users"
  }
}
```

## Load Stages

Both tests use these stages:

```
Stage 1: Warm-up (10 users)       - 2 minutes
Stage 2: Baseline (10 users)      - 2 minutes
Stage 3: Light Stress (20 users)  - 3 minutes
Stage 4: Medium Hold (20 users)   - 2 minutes
Stage 5: Heavy Stress (40 users)  - 2 minutes
Stage 6: Peak Hold (40 users)     - 2 minutes
Stage 7: Breaking Point (60 users)- 2 minutes
Stage 8: Observation (60 users)   - 2 minutes
Stage 9: Cool Down (10 users)     - 1 minute

Total: ~18 minutes
```

## Before Running

⚠️ **Important:** Disable retries for accurate results!

Edit `nmt_test.py` and `asr_test.py` in `load_testing_scripts/`:
```python
# Line ~62 in both files
retry_strategy = TrackedRetry(
    total=0,  # Set to 0!
```

## Documentation

For complete documentation, see:
- `../ENHANCED_LOAD_SHAPE_GUIDE.md` - Detailed guide for enhanced tests
- `../LOAD_SHAPING_GUIDE.md` - General load shaping concepts

## Quick Tips

1. **Start with enhanced tests** - They provide much more insight
2. **Monitor Grafana** during the test to see CPU/memory usage
3. **Compare multiple runs** to track improvements
4. **Set production limits** to 70% of max healthy capacity found

## Example Workflow

```bash
# 1. Disable retries (set total=0 in test files)

# 2. Run test
locust -f Load_testing_DPG/load_testing_by_shape/nmt_load_shape_test_with_metrics.py \
       --host=http://13.204.164.186

# 3. Open browser: http://localhost:8089, click "Start"

# 4. After 18 minutes, check results
cat Load_testing_DPG/load_testing_shape_results/nmt_load_shape_results_*.json

# 5. Review recommendations
jq '.recommendations' Load_testing_DPG/load_testing_shape_results/nmt_load_shape_results_*.json
```

---

**Happy Load Testing!** 🚀
