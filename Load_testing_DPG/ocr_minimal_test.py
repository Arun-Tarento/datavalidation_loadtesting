#!/usr/bin/env python3
"""
Minimal OCR test to debug why Postman works but Python doesn't
"""
import os
import json
import time
from dotenv import load_dotenv
import requests

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")
service_id = os.getenv("OCR_SERVICE_ID", "ai4bharat/surya-ocr-v1--gpu--t4")

print("="*70)
print("MINIMAL OCR TEST - Debugging Postman vs Python")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth Token (first 20 chars): {auth_token[:20]}...")
print()

# Load a small sample
samples_path = "load_testing_test_samples/ocr/ocr_samples.json"
with open(samples_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    ocr_samples = data.get("ocr_samples", [])
    valid_samples = [s for s in ocr_samples if s.get("imageContent") != "PLACEHOLDER_BASE64_IMAGE_HERE"]

    if not valid_samples:
        print("ERROR: No valid samples")
        exit(1)

    sample = valid_samples[0]
    image_content = sample.get("imageContent", "")
    language = sample.get("language", "hi")

print(f"Sample: {sample.get('description', 'N/A')}")
print(f"Image size: {len(image_content)} characters")
print()

# Try the exact payload structure
payload = {
    "pipelineTasks": [
        {
            "taskType": "ocr",
            "config": {
                "serviceId": service_id,
                "language": {
                    "sourceLanguage": language
                }
            }
        }
    ],
    "inputData": {
        "image": [
            {
                "imageContent": image_content
            }
        ]
    },
    "controlConfig": {
        "dataTracking": True
    }
}

# Print payload structure (without the huge base64)
payload_preview = json.loads(json.dumps(payload))
payload_preview['inputData']['image'][0]['imageContent'] = f"<{len(image_content)} chars>"
print("Payload structure:")
print(json.dumps(payload_preview, indent=2))
print()

# Try different header combinations
test_cases = [
    {
        "name": "Test 1: Standard headers",
        "headers": {
            "Authorization": auth_token,
            "x-auth-source": "AUTH_TOKEN",
            "Content-Type": "application/json",
            "accept": "application/json"
        }
    },
    {
        "name": "Test 2: Postman-like headers (User-Agent)",
        "headers": {
            "Authorization": auth_token,
            "x-auth-source": "AUTH_TOKEN",
            "Content-Type": "application/json",
            "accept": "application/json",
            "User-Agent": "PostmanRuntime/7.32.3"
        }
    },
    {
        "name": "Test 3: Minimal headers",
        "headers": {
            "Authorization": auth_token,
            "Content-Type": "application/json"
        }
    }
]

url = f"{base_url}/services/inference/pipeline"

for test_case in test_cases:
    print("="*70)
    print(test_case["name"])
    print("="*70)
    print("Headers:")
    for k, v in test_case["headers"].items():
        if k == "Authorization":
            print(f"  {k}: {v[:20]}...")
        else:
            print(f"  {k}: {v}")
    print()

    start_time = time.time()

    try:
        print("Sending request...")
        response = requests.post(
            url,
            json=payload,
            headers=test_case["headers"],
            timeout=10
        )

        elapsed = time.time() - start_time

        print(f"✅ Response received in {elapsed:.2f} seconds")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                if "pipelineResponse" in data:
                    print("✅ Valid OCR response received!")
                    output = data['pipelineResponse'][0].get('output', [])
                    if output:
                        text = output[0].get('text', output[0].get('content', ''))
                        print(f"OCR Text (first 100 chars): {text[:100]}")
                else:
                    print("⚠️  No pipelineResponse in response")
            except Exception as e:
                print(f"⚠️  Could not parse: {e}")
        else:
            print(f"❌ Error response: {response.text[:200]}")

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ TIMEOUT after {elapsed:.2f} seconds")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Exception after {elapsed:.2f} seconds: {e}")

    print()

print("="*70)
print("If all tests timeout, please share your Postman request details")
print("="*70)
