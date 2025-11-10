#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/arun/Doc 2/Auto')

# Force reload of environment
import os
from dotenv import load_dotenv
load_dotenv(override=True)

import json
import requests

# Read audio
with open('asr/audio_samples.json') as f:
    audio_content = json.load(f)['audio_samples'][0]

# Build payload with all fields
payload = {
    "audio": [{
        "audioContent": audio_content
    }],
    "config": {
        "language": {"sourceLanguage": "hi"},
        "serviceId": os.getenv("ASR_SERVICE_ID"),
        "audioFormat": "wav",
        "samplingRate": 16000,
        "transcriptionFormat": "transcript",
        "bestTokenCount": 0,
        "encoding": "base64",
        "preProcessors": ["vad", "denoise"],
        "postProcessors": ["lm", "punctuation"]
    },
    "controlConfig": {"dataTracking": False}
}

headers = {
    "x-auth-source": "YOUR_TOKEN",
    "Content-Type": "application/json",
    "Authorization": os.getenv("AUTH_TOKEN", "").strip('"')
}

print(f"Service ID: {payload['config']['serviceId']}")
print("Making request...")

response = requests.post(
    "https://core-v1.ai4inclusion.org/api/v1/asr/inference",
    json=payload,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response text (first 500 chars): {response.text[:500]}")
try:
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Failed to parse JSON: {e}")

if result['output'][0]['source']:
    print(f"\n✅ SUCCESS! Transcription: {result['output'][0]['source']}")
else:
    print("\n❌ FAILED: Empty transcription")
