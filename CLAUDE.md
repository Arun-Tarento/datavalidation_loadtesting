# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains **Locust-based load testing scripts** for AI4I (AI for India) language services targeting `staging.ai4inclusion.org` and `sandbox.ai4inclusion.org`. Services covered: NMT (translation), ASR (speech recognition), TTS (text-to-speech), and auth endpoints (login, token refresh, `/me`, API keys).

## Repository Structure

```
testing/
  .sandbox.env                  ← All config/credentials for sandbox
  .staging.env                  ← All config/credentials for staging
  AI4I/
    loadtesting/
      NMT/                      ← NMT-specific load testing files
        nmt_loadtesting.py      ← NMT inference load test (Jaeger-integrated)
        check_timing_headers.py ← Utility to verify timing headers
        analyze_request_timing.sh ← Shell script for timing analysis
        JAEGER_CLIENT_INTEGRATION_GUIDE.md ← Guide for using Jaeger traces
        JAEGER_IMPLEMENTATION_GUIDE.md     ← Server-side Jaeger setup reference
      asr_loadtesting.py        ← ASR inference load test
      tts_loadtesting.py        ← TTS inference load test
      login_test_concurrency.py ← Auth login endpoint stress test
      x.py                      ← One-shot login test (stops user after single login)
      metrics_tracker.py        ← Custom metrics aggregator (captures trace IDs)
      jaeger_analyzer.py        ← Jaeger trace analysis utility
      users.py                  ← Utility: bulk-create 100 test users via API
    Errors/
      nmt_errors.py             ← Interactive error-trigger script for NMT
      asr_errors.py             ← Interactive error-trigger script for ASR
    logs/                       ← JSON metrics output (auto-created at test stop)
samples/
  NMT/nmt_100_samples.json
  TTS/tts_100_samples.json
  ASR/hindi_4s.wav
generate_nmt_100_samples.py
requirements.txt
```

## Running Tests

**Always run from the repo root.** Select the environment with the `ENV` variable (`staging` is the default).

### Install dependencies
```bash
pip install -r requirements.txt
```

### NMT load test
```bash
# Staging (default)
locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 1h

# Sandbox
ENV=sandbox locust -f testing/AI4I/loadtesting/NMT/nmt_loadtesting.py --users 10 --spawn-rate 1 --run-time 1h
```

### ASR / TTS load test
```bash
# Staging
locust -f testing/AI4I/loadtesting/asr_loadtesting.py --users 10 --spawn-rate 1 --run-time 1h

# Sandbox
ENV=sandbox locust -f testing/AI4I/loadtesting/tts_loadtesting.py --users 10 --spawn-rate 1 --run-time 1h
```

### Login stress test
```bash
ENV=staging locust -f testing/AI4I/loadtesting/login_test_concurrency.py --users 20 --spawn-rate 2 --run-time 30m
```

### One-shot login test
```bash
ENV=sandbox locust -f testing/AI4I/loadtesting/x.py --users 100 --spawn-rate 10
```

Open http://localhost:8089 for the Locust web UI. Add `--headless` to skip the UI.

### Trigger deliberate errors interactively
```bash
ENV=sandbox python testing/AI4I/Errors/nmt_errors.py
ENV=sandbox python testing/AI4I/Errors/asr_errors.py
# prompts for error code (400/401/403/404/500/502/valid) and request count
```

### Bulk-create 100 test accounts (one-time setup)
```bash
python testing/AI4I/loadtesting/users.py
# Admin token + API key are hardcoded inside this script
```

### Analyze Jaeger traces
Server-side Jaeger tracing is enabled on staging and sandbox. Load tests automatically extract trace IDs from response headers.

```bash
# Analyze a specific trace
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --trace-id e6887e0d7ba9f00d00414608926747f7 \
  --env staging

# Analyze all failed/slow traces from a load test
python testing/AI4I/loadtesting/jaeger_analyzer.py \
  --metrics-file testing/AI4I/logs/nmt_metrics_staging_*.json \
  --env staging
```

The analyzer shows timing breakdowns: total time, ML inference time, non-inference time (auth, preprocessing, postprocessing), and top slowest spans. See [JAEGER_CLIENT_INTEGRATION_GUIDE.md](testing/AI4I/loadtesting/NMT/JAEGER_CLIENT_INTEGRATION_GUIDE.md) for details.

## Architecture

### Environment switching
All scripts read `ENV` at startup and load `testing/.{ENV}.env` via `python-dotenv`. Every hardcoded value (URL, API key, credentials, service IDs, sample paths, log dir) lives in those env files. The two env files differ in:
- `BASE_URL` — staging vs sandbox URL
- `API_KEY` — different key per environment
- `NMT_SERVICE_ID` — staging uses a UUID, sandbox uses a named ID
- `TEST_ACCOUNT_EMAIL_PATTERN` — `ltest_user_{}` (staging) vs `test_user_{}` (sandbox)

### Auth flow (inference tests)
All three inference files share the same pattern:
1. `on_start` → `login()` → store `access_token` + `refresh_token`
2. Before each `@task` → `token_refresh()` re-posts to `/api/v1/auth/refresh` if `TOKEN_LIFETIME` has elapsed; re-login on refresh failure
3. On 401 response → clear `access_token`; next task iteration retries login
4. Samples are loaded once into a class-level cache (`source_cache`) and iterated via `itertools.cycle`

### MetricsTracker
Used only by `NMT/nmt_loadtesting.py`. Module-level singleton (`metrics = MetricsTracker()`). On `test_stop`, writes a JSON summary to `testing/AI4I/logs/nmt_metrics_{env}_{timestamp}.json` with counts, success rate, req/s, response time percentiles (P95, P99), and lists of trace IDs for failed requests and slow requests (>5s). Trace IDs link to Jaeger UI for detailed timing breakdown.

### Test account pool
100 pre-created accounts managed per environment. `login_test_concurrency.py` picks randomly; `x.py` uses round-robin via `itertools.cycle`. Account email pattern and password come from the env file. `users.py` is the one-time admin script to create them.

### Error trigger scripts
Plain Python (not Locust). Login once, then send `N` requests with deliberately malformed payloads or headers (bad token, bad API key, wrong endpoint, null payload, oversized payload). Controlled interactively via stdin.
