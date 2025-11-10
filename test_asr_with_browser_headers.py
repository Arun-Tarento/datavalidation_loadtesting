#!/usr/bin/env python3
"""
Test ASR with browser-like headers to match UI behavior
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

# Build payload - exact same as UI
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

# Headers with browser-like attributes
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
headers = {
    "Authorization": auth_token,
    "Content-Type": "application/json",
    "x-auth-source": "YOUR_TOKEN",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://core-v1.ai4inclusion.org",
    "Referer": "https://core-v1.ai4inclusion.org/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection": "keep-alive"
}

print("Making request with browser-like headers and 120s timeout...")

try:
    response = requests.post(
        "https://core-v1.ai4inclusion.org/api/v1/asr/inference",
        json=payload,
        headers=headers,
        timeout=120  # 2 minute timeout
    )

    print(f"Status: {response.status_code}")
    print(f"Response length: {len(response.text)}")
    print(f"Response headers: {dict(response.headers)}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS! Transcription: {result['output'][0]['source']}")
    else:
        print(f"❌ FAILED: {response.text[:500]}")

except requests.exceptions.Timeout:
    print("❌ Request timed out after 120 seconds")
except Exception as e:
    print(f"❌ Error: {e}")
