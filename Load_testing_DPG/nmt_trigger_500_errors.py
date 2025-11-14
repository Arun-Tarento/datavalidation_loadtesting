#!/usr/bin/env python3
"""
Script to trigger errors for NMT service:
- 10 requests to trigger HTTP 500 errors (server errors)
- 20 requests to trigger HTTP 400 errors (client errors)
Usage: python3 nmt_trigger_500_errors.py
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

headers = {
    "Authorization": auth_token,
    "x-auth-source": "AUTH_TOKEN",
    "Content-Type": "application/json",
    "accept": "application/json"
}

print("="*70)
print("NMT ERROR GENERATION SCRIPT")
print("="*70)
print(f"Target: {base_url}/services/inference/translation")
print()

error_500_count = 0
error_400_count = 0
total_error_count = 0
success_count = 0

# ===== PART 1: Generate 500 Errors =====
print("="*70)
print("PART 1: SENDING 10 REQUESTS TO TRIGGER 500 ERRORS")
print("="*70)
print()

# Send 10 requests with empty source text (should trigger 500)
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": "ai4bharat/indictrans--gpu-t4",
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva",
                "targetLanguage": "ta",
                "targetScriptCode": "Taml"
            }
        },
        "input": [{"source": ""}]  # Empty source text - should cause error
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/translation",
            params={"serviceId": "ai4bharat/indictrans--gpu-t4"},
            json=payload,
            headers=headers,
            timeout=30
        )

        status = response.status_code
        if status >= 500:
            print(f"✅ Request {i+1:2d}: HTTP {status} (500 error as expected)")
            error_500_count += 1
            total_error_count += 1
        elif status >= 400:
            print(f"⚠️  Request {i+1:2d}: HTTP {status} (Client error, expected 500)")
            total_error_count += 1
        else:
            print(f"❌ Request {i+1:2d}: HTTP {status} (Unexpected success)")
            success_count += 1

    except Exception as e:
        print(f"❌ Request {i+1:2d}: Exception - {e}")
        total_error_count += 1

print()

# ===== PART 2: Generate 400 Errors =====
print("="*70)
print("PART 2: SENDING 20 REQUESTS TO TRIGGER 400 ERRORS")
print("="*70)
print()

# Send 20 requests with non-existent service ID (should trigger 404)
for i in range(20):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": "ai4bharat/non-existent-nmt-service-404",  # Non-existent service
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva",
                "targetLanguage": "ta",
                "targetScriptCode": "Taml"
            }
        },
        "input": [{"source": "यह एक परीक्षण वाक्य है"}]  # Valid source text
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/translation",
            params={"serviceId": "ai4bharat/non-existent-nmt-service-404"},
            json=payload,
            headers=headers,
            timeout=30
        )

        status = response.status_code
        if status >= 400 and status < 500:
            print(f"✅ Request {i+1:2d}: HTTP {status} (400 error as expected)")
            error_400_count += 1
            total_error_count += 1
        elif status >= 500:
            print(f"⚠️  Request {i+1:2d}: HTTP {status} (Server error, expected 400)")
            total_error_count += 1
        else:
            print(f"❌ Request {i+1:2d}: HTTP {status} (Unexpected success)")
            success_count += 1

    except Exception as e:
        print(f"❌ Request {i+1:2d}: Exception - {e}")
        total_error_count += 1

print()
print("="*70)
print("SUMMARY")
print("="*70)
print(f"Total Requests: 30")
print(f"  - 500 Errors Generated: {error_500_count}")
print(f"  - 400 Errors Generated: {error_400_count}")
print(f"  - Total Errors: {total_error_count}")
print(f"  - Unexpected Success: {success_count}")
print()
print("✅ Check your Grafana dashboard now!")
print("   Look for error rate spike in NMT/Translation endpoint")
print("   - 10 × HTTP 500 errors (server errors)")
print("   - 20 × HTTP 400 errors (client errors)")
print("="*70)
