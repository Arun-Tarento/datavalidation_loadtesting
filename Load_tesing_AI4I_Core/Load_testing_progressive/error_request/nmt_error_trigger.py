#!/usr/bin/env python3
"""
Comprehensive NMT Error Trigger Script - AI4I Core API
Triggers: 10x500, 20x400, 5x300, 5x200 responses
Usage: python3 Load_tesing_AI4I_Core/Load_testing_progressive/error_request/nmt_error_trigger.py
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment
script_dir = os.path.dirname(os.path.abspath(__file__))
progressive_dir = os.path.dirname(script_dir)  # Load_testing_progressive
ai4i_core_dir = os.path.dirname(progressive_dir)  # Load_tesing_AI4I_Core
project_root = os.path.dirname(ai4i_core_dir)  # datavalidation_loadtesting
env_path = os.path.join(ai4i_core_dir, '.env')
load_dotenv(env_path)

# Configuration
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
base_url = os.getenv("NMT_BASE_URL", "https://core-v1.ai4inclusion.org")
service_id = os.getenv("NMT_SERVICE_ID", "ai4bharat/indictrans--gpu-t4")

headers = {
    "Authorization": auth_token,
    "x-auth-source": x_auth_source,
    "Content-Type": "application/json",
    "accept": "application/json"
}

# Load valid text sample
samples_file = os.path.join(project_root, "load_testing_test_samples/nmt/nmt_samples.json")
try:
    with open(samples_file, 'r') as f:
        data = json.load(f)
        valid_text = data.get("nmt_samples", [{"source": "Hello"}])[0]["source"]
except:
    valid_text = "Hello, how are you?"

# Results tracking
results = {
    "500_errors": 0,
    "400_errors": 0,
    "300_redirects": 0,
    "200_success": 0,
    "other": 0
}

print("="*80)
print("NMT ERROR TRIGGER SCRIPT - AI4I Core API")
print("="*80)
print(f"Target: {base_url}/api/v1/nmt/inference")
print(f"Total requests: 40 (10x500 + 20x400 + 5x300 + 5x200)")
print("="*80)
print()

# ============================================================================
# 1. TRIGGER 10 x 500 ERRORS (Server Errors)
# ============================================================================
print("📛 Triggering 10 x 500 Server Errors (empty text/invalid config)...")
print("-" * 80)

for i in range(10):
    payload = {
        "input": [
            {
                "source": ""  # Empty text - may cause server error
            }
        ],
        "config": {
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "ta"
            },
            "serviceId": service_id
        },
        "controlConfig": {"dataTracking": False}
    }

    try:
        response = requests.post(
            f"{base_url}/api/v1/nmt/inference",
            json=payload,
            headers=headers,
            timeout=30
        )
        status = response.status_code

        if status >= 500:
            results["500_errors"] += 1
            print(f"  ✅ Request {i+1:2d}/10: HTTP {status} (500 error)")
        elif status >= 400:
            results["400_errors"] += 1
            print(f"  ⚠️  Request {i+1:2d}/10: HTTP {status} (400 error instead)")
        elif status >= 300:
            results["300_redirects"] += 1
            print(f"  ⚠️  Request {i+1:2d}/10: HTTP {status} (redirect)")
        elif status == 200:
            results["200_success"] += 1
            print(f"  ❌ Request {i+1:2d}/10: HTTP {status} (unexpected success)")
        else:
            results["other"] += 1
            print(f"  ❓ Request {i+1:2d}/10: HTTP {status}")
    except Exception as e:
        results["500_errors"] += 1
        print(f"  ✅ Request {i+1:2d}/10: Exception (counted as 500)")

print()

# ============================================================================
# 2. TRIGGER 20 x 400 ERRORS (Client Errors)
# ============================================================================
print("📛 Triggering 20 x 400 Client Errors (invalid service ID)...")
print("-" * 80)

for i in range(20):
    payload = {
        "input": [
            {
                "source": valid_text
            }
        ],
        "config": {
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "ta"
            },
            "serviceId": f"invalid-nmt-service-{i}"  # Invalid service ID
        },
        "controlConfig": {"dataTracking": False}
    }

    try:
        response = requests.post(
            f"{base_url}/api/v1/nmt/inference",
            json=payload,
            headers=headers,
            timeout=30
        )
        status = response.status_code

        if status >= 400 and status < 500:
            results["400_errors"] += 1
            print(f"  ✅ Request {i+1:2d}/20: HTTP {status} (400 error)")
        elif status >= 500:
            results["500_errors"] += 1
            print(f"  ⚠️  Request {i+1:2d}/20: HTTP {status} (500 error instead)")
        elif status >= 300:
            results["300_redirects"] += 1
            print(f"  ⚠️  Request {i+1:2d}/20: HTTP {status} (redirect)")
        elif status == 200:
            results["200_success"] += 1
            print(f"  ❌ Request {i+1:2d}/20: HTTP {status} (unexpected success)")
        else:
            results["other"] += 1
            print(f"  ❓ Request {i+1:2d}/20: HTTP {status}")
    except Exception as e:
        results["400_errors"] += 1
        print(f"  ✅ Request {i+1:2d}/20: Exception (counted as 400)")

print()

# ============================================================================
# 3. TRIGGER 5 x 300 REDIRECTS
# ============================================================================
print("📛 Triggering 5 x 300 Redirects (wrong endpoint URLs)...")
print("-" * 80)

for i in range(5):
    payload = {
        "input": [
            {
                "source": valid_text
            }
        ],
        "config": {
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "ta"
            },
            "serviceId": service_id
        },
        "controlConfig": {"dataTracking": False}
    }

    try:
        # Try different URL variations that might redirect
        response = requests.post(
            f"{base_url}/api/v1/nmt/inference/",  # Trailing slash might redirect
            json=payload,
            headers=headers,
            timeout=30,
            allow_redirects=False  # Don't follow redirects
        )
        status = response.status_code

        if status >= 300 and status < 400:
            results["300_redirects"] += 1
            print(f"  ✅ Request {i+1:2d}/5: HTTP {status} (redirect)")
        elif status >= 400 and status < 500:
            results["400_errors"] += 1
            print(f"  ⚠️  Request {i+1:2d}/5: HTTP {status} (400 error instead)")
        elif status >= 500:
            results["500_errors"] += 1
            print(f"  ⚠️  Request {i+1:2d}/5: HTTP {status} (500 error instead)")
        elif status == 200:
            results["200_success"] += 1
            print(f"  ⚠️  Request {i+1:2d}/5: HTTP {status} (success instead)")
        else:
            results["other"] += 1
            print(f"  ❓ Request {i+1:2d}/5: HTTP {status}")
    except Exception as e:
        results["300_redirects"] += 1
        print(f"  ⚠️  Request {i+1:2d}/5: Exception (counted as 300)")

print()

# ============================================================================
# 4. TRIGGER 5 x 200 SUCCESS
# ============================================================================
print("✅ Triggering 5 x 200 Success (valid requests)...")
print("-" * 80)

for i in range(5):
    payload = {
        "input": [
            {
                "source": valid_text
            }
        ],
        "config": {
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "ta"
            },
            "serviceId": service_id
        },
        "controlConfig": {"dataTracking": False}
    }

    try:
        response = requests.post(
            f"{base_url}/api/v1/nmt/inference",
            json=payload,
            headers=headers,
            timeout=60
        )
        status = response.status_code

        if status == 200:
            results["200_success"] += 1
            print(f"  ✅ Request {i+1:2d}/5: HTTP {status} (success)")
        elif status >= 400 and status < 500:
            results["400_errors"] += 1
            print(f"  ⚠️  Request {i+1:2d}/5: HTTP {status} (400 error)")
        elif status >= 500:
            results["500_errors"] += 1
            print(f"  ⚠️  Request {i+1:2d}/5: HTTP {status} (500 error)")
        elif status >= 300:
            results["300_redirects"] += 1
            print(f"  ⚠️  Request {i+1:2d}/5: HTTP {status} (redirect)")
        else:
            results["other"] += 1
            print(f"  ❓ Request {i+1:2d}/5: HTTP {status}")
    except Exception as e:
        print(f"  ❌ Request {i+1:2d}/5: Exception - {str(e)[:50]}")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("="*80)
print("SUMMARY - NMT ERROR TRIGGER RESULTS (AI4I Core API)")
print("="*80)
print(f"500 Server Errors:  {results['500_errors']:3d} (target: 10)")
print(f"400 Client Errors:  {results['400_errors']:3d} (target: 20)")
print(f"300 Redirects:      {results['300_redirects']:3d} (target: 5)")
print(f"200 Success:        {results['200_success']:3d} (target: 5)")
print(f"Other:              {results['other']:3d}")
print(f"Total Requests:     {sum(results.values()):3d} (expected: 40)")
print("="*80)
print("\n✅ Check your monitoring dashboard for error rate spikes!")
