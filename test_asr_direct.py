#!/usr/bin/env python3
"""
Direct ASR API test to diagnose the issue
"""
import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Load audio sample
with open('asr/audio_samples.json', 'r') as f:
    data = json.load(f)
    audio_content = data['audio_samples'][0]

print(f"Audio content length: {len(audio_content)}")
print(f"First 100 chars: {audio_content[:100]}")

# Build payload
payload = {
    "audio": [
        {
            "audioContent": audio_content
        }
    ],
    "config": {
        "serviceId": "ai4bharat/indictasr",
        "language": {
            "sourceLanguage": "hi"
        },
        "audioFormat": "wav",
        "samplingRate": 16000,
        "transcriptionFormat": "transcript",
        "bestTokenCount": 0
    },
    "controlConfig": {"dataTracking": False}
}

# Headers
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
headers = {
    "x-auth-source": os.getenv("X_AUTH_SOURCE", ""),
    "Content-Type": "application/json",
    "Authorization": auth_token
}

print("\n=== Making API Request ===")
print(f"URL: https://core-v1.ai4inclusion.org/api/v1/asr/inference")
print(f"Service: {payload['config']['serviceId']}")
print(f"Language: {payload['config']['language']['sourceLanguage']}")
print(f"Format: {payload['config']['audioFormat']}")
print(f"Sampling Rate: {payload['config']['samplingRate']}")
print(f"\n=== Headers ===")
for key, value in headers.items():
    if key.lower() == 'authorization':
        print(f"{key}: {value[:20]}..." if len(value) > 20 else f"{key}: {value}")
    else:
        print(f"{key}: {value}")
print(f"\n=== Payload Structure ===")
print(f"Audio content length: {len(payload['audio'][0]['audioContent'])}")
print(f"Config keys: {list(payload['config'].keys())}")
print(f"Control config: {payload['controlConfig']}")

# Make request
response = requests.post(
    "https://core-v1.ai4inclusion.org/api/v1/asr/inference",
    json=payload,
    headers=headers
)

print(f"\n=== Response ===")
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
