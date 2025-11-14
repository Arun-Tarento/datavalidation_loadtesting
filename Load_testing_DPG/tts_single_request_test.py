"""
Test single TTS request to debug issues
Can be run from any directory: python3 Load_testing_DPG/tts_single_request_test.py
"""
import os
import json
from dotenv import load_dotenv
import requests

# Load environment - check script directory first, then project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Try to find .env file in script directory first, then project root
env_path = os.path.join(script_dir, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(project_root, '.env')

load_dotenv(env_path)

# Configuration
auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
x_auth_source = os.getenv("X_AUTH_SOURCE", "AUTH_TOKEN")
service_id = os.getenv("TTS_SERVICE_ID", "ai4bharat/indictts--gpu-t4")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")
source_language = os.getenv("TTS_SOURCE_LANGUAGE", "hi")
source_script = os.getenv("TTS_SOURCE_SCRIPT", "Deva")
gender = os.getenv("TTS_GENDER", "male")
sampling_rate = int(os.getenv("TTS_SAMPLING_RATE", "16000"))
audio_format = os.getenv("TTS_AUDIO_FORMAT", "wav")

print("="*70)
print("TESTING TTS REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")
print(f"Language: {source_language} ({source_script})")
print(f"Gender: {gender}")
print(f"Sampling Rate: {sampling_rate}")
print(f"Audio Format: {audio_format}")

# Load TTS sample with robust path resolution
samples_file = "load_testing_test_samples/tts/tts_samples.json"
samples_path = os.path.join(project_root, samples_file)

print(f"\nLoading TTS samples from: {samples_path}")
try:
    with open(samples_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        tts_samples = data.get("tts_samples", [])
        print(f"Loaded {len(tts_samples)} TTS samples")
        if tts_samples:
            source_text = tts_samples[0].get("source", "")
            print(f"Using sample text: {source_text[:100]}...")
        else:
            print("ERROR: No TTS samples found!")
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
        "serviceId": service_id,
        "gender": gender,
        "samplingRate": sampling_rate,
        "audioFormat": audio_format,
        "language": {
            "sourceLanguage": source_language,
            "sourceScriptCode": source_script
        }
    },
    "input": [
        {
            "source": source_text
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

# Test TTS request
print("TEST: TTS Synthesis Request")
print("-" * 70)
url = f"{base_url}/services/inference/tts"
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
            if "audio" in data:
                audio_content = data['audio'][0].get('audioContent', '')
                print(f"Audio content received: {len(audio_content)} characters (base64)")
                # Check if it looks like valid base64 audio
                if len(audio_content) > 1000:
                    print(f"Audio content sample (first 100 chars): {audio_content[:100]}...")
                else:
                    print("⚠️  Warning: Audio content seems too short")
        except Exception as e:
            print(f"⚠️  Could not parse response: {e}")
    else:
        print("❌ FAILED!")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
