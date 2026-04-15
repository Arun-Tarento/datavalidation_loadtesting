"""
Test single ASR request to debug issues
Can be run from any directory: python3 Load_testing_DPG/single_request_to_validate/asr_single_request_test.py
"""
import os
import json
from dotenv import load_dotenv
import requests

# Load environment - check script directory first, then project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))  # Go up 2 levels (single_request_to_validate -> Load_testing_DPG -> project_root)

# Try to find .env file in script directory first, then project root
env_path = os.path.join(script_dir, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(project_root, '.env')

load_dotenv(env_path)

# Configuration
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
service_id = os.getenv("ASR_SERVICE_ID", "ai4bharat/indictasr")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

print("="*70)
print("TESTING ASR REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")

# Load audio sample with robust path resolution
samples_file = "load_testing_test_samples/ASR/audio_samples.json"
samples_path = os.path.join(project_root, samples_file)

print(f"\nLoading audio samples from: {samples_path}")
try:
    with open(samples_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        audio_samples = data.get("audio_samples", [])
        print(f"Loaded {len(audio_samples)} audio samples")
        if audio_samples:
            audio_content = audio_samples[0]
            print(f"Audio content length: {len(audio_content)} characters")
        else:
            print("ERROR: No audio samples found!")
            exit(1)
except Exception as e:
    print(f"ERROR loading samples: {e}")
    print(f"Looking for file at: {samples_path}")
    exit(1)

print()

# Payload
payload = {
    "controlConfig": {
        "dataTracking": True
    },
    "config": {
        "audioFormat": "wav",
        "language": {
            "sourceLanguage": "hi",
            "sourceScriptCode": "Deva"
        },
        "encoding": "base64",
        "samplingRate": 0,
        "serviceId": service_id,
        "preProcessors": [],
        "postProcessors": [],
        "transcriptionFormat": {
            "value": "transcript"
        },
        "bestTokenCount": 0
    },
    "audio": [
        {
            "audioContent": audio_content
        }
    ]
}

# Headers
headers = {
    "accept": "application/json",
    "x-auth-source": x_auth_source,
    "Content-Type": "application/json",
    "Authorization": auth_token
}

# Test ASR request
print("TEST: ASR Transcription Request")
print("-" * 70)
url = f"{base_url}/services/inference/asr"
params = {"serviceId": service_id}
print(f"Full URL: {url}?serviceId={service_id}")
print(f"Payload size: {len(json.dumps(payload))} bytes")

try:
    print("\nSending request...")
    response = requests.post(url, params=params, json=payload, headers=headers, timeout=60)
    print(f"✓ Request sent successfully")
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} bytes")

    if response.status_code == 200:
        print("✅ SUCCESS!")
        try:
            data = response.json()
            if "output" in data:
                transcript = data['output'][0].get('source', '')
                print(f"Transcript: {transcript[:200]}...")
        except:
            pass
    else:
        print("❌ FAILED!")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
