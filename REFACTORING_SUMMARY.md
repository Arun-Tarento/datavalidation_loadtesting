# Load Testing Scripts Refactoring Summary

## Overview
All three load testing scripts (asr_latency.py, nmt_latency.py, tts_latency.py) have been refactored to:
1. Load samples from `.example` files in `Test_samples/` directory
2. Save results to `results/` directory
3. Use absolute paths for reliable file access
4. Fix global configuration initialization issues

---

## Changes Made to All Three Scripts

### 1. Sample File Paths (Now using Test_samples/)

**asr_latency.py:**
- Old: `"ASR/audio_samples.json"`
- New: `"Test_samples/ASR/audio_samples.json.example"`

**nmt_latency.py:**
- Old: `"NMT/nmt_samples.json"`
- New: `"Test_samples/NMT/nmt_samples.json.example"`

**tts_latency.py:**
- Old: `"TTS/tts_samples.json"`
- New: `"Test_samples/TTS/tts_samples.json.example"`

### 2. Results Output Directory

All three scripts now save results to `results/` directory:
- `results/asr_latency_locust_results.json`
- `results/nmt_latency_locust_results.json`
- `results/tts_latency_locust_results.json`

The `results/` directory is automatically created if it doesn't exist.

### 3. Absolute Path Resolution

All scripts now convert relative paths to absolute paths:
```python
# Convert to absolute path if it's relative
if not os.path.isabs(file_path):
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    project_root = os.path.dirname(script_dir)
    file_path = os.path.join(project_root, file_path)
```

This ensures files are found regardless of the current working directory.

### 4. Global Configuration Fix (NMT & TTS)

**Problem:** Scripts were initializing config at module load time, causing errors.

**Solution:**
- Commented out global config initialization
- Config is now created fresh in each user's `on_start()` method
- Config is created temporarily in event handlers when needed

**Before:**
```python
config = NMTConfig()  # This runs at import time
```

**After:**
```python
# Initialize global configuration (will be created fresh in each user)
# config = NMTConfig()  # Commented out to avoid caching

class NMTUser(HttpUser):
    def on_start(self):
        try:
            load_dotenv(override=True)
            self.config = NMTConfig()  # Fresh config per user
            ...
```

### 5. Updated Usage Instructions

All scripts now reference the correct path:
- Old: `locust -f ASR/asr_latency.py ...`
- New: `locust -f Load_testing_scripts/asr_latency.py ...`

---

## New File Created

**Test_samples/TTS/tts_samples.json.example**
- Created with 10 Hindi text samples for TTS testing
- Format matches NMT samples structure

---

## File Structure

```
/home/arun/Doc 2/Auto/
├── Load_testing_scripts/
│   ├── asr_latency.py          # ✅ Refactored
│   ├── nmt_latency.py          # ✅ Refactored
│   └── tts_latency.py          # ✅ Refactored
├── Test_samples/
│   ├── ASR/
│   │   └── audio_samples.json.example  # ✅ Exists (large file)
│   ├── NMT/
│   │   └── nmt_samples.json.example    # ✅ Exists (5 samples)
│   └── TTS/
│       └── tts_samples.json.example    # ✅ Created (10 samples)
└── results/                             # ✅ Auto-created by scripts
    ├── asr_latency_locust_results.json
    ├── nmt_latency_locust_results.json
    └── tts_latency_locust_results.json
```

---

## Usage Examples

### ASR Load Testing
```bash
cd "/home/arun/Doc 2/Auto"
locust -f Load_testing_scripts/asr_latency.py --host=https://core-v1.ai4inclusion.org
```

### NMT Load Testing
```bash
cd "/home/arun/Doc 2/Auto"
locust -f Load_testing_scripts/nmt_latency.py -u 1 -r 1 --run-time 30s --host=https://core-v1.ai4inclusion.org
```

### TTS Load Testing
```bash
cd "/home/arun/Doc 2/Auto"
locust -f Load_testing_scripts/tts_latency.py --host=https://core-v1.ai4inclusion.org
```

---

## Key Features

1. **Flexible Sample Loading:**
   - Can override sample file path via environment variable
   - Example: `export NMT_SAMPLES_FILE="/custom/path/samples.json"`

2. **Better Error Reporting:**
   - Shows current working directory on file not found
   - Prints absolute path being used

3. **Environment Refresh:**
   - Each user reloads `.env` file for fresh configuration
   - Supports dynamic configuration updates

4. **Result Organization:**
   - All results in one directory
   - Easy to find and manage test outputs

---

## Verification Commands

Check if all changes are applied:
```bash
# Check sample paths
grep "Test_samples" Load_testing_scripts/*.py

# Check results paths
grep "results/" Load_testing_scripts/*.py

# Check global config is commented
grep -A1 "# Initialize global configuration" Load_testing_scripts/nmt_latency.py
grep -A1 "# Initialize global configuration" Load_testing_scripts/tts_latency.py

# Check absolute path code
grep "Convert to absolute path" Load_testing_scripts/*.py
```

---

## Status: ✅ ALL CHANGES SAVED

All refactoring changes have been successfully applied and saved to the files.
