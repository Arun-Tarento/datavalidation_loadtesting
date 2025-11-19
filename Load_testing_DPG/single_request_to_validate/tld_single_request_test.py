"""
Test single TLD (Text Language Detection) request to debug issues
Can be run from any directory: python3 Load_testing_DPG/single_request_to_validate/tld_single_request_test.py
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
service_id = os.getenv("TLD_SERVICE_ID", "ai4bharat-indiclid")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

print("="*70)
print("TESTING TLD (TEXT LANGUAGE DETECTION) REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")

# Load TLD sample with robust path resolution
samples_file = "load_testing_test_samples/tld/tld_samples.json"
samples_path = os.path.join(project_root, samples_file)

print(f"\nLoading TLD samples from: {samples_path}")
try:
    with open(samples_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        tld_samples = data.get("tld_samples", [])
        print(f"Loaded {len(tld_samples)} TLD samples")

        if tld_samples:
            print(f"\n{'='*70}")
            print("Testing all samples:")
            print(f"{'='*70}\n")

            for idx, sample in enumerate(tld_samples, 1):
                source_text = sample.get("source", "")
                expected_lang = sample.get("expected_language", "unknown")

                print(f"Sample {idx}:")
                print(f"  Text: {source_text[:80]}...")
                print(f"  Expected Language: {expected_lang}")

                # Payload
                payload = {
                    "pipelineTasks": [
                        {
                            "taskType": "txt-lang-detection",
                            "config": {
                                "serviceId": service_id
                            }
                        }
                    ],
                    "inputData": {
                        "input": [
                            {
                                "source": source_text
                            }
                        ],
                        "audio": [
                            {}
                        ],
                        "image": [
                            {}
                        ]
                    },
                    "controlConfig": {
                        "dataTracking": True
                    }
                }

                # Headers
                headers = {
                    "accept": "application/json",
                    "x-auth-source": x_auth_source,
                    "Content-Type": "application/json",
                    "Authorization": auth_token
                }

                # Test TLD request
                url = f"{base_url}/services/inference/pipeline"

                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=60)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if "pipelineResponse" in data:
                                pipeline_response = data['pipelineResponse'][0]
                                lang_prediction_array = pipeline_response['output'][0].get('langPrediction', [])

                                if isinstance(lang_prediction_array, list) and len(lang_prediction_array) > 0:
                                    detected_lang = lang_prediction_array[0].get('langCode', '')
                                else:
                                    detected_lang = ''

                                match = "✅" if detected_lang == expected_lang else "❌"
                                print(f"  Detected Language: {detected_lang} {match}")
                        except Exception as e:
                            print(f"  ⚠️  Could not parse response: {e}")
                    else:
                        print(f"  ❌ FAILED! Status: {response.status_code}")
                        print(f"  Response: {response.text[:200]}")
                except Exception as e:
                    print(f"  ❌ EXCEPTION: {e}")

                print()

            print(f"{'='*70}")
            print("Detailed test of first sample:")
            print(f"{'='*70}\n")

            # Test first sample in detail
            first_sample = tld_samples[0]
            source_text = first_sample.get("source", "")
            expected_lang = first_sample.get("expected_language", "unknown")
        else:
            print("ERROR: No TLD samples found!")
            exit(1)
except Exception as e:
    print(f"ERROR loading samples: {e}")
    print(f"Looking for file at: {samples_path}")
    exit(1)

# Payload for detailed test
payload = {
    "pipelineTasks": [
        {
            "taskType": "txt-lang-detection",
            "config": {
                "serviceId": service_id
            }
        }
    ],
    "inputData": {
        "input": [
            {
                "source": source_text
            }
        ],
        "audio": [
            {}
        ],
        "image": [
            {}
        ]
    },
    "controlConfig": {
        "dataTracking": True
    }
}

# Headers
headers = {
    "accept": "application/json",
    "x-auth-source": x_auth_source,
    "Content-Type": "application/json",
    "Authorization": auth_token
}

# Test TLD request
print("TEST: TLD Language Detection Request")
print("-" * 70)
url = f"{base_url}/services/inference/pipeline"
print(f"Full URL: {url}")
print(f"Payload size: {len(json.dumps(payload))} bytes")
print(f"Sample text: {source_text[:100]}...")

try:
    print("\nSending request...")
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    print(f"✓ Request sent successfully")
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} bytes")

    if response.status_code == 200:
        print("✅ SUCCESS!")
        try:
            data = response.json()
            print(f"\nFull response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if "pipelineResponse" in data:
                pipeline_response = data['pipelineResponse'][0]
                lang_prediction_array = pipeline_response['output'][0].get('langPrediction', [])

                if isinstance(lang_prediction_array, list) and len(lang_prediction_array) > 0:
                    detected_lang_code = lang_prediction_array[0].get('langCode', '')
                    detected_lang_name = lang_prediction_array[0].get('language', '')
                    detected_script = lang_prediction_array[0].get('scriptCode', '')
                    lang_score = lang_prediction_array[0].get('langScore', '')
                else:
                    detected_lang_code = ''
                    detected_lang_name = ''
                    detected_script = ''
                    lang_score = ''

                print(f"\nExpected Language Code: {expected_lang}")
                print(f"Detected Language Code: {detected_lang_code}")
                print(f"Detected Language Name: {detected_lang_name}")
                print(f"Detected Script: {detected_script}")
                print(f"Confidence Score: {lang_score}")

                if detected_lang_code == expected_lang:
                    print("\n✅ Language detection matches expected!")
                else:
                    print(f"\n⚠️  Language detection does not match expected (expected: {expected_lang}, got: {detected_lang_code})")
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
