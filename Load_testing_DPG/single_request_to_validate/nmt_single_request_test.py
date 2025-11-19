"""
Test single NMT request to debug issues
Can be run from any directory: python3 Load_testing_DPG/single_request_to_validate/nmt_single_request_test.py
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
service_id = os.getenv("NMT_SERVICE_ID", "ai4bharat/indictrans--gpu-t4")
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

print("="*70)
print("TESTING NMT REQUEST")
print("="*70)
print(f"Base URL: {base_url}")
print(f"Service ID: {service_id}")
print(f"Auth token (first 50 chars): {auth_token[:50]}...")
print()

# Payload
payload = {
    "controlConfig": {
        "dataTracking": True
    },
    "config": {
        "serviceId": service_id,
        "language": {
            "sourceLanguage": "hi",
            "sourceScriptCode": "Deva",
            "targetLanguage": "ta",
            "targetScriptCode": "Taml"
        }
    },
    "input": [
        {
            "source": "आर्टिफिशियल इंटेलिजेंस के क्षेत्र में भारत की तरक्की कमाल की है"
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

# Test 1: Using json= parameter (Locust style)
print("TEST 1: Using json= parameter (like Locust)")
print("-" * 70)
url = f"{base_url}/services/inference/translation"
params = {"serviceId": service_id}
print(f"Full URL will be: {url}?serviceId={service_id}")

try:
    response = requests.post(url, params=params, json=payload, headers=headers, timeout=30)
    print(f"✓ Request sent successfully")
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} bytes")

    if response.status_code == 200:
        print("✅ SUCCESS!")
        try:
            data = response.json()
            if "output" in data:
                print(f"Translation output: {data['output'][0].get('target', '')[:100]}...")
        except:
            pass
    else:
        print("❌ FAILED!")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n")

# Test 2: Using data= parameter (your working style)
print("TEST 2: Using data= parameter (like your working code)")
print("-" * 70)
payload_str = json.dumps(payload)

try:
    response2 = requests.post(url, params=params, data=payload_str, headers=headers, timeout=30)
    print(f"✓ Request sent successfully")
    print(f"Status Code: {response2.status_code}")
    print(f"Response Length: {len(response2.text)} bytes")

    if response2.status_code == 200:
        print("✅ SUCCESS!")
        try:
            data = response2.json()
            if "output" in data:
                print(f"Translation output: {data['output'][0].get('target', '')[:100]}...")
        except:
            pass
    else:
        print("❌ FAILED!")
        print(f"Response: {response2.text[:500]}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
