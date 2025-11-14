"""
Test single Transliteration request to debug issues
Can be run from any directory: python3 Load_testing_DPG/transliteration_single_request_test.py
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
service_id = os.getenv("TRANSLITERATION_SERVICE_ID", "ai4bharat-transliteration")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")
source_language = os.getenv("TRANSLITERATION_SOURCE_LANGUAGE", "en")
source_script = os.getenv("TRANSLITERATION_SOURCE_SCRIPT", "Latn")
target_language = os.getenv("TRANSLITERATION_TARGET_LANGUAGE", "hi")
target_script = os.getenv("TRANSLITERATION_TARGET_SCRIPT", "Deva")
is_sentence = os.getenv("TRANSLITERATION_IS_SENTENCE", "true").lower() == "true"
num_suggestions = int(os.getenv("TRANSLITERATION_NUM_SUGGESTIONS", "0"))

print("="*70)
print("TESTING TRANSLITERATION REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")
print(f"Source: {source_language} ({source_script})")
print(f"Target: {target_language} ({target_script})")
print(f"Is Sentence: {is_sentence}")
print(f"Num Suggestions: {num_suggestions}")

# Load Transliteration sample with robust path resolution
samples_file = "load_testing_test_samples/transliteration/transliteration_samples.json"
samples_path = os.path.join(project_root, samples_file)

print(f"\nLoading Transliteration samples from: {samples_path}")
try:
    with open(samples_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        transliteration_samples = data.get("transliteration_samples", [])
        print(f"Loaded {len(transliteration_samples)} Transliteration samples")
        if transliteration_samples:
            source_text = transliteration_samples[0].get("source", "")
            print(f"Using sample text: {source_text}")
        else:
            print("ERROR: No Transliteration samples found!")
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
        "language": {
            "sourceLanguage": source_language,
            "sourceScriptCode": source_script,
            "targetLanguage": target_language,
            "targetScriptCode": target_script
        },
        "isSentence": is_sentence,
        "numSuggestions": num_suggestions
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

# Test Transliteration request
print("TEST: Transliteration Request")
print("-" * 70)
url = f"{base_url}/services/inference/transliteration"
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
            print(f"\nFull response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            if "output" in data:
                transliterated_text = data['output'][0].get('target', '')
                print(f"\nOriginal text: {source_text}")
                print(f"Transliterated text: {transliterated_text}")
                print(f"Transliterated text type: {type(transliterated_text)}")
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
