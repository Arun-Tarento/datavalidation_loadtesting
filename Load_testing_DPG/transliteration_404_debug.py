#!/usr/bin/env python3
"""
Debug script to check what the transliteration 404 response looks like
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("AUTH_TOKEN", "").strip('"')
base_url = os.getenv("BASE_URL", "http://13.204.164.186:8000")

headers = {
    "Authorization": auth_token,
    "x-auth-source": "AUTH_TOKEN",
    "Content-Type": "application/json",
    "accept": "application/json"
}

print("Testing transliteration 404 error response...")
print()

payload = {
    "controlConfig": {"dataTracking": True},
    "config": {
        "serviceId": "ai4bharat/non-existent-transliteration-service-404",
        "language": {
            "sourceLanguage": "hi",
            "sourceScriptCode": "Deva",
            "targetLanguage": "hi",
            "targetScriptCode": "Latn"
        },
        "isSentence": False,
        "numSuggestions": 5
    },
    "input": [{"source": "नमस्ते"}]
}

response = requests.post(
    f"{base_url}/services/inference/transliteration",
    json=payload,
    headers=headers,
    timeout=30
)

print(f"Status Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print()
print("Response Body:")
print(response.text)
print()

try:
    response_json = response.json()
    print("JSON Response:")
    print(json.dumps(response_json, indent=2))
except:
    print("Could not parse as JSON")
