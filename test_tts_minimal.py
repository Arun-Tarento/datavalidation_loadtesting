#!/usr/bin/env python3
"""
Minimal TTS test
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Load text sample
with open('load_testing_test_samples/tts/tts_samples.json', 'r') as f:
    data = json.load(f)
    source_text = data['tts_samples'][0]['source']

print(f"Source text: {source_text[:100]}...")

# Build payload
payload = {
    "input": [{"source": source_text}],
    "config": {
        "language": {"sourceLanguage": "hi"},
        "serviceId": "indic-tts-coqui-indo_aryan",
        "gender": "female",
        "samplingRate": 22050,
        "audioFormat": "wav"
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

print("Making TTS request with 60s timeout...")

try:
    response = requests.post(
        "https://core-v1.ai4inclusion.org/api/v1/tts/inference",
        json=payload,
        headers=headers,
        timeout=60
    )

    print(f"Status: {response.status_code}")
    print(f"Response length: {len(response.text)}")

    if response.status_code == 200:
        result = response.json()
        audio_content = result.get('output', [{}])[0].get('audioContent', '')
        if audio_content:
            print(f"✅ SUCCESS! Audio content length: {len(audio_content)} characters")
        else:
            print(f"❌ FAILED: No audio content in response")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ FAILED: {response.text[:500]}")

except requests.exceptions.Timeout:
    print("❌ Request timed out after 60 seconds")
except Exception as e:
    print(f"❌ Error: {e}")
