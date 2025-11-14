#!/usr/bin/env python3
"""
Simple script to send 10 malformed requests to trigger HTTP 404 errors for ASR
Usage: python3 asr_trigger_400_errors.py
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
print("SENDING 10 REQUESTS TO TRIGGER 404 ERRORS - ASR SERVICE")
print("="*70)
print(f"Target: {base_url}/services/inference/asr")
print()

error_count = 0
success_count = 0
error_404_count = 0

# Send 10 requests with non-existent service ID to trigger 404
for i in range(10):
    payload = {
        "controlConfig": {"dataTracking": True},
        "config": {
            "serviceId": "ai4bharat/non-existent-service-id-404",  # Non-existent service
            "language": {
                "sourceLanguage": "hi"
            }
        },
        "audio": [{"audioContent": "dGVzdCBhdWRpbyBjb250ZW50"}]  # Valid base64
    }

    try:
        response = requests.post(
            f"{base_url}/services/inference/asr",
            params={"serviceId": "ai4bharat/non-existent-service-id-404"},
            json=payload,
            headers=headers,
            timeout=30
        )

        status = response.status_code
        if status == 404:
            print(f"✅ Request {i+1:2d}: HTTP {status} (404 as expected)")
            error_404_count += 1
            error_count += 1
        elif status >= 500:
            print(f"⚠️  Request {i+1:2d}: HTTP {status} (Server error)")
            error_count += 1
        elif status >= 400:
            print(f"⚠️  Request {i+1:2d}: HTTP {status} (Client error, not 404)")
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
print(f"404 Errors Generated: {error_404_count}")
print(f"Total Errors: {error_count}")
print(f"Unexpected Success: {success_count}")
print()
print("✅ Check your Grafana dashboard now!")
print("   Look for 404 error rate spike in ASR endpoint")
print("="*70)
