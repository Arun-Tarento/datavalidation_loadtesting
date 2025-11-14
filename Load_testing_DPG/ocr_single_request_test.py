"""
Test single OCR (Optical Character Recognition) request to debug issues
Can be run from any directory: python3 Load_testing_DPG/ocr_single_request_test.py
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
service_id = os.getenv("OCR_SERVICE_ID", "ai4bharat/surya-ocr-v1--gpu--t4")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

print("="*70)
print("TESTING OCR (OPTICAL CHARACTER RECOGNITION) REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")

# Load OCR sample with robust path resolution
samples_file = "load_testing_test_samples/ocr/ocr_samples.json"
samples_path = os.path.join(project_root, samples_file)

print(f"\nLoading OCR samples from: {samples_path}")
try:
    with open(samples_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        ocr_samples = data.get("ocr_samples", [])
        # Filter out placeholder samples
        valid_samples = [s for s in ocr_samples if s.get("imageContent") != "PLACEHOLDER_BASE64_IMAGE_HERE"]

        print(f"Loaded {len(ocr_samples)} OCR samples ({len(valid_samples)} valid)")

        if len(valid_samples) == 0:
            print("\n" + "="*70)
            print("⚠️  NO VALID IMAGE SAMPLES FOUND")
            print("="*70)
            print("\nPlease add base64 encoded images to ocr_samples.json")
            print("\nTo encode an image to base64:")
            print("  1. Linux/Mac: base64 -w 0 image.png > image.base64")
            print("  2. Or use Python:")
            print("     import base64")
            print("     with open('image.png', 'rb') as f:")
            print("         b64 = base64.b64encode(f.read()).decode()")
            print("         print(b64)")
            print("\nThen replace 'PLACEHOLDER_BASE64_IMAGE_HERE' in ocr_samples.json")
            print("="*70)
            exit(1)

        if valid_samples:
            print(f"\n{'='*70}")
            print("Testing all valid samples:")
            print(f"{'='*70}\n")

            for idx, sample in enumerate(valid_samples, 1):
                image_content = sample.get("imageContent", "")
                language = sample.get("language", "hi")
                description = sample.get("description", "No description")

                print(f"Sample {idx} (Language: {language}):")
                print(f"  Description: {description}")
                print(f"  Image size: {len(image_content)} characters (base64)")

                # Payload
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

                # Headers
                headers = {
                    "accept": "application/json",
                    "x-auth-source": x_auth_source,
                    "Content-Type": "application/json",
                    "Authorization": auth_token
                }

                # Test OCR request - using direct OCR endpoint
                url = f"{base_url}/services/inference/pipeline/ocr"

                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=120)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if "pipelineResponse" in data and len(data['pipelineResponse']) > 0:
                                output = data['pipelineResponse'][0].get('output', [])
                                if len(output) > 0:
                                    ocr_text = output[0].get('text', output[0].get('content', ''))
                                    print(f"  ✅ SUCCESS!")
                                    print(f"  OCR Text: {ocr_text[:100]}...")
                                else:
                                    print(f"  ⚠️  Response missing output")
                            else:
                                print(f"  ⚠️  Response missing pipelineResponse")
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
            first_sample = valid_samples[0]
            image_content = first_sample.get("imageContent", "")
            language = first_sample.get("language", "hi")
            description = first_sample.get("description", "No description")
        else:
            print("ERROR: No valid OCR samples found!")
            exit(1)
except Exception as e:
    print(f"ERROR loading samples: {e}")
    print(f"Looking for file at: {samples_path}")
    exit(1)

# Payload for detailed test
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

# Headers
headers = {
    "accept": "application/json",
    "x-auth-source": x_auth_source,
    "Content-Type": "application/json",
    "Authorization": auth_token
}

# Test OCR request - using direct OCR endpoint
print("TEST: OCR Request")
print("-" * 70)
url = f"{base_url}/services/inference/pipeline/ocr"
print(f"Full URL: {url}")
print(f"Payload size: {len(json.dumps(payload))} bytes")
print(f"Language: {language}")
print(f"Description: {description}")
print(f"Image size: {len(image_content)} characters (base64)")

try:
    print("\nSending request...")
    response = requests.post(url, json=payload, headers=headers, timeout=120)
    print(f"✓ Request sent successfully")
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} bytes")

    if response.status_code == 200:
        print("✅ SUCCESS!")
        try:
            data = response.json()
            print(f"\nFull response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if "pipelineResponse" in data and len(data['pipelineResponse']) > 0:
                pipeline_response = data['pipelineResponse'][0]
                output = pipeline_response.get('output', [])

                if len(output) > 0:
                    output_data = output[0]
                    ocr_text = output_data.get('text', output_data.get('content', ''))

                    print(f"\nAvailable fields in output: {list(output_data.keys())}")
                    print(f"\n{'='*70}")
                    print("OCR Extracted Text:")
                    print(f"{'='*70}")
                    print(ocr_text)
                    print(f"{'='*70}")
        except Exception as e:
            print(f"⚠️  Could not parse response: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ FAILED!")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
