import requests
import time

# Configuration
base_url = "https://sandbox.ai4inclusion.org"
admin_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJhZG1pbkBhaTRpbmNsdXNpb24ub3JnIiwidXNlcm5hbWUiOiJhZG1pbiIsImV4cCI6MTc3MzU5MjAwMiwidHlwZSI6ImFjY2VzcyIsInJvbGVzIjpbIkFETUlOIl19.aejinaQKkeOK500Fj7h5_2HjsbeblyMWxNI_zlpO8Xc"
api_key = "ak_JijeEnGF0lBDbO45eZnYmmODzRb_U6GTtmzIYoOWPws"

headers = {
    "accept": "*/*",
    "Authorization": f"Bearer {admin_token}",
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

# Create 100 test users
success_count = 0
failed_count = 0

for i in range(1, 101):
    payload = {
        "email": f"ltest_user_{i}@test.com",
        "username": f"ltest_user_{i}",
        "password": "Password@123",
        "confirm_password": "Password@123",
        "full_name": f"Load Test User {i}",
        "phone_number": f"99099099{i:02d}",  # Generates unique phone numbers
        "timezone": "UTC",
        "language": "en",
        "is_tenant": True
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/register",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            success_count += 1
            print(f"✅ Created user {i}/100: ltest_user_{i}@test.com")
        else:
            failed_count += 1
            print(f"❌ Failed user {i}/100: {response.status_code} - {response.text[:100]}")
            
    except Exception as e:
        failed_count += 1
        print(f"❌ Exception for user {i}/100: {e}")
    
    # Small delay to avoid rate limiting
    time.sleep(10)

print("\n" + "="*60)
print(f"📊 Summary:")
print(f"   Successfully created: {success_count}/100")
print(f"   Failed: {failed_count}/100")
print("="*60)