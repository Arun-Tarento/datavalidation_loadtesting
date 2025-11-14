#!/usr/bin/env python3
"""
Simple script to send 10 malformed requests to trigger HTTP 500 errors
Usage: python3 trigger_500_errors.py
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186")

headers = {
    "Authorization": auth_token,
    "x-auth-source": "AUTH_TOKEN",
    "Content-Type": "application/json",
    "accept": "application/json"
}

print("="*70)
print("SENDING 10 MALFORMED REQUESTS TO TRIGGER 500 ERRORS")
print("="*70)
print(f"Target: {base_url}/services/inference/translation")
print()

error_count = 0
success_count = 0

# Send 10 requests with empty audio (should trigger 500)
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": "ai4bharat/indictasr",
            "language": {
                "sourceLanguage": "hi"
            }
        },
        "audio": [{"audioContent": ""}]  # Empty audio - should cause error
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/asr",
            params={"serviceId": "ai4bharat/indictasr"},
            json=payload,
            headers=headers,
            timeout=30
        )

        status = response.status_code
        if status >= 500:
            print(f"✅ Request {i+1:2d}: HTTP {status} (Error as expected)")
            error_count += 1
        elif status >= 400:
            print(f"⚠️  Request {i+1:2d}: HTTP {status} (Client error)")
            error_count += 1
        else:
            print(f"❌ Request {i+1:2d}: HTTP {status} (Unexpected success)")
            success_count += 1

    except Exception as e:
        print(f"❌ Request {i+1:2d}: Exception - {e}")
        error_count += 1

print()
print("="*70)
print("SUMMARY")
print("="*70)
print(f"Total Requests: 10")
print(f"Errors Generated: {error_count}")
print(f"Unexpected Success: {success_count}")
print()
print("✅ Check your Grafana dashboard now!")
print("   Look for error rate spike in ASR endpoint")
print("="*70)
