#!/usr/bin/env python3
"""
Script to trigger errors for Transliteration service:
- 10 requests to trigger HTTP 500 errors (server errors)
- 10 requests to trigger HTTP 400 errors (client errors)
- 10 requests to trigger HTTP 300 errors (redirect errors)

Usage: python3 transliteration_trigger_error.py
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")
service_id = os.getenv("TRANSLITERATION_SERVICE_ID", "ai4bharat/indicxlit--cpu-fsv2")

headers = {
    "Authorization": auth_token,
    "x-auth-source": "AUTH_TOKEN",
    "Content-Type": "application/json",
    "accept": "application/json"
}

print("="*70)
print("TRANSLITERATION ERROR GENERATION SCRIPT")
print("="*70)
print(f"Target: {base_url}/services/inference/transliteration")
print()

error_500_count = 0
error_400_count = 0
error_300_count = 0
total_error_count = 0
success_count = 0

# ===== PART 1: Generate 500 Errors =====
print("="*70)
print("PART 1: SENDING 10 REQUESTS TO TRIGGER 500 ERRORS")
print("="*70)
print()

# Send 10 requests with invalid language code to trigger 500
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": service_id,
            "language": {
                "sourceLanguage": "INVALID_LANG_CODE_XYZ",  # Invalid language triggers 500
                "sourceScriptCode": "Deva",
                "targetLanguage": "hi",
                "targetScriptCode": "Latn"
            },
            "isSentence": False,
            "numSuggestions": 5
        },
        "input": [{"source": "नमस्ते"}]
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/transliteration",
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
print("PART 2: SENDING 10 REQUESTS TO TRIGGER 400 ERRORS")
print("="*70)
print()

# Send 10 requests with non-existent service ID
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": "ai4bharat/non-existent-transliteration-service-404",
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva",
                "targetLanguage": "hi",
                "targetScriptCode": "Latn"
            },
            "isSentence": False,
            "numSuggestions": 5
        },
        "input": [{"source": "नमस्ते"}]
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/transliteration",
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

# ===== PART 3: Generate 300 Errors =====
print("="*70)
print("PART 3: SENDING 10 REQUESTS TO TRIGGER 300 ERRORS (REDIRECTS)")
print("="*70)
print()

# Use trailing slash to trigger 307 redirects
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": service_id,
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva",
                "targetLanguage": "hi",
                "targetScriptCode": "Latn"
            },
            "isSentence": False,
            "numSuggestions": 5
        },
        "input": [{"source": "नमस्ते"}]
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/transliteration/",  # Trailing slash for redirect
            json=payload,
            headers=headers,
            timeout=30,
            allow_redirects=False
        )

        status = response.status_code
        if status >= 300 and status < 400:
            print(f"✅ Request {i+1:2d}: HTTP {status} (300 redirect as expected)")
            error_300_count += 1
            total_error_count += 1
        elif status >= 400:
            print(f"⚠️  Request {i+1:2d}: HTTP {status} (Error, but not 3xx)")
            total_error_count += 1
        else:
            print(f"❌ Request {i+1:2d}: HTTP {status} (No redirect triggered)")
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
print(f"  - 300 Errors Generated: {error_300_count}")
print(f"  - Total Errors: {total_error_count}")
print(f"  - Unexpected Success: {success_count}")
print()
print("✅ Check your Grafana dashboard now!")
print("   Look for error rate spike in Transliteration endpoint")
print("   - 10 × HTTP 500 errors (server errors)")
print("   - 10 × HTTP 400 errors (client errors)")
print(f"   - {error_300_count} × HTTP 300 errors (redirect errors)")
print("="*70)
