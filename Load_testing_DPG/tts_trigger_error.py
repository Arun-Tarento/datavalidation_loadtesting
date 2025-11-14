#!/usr/bin/env python3
"""
Script to trigger errors for TTS service:
- 10 requests to trigger HTTP 500 errors (server errors)
- 10 requests to trigger HTTP 400 errors (client errors)
- 10 requests to attempt HTTP 300 errors (redirect errors - may not succeed)

Note: 3xx errors are redirect status codes which are rare in REST APIs.
      The script attempts to trigger them but they may not occur.

Usage: python3 tts_trigger_error.py
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")
service_id = os.getenv("TTS_SERVICE_ID", "ai4bharat/indictts--gpu-t4")

headers = {
    "Authorization": auth_token,
    "x-auth-source": "AUTH_TOKEN",
    "Content-Type": "application/json",
    "accept": "application/json"
}

print("="*70)
print("TTS ERROR GENERATION SCRIPT")
print("="*70)
print(f"Target: {base_url}/services/inference/tts")
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

# Send 10 requests with empty source text (should trigger 500)
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": service_id,
            "gender": "male",
            "samplingRate": 16000,
            "audioFormat": "wav",
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva"
            }
        },
        "input": []  # Empty input array - should cause error
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/tts",
            params={"serviceId": service_id},
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

# Send 10 requests with non-existent service ID (should trigger 404)
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": "ai4bharat/non-existent-tts-service-404",  # Non-existent service
            "gender": "male",
            "samplingRate": 16000,
            "audioFormat": "wav",
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva"
            }
        },
        "input": [{"source": "यह एक परीक्षण वाक्य है"}]  # Valid source text
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/tts",
            params={"serviceId": "ai4bharat/non-existent-tts-service-404"},
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

# ===== PART 3: Attempt to Generate 300 Errors =====
print("="*70)
print("PART 3: ATTEMPTING TO TRIGGER 300 ERRORS (REDIRECTS)")
print("="*70)
print("Note: 3xx errors are redirect codes, rare in REST APIs")
print()

# Try different approaches to trigger 3xx errors
for i in range(10):
    # The 307 redirects are actually coming from trailing slash handling
    # Let's use this consistently to generate 3xx errors

    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": service_id,
            "gender": "male",
            "samplingRate": 16000,
            "audioFormat": "wav",
            "language": {
                "sourceLanguage": "hi",
                "sourceScriptCode": "Deva"
            }
        },
        "input": [{"source": "परीक्षण"}]
    }

    # Use trailing slash to trigger 307 redirects consistently
    url = f"{base_url}/services/inference/tts/"

    try:
        response = requests.post(
            url,
            params={"serviceId": service_id},
            json=payload,
            headers=headers,
            timeout=30,
            allow_redirects=False  # Don't follow redirects to see 3xx status
        )

        status = response.status_code
        if status >= 300 and status < 400:
            print(f"✅ Request {i+1:2d}: HTTP {status} (300 redirect as expected!)")
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

if error_300_count == 0:
    print("⚠️  No 3xx redirect errors were triggered.")
    print("   This is expected - REST APIs rarely return redirect codes.")
    print()

print("✅ Check your Grafana dashboard now!")
print("   Look for error rate spike in TTS endpoint")
print("   - 10 × HTTP 500 errors (server errors)")
print("   - 10 × HTTP 400 errors (client errors)")
if error_300_count > 0:
    print(f"   - {error_300_count} × HTTP 300 errors (redirect errors)")
print("="*70)
