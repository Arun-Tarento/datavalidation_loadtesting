import os
import time
import requests
from dotenv import load_dotenv

# Active environment is set by running: python testing/switch_env.py <staging|sandbox>
load_dotenv("testing/.env")
env = os.getenv("ENVIRONMENT", "staging")

base_url      = os.getenv("BASE_URL")
account_count = int(os.getenv("TEST_ACCOUNT_COUNT", 5))
email_pattern = os.getenv("TEST_ACCOUNT_EMAIL_PATTERN", "ltest_user_{}@test.com")
password      = os.getenv("TEST_ACCOUNT_PASSWORD", "Password@123")

print(f"Environment    : {env}")
print(f"Base URL       : {base_url}")
print(f"Users to create: {account_count}")
print("=" * 60)


def create_user(index):
    """Register a single test user. Returns True on success, None on rate limit."""
    payload = {
        "email":            email_pattern.format(index),
        "username":         f"ltest_user_{index}",
        "password":         password,
        "confirm_password": password,
        "full_name":        f"Load Test User {index}",
        "phone_number":     f"99099099{index:02d}",
        "timezone":         "UTC",
        "language":         "en",
        "is_tenant":        True
    }
    resp = requests.post(
        f"{base_url}/api/v1/auth/register",
        json=payload,
        timeout=30
    )

    if resp.status_code in [200, 201]:
        print(f"✅ [{index}/{account_count}] Created : {payload['email']}")
        return True
    elif resp.status_code == 409:
        print(f"⚠️  [{index}/{account_count}] Already exists: {payload['email']}")
        return True
    elif resp.status_code == 429:
        print(f"🚫 [{index}/{account_count}] Rate limited — stopping early.")
        return None
    else:
        print(f"❌ [{index}/{account_count}] Failed ({resp.status_code}): {resp.text[:150]}")
        return False


def main():
    success, failed = 0, 0

    for i in range(5, account_count + 1):
        result = create_user(i)

        if result is None:   # Rate limited — stop
            break
        elif result:
            success += 1
        else:
            failed += 1

        if i < account_count:
            time.sleep(5)

    print(f"\n{'=' * 60}")
    print(f"📊 Summary ({env}):")
    print(f"   Created : {success}/{account_count}")
    print(f"   Failed  : {failed}/{account_count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
