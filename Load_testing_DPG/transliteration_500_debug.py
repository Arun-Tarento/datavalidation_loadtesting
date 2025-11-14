#!/usr/bin/env python3
"""
Debug script to find what triggers 500 errors for transliteration
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")
service_id = os.getenv("TRANSLITERATION_SERVICE_ID", "ai4bharat/indicxlit--cpu-fsv2")

headers = {
    "Authorization": auth_token,
    "x-auth-source": "AUTH_TOKEN",
    "Content-Type": "application/json",
    "accept": "application/json"
}

print("Testing different approaches to trigger 500 errors for transliteration...")
print("="*70)
print()

# Test 1: Empty input array
print("Test 1: Empty input array")
payload1 = {
    "controlConfig": {"dataTracking": True},
    "config": {
        "serviceId": service_id,
        "language": {
            "sourceLanguage": "hi",
            "sourceScriptCode": "Deva",
            "targetLanguage": "hi",
            "targetScriptCode": "Latn"
        },
        "isSentence": False,
        "numSuggestions": 5
    },
    "input": []  # Empty
}

try:
    response = requests.post(
        f"{base_url}/services/inference/transliteration",
        json=payload1,
        headers=headers,
        timeout=30
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
print()

# Test 2: Missing source field
print("Test 2: Missing 'source' field in input")
payload2 = {
    "controlConfig": {"dataTracking": True},
    "config": {
        "serviceId": service_id,
        "language": {
            "sourceLanguage": "hi",
            "sourceScriptCode": "Deva",
            "targetLanguage": "hi",
            "targetScriptCode": "Latn"
        },
        "isSentence": False,
        "numSuggestions": 5
    },
    "input": [{}]  # Empty dict - missing 'source'
}

try:
    response = requests.post(
        f"{base_url}/services/inference/transliteration",
        json=payload2,
        headers=headers,
        timeout=30
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
print()

# Test 3: Invalid language code
print("Test 3: Invalid language code")
payload3 = {
    "controlConfig": {"dataTracking": True},
    "config": {
        "serviceId": service_id,
        "language": {
            "sourceLanguage": "INVALID_LANG_CODE_XYZ",
            "sourceScriptCode": "Deva",
            "targetLanguage": "hi",
            "targetScriptCode": "Latn"
        },
        "isSentence": False,
        "numSuggestions": 5
    },
    "input": [{"source": "नमस्ते"}]
}

try:
    response = requests.post(
        f"{base_url}/services/inference/transliteration",
        json=payload3,
        headers=headers,
        timeout=30
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
print()

# Test 4: Invalid script code
print("Test 4: Invalid script code")
payload4 = {
    "controlConfig": {"dataTracking": True},
    "config": {
        "serviceId": service_id,
        "language": {
            "sourceLanguage": "hi",
            "sourceScriptCode": "INVALID_SCRIPT",
            "targetLanguage": "hi",
            "targetScriptCode": "Latn"
        },
        "isSentence": False,
        "numSuggestions": 5
    },
    "input": [{"source": "नमस्ते"}]
}

try:
    response = requests.post(
        f"{base_url}/services/inference/transliteration",
        json=payload4,
        headers=headers,
        timeout=30
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
print()

# Test 5: Malformed config (missing required fields)
print("Test 5: Missing required config fields")
payload5 = {
    "controlConfig": {"dataTracking": True},
    "config": {
        "serviceId": service_id
        # Missing language config
    },
    "input": [{"source": "नमस्ते"}]
}

try:
    response = requests.post(
        f"{base_url}/services/inference/transliteration",
        json=payload5,
        headers=headers,
        timeout=30
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
print()

print("="*70)
print("Summary: Check which test produced 500 errors above")
