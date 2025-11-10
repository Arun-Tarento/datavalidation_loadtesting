#!/usr/bin/env python3
"""
Minimal ASR test with timeout
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Load audio sample
with open('ASR/audio_samples.json', 'r') as f:
    data = json.load(f)
    audio_content = data['audio_samples'][0]

print(f"Audio content length: {len(audio_content)}")

# Build payload
payload = {
    "audio": [{"audioContent": audio_content}],
    "config": {
        "language": {"sourceLanguage": "hi"},
        "serviceId": "asr_am_ensemble",
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

# Headers
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
headers = {
    "x-auth-source": "YOUR_TOKEN",
    "Content-Type": "application/json",
    "Authorization": auth_token
}

print("Making request with 60s timeout...")

try:
    response = requests.post(
        "https://core-v1.ai4inclusion.org/api/v1/asr/inference",
        json=payload,
        headers=headers,
        timeout=60
    )

    print(f"Status: {response.status_code}")
    print(f"Response length: {len(response.text)}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS! Transcription: {result['output'][0]['source']}")
    else:
        print(f"❌ FAILED: {response.text[:500]}")

except requests.exceptions.Timeout:
    print("❌ Request timed out after 60 seconds")
except Exception as e:
    print(f"❌ Error: {e}")
