"""
Quick script to check if NMT API returns timing headers
Usage: ENV=sandbox python testing/AI4I/loadtesting/NMT/check_timing_headers.py
"""
import os
import requests
import json
from dotenv import load_dotenv

env = os.getenv("ENV", "staging")
load_dotenv(f"testing/.{env}.env", override=True)

base_url = os.getenv("BASE_URL")

# Login first
login_response = requests.post(
    f"{base_url}/api/v1/auth/login",
    json={
        "email": os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com").format(1),
        "password": os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123"),
        "remember_me": False
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    exit(1)

access_token = login_response.json()["access_token"]
print(f"✅ Login successful\n")

# Make NMT request
nmt_response = requests.post(
    f"{base_url}/api/v1/nmt/inference",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json={
        "input": [{"source": "नमस्ते"}],
        "config": {
            "serviceId": os.getenv("NMT_SERVICE_ID"),
            "language": {
                "sourceLanguage": "hi",
                "targetLanguage": "en"
            }
        },
        "controlConfig": {"additionalProp1": {"dataTracking": False}}
    }
)

print(f"NMT Response Status: {nmt_response.status_code}")
print(f"Total Response Time: {nmt_response.elapsed.total_seconds():.3f}s\n")

if nmt_response.status_code != 200:
    print("ERROR RESPONSE:")
    print(nmt_response.text)
    print()

print("=" * 80)
print("RESPONSE HEADERS:")
print("=" * 80)

print(nmt_response.headers)

# for header, value in sorted(nmt_response.headers.items()):
#     # Highlight timing-related headers
#     if any(keyword in header.lower() for keyword in ['time', 'timing', 'duration', 'process', 'inference']):
#         print(f"⏱️  {header}: {value}")
#     else:
#         print(f"   {header}: {value}")

# print("\n" + "=" * 80)
# print("LOOK FOR HEADERS LIKE:")
# print("=" * 80)
# print("  - X-Inference-Time, X-Processing-Time")
# print("  - Server-Timing (standard header)")
# print("  - X-Response-Time, X-Runtime")
# print("  - Any custom timing headers")
