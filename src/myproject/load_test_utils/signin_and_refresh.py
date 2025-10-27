"""
User sign-in and refresh token generation for load testing.

Prerequisites: Users must already be signed up (use loadtest_user_signup.py first)

Flow:
1. Load users from users.json
2. Sign in first batch of users (with delay between each) → get tokens
3. Use those tokens to refresh (with delay between each)
4. Process remaining users concurrently for signin → refresh
5. Save refresh tokens to refresh_token.json
"""

import asyncio
import httpx
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger - safer approach
try:
    logger.remove()  # Remove default handler
except Exception:
    pass  # Ignore if no handlers to remove

logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
)

# Get the directory where THIS script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()
if ENVIRONMENT == "test":
    BASE_URL = os.getenv("BASE_URL_TEST", "http://15.206.184.161:8000/")
else:
    BASE_URL = os.getenv("BASE_URL_DEV", "http://localhost:8001/")
# Ensure trailing slash
if not BASE_URL.endswith("/"):
    BASE_URL += "/"
USERS_JSON_FILE = SCRIPT_DIR / "users.json"  # Look for user.json in script's directory
OUTPUT_FILE = SCRIPT_DIR / "refresh_token.json"  # Save output in script's directory
INITIAL_BATCH_SIZE = int(os.getenv("MIN_SIGNED_BEFORE_REFRESH", "5"))
SIGNIN_DELAY = float(os.getenv("THROTTLE_BETWEEN_CALLS", "2.0"))
REFRESH_DELAY = float(os.getenv("THROTTLE_BETWEEN_CALLS", "2.0"))
SIGNIN_CONCURRENCY = int(os.getenv("SIGNIN_CONCURRENCY", "20"))
REFRESH_CONCURRENCY = int(os.getenv("REFRESH_CONCURRENCY", "8"))
REQUEST_TIMEOUT = 30.0


def load_users_from_json(file_path: Path) -> List[Dict]:
    """Load users from JSON file"""
    try:
        with open(file_path, 'r') as f:
            users = json.load(f)
        logger.info(f"✓ Loaded {len(users)} users from {file_path}")
        return users
    except FileNotFoundError:
        logger.error(f"✗ File not found: {file_path}")
        logger.error(f"✗ Script directory: {SCRIPT_DIR}")
        logger.error(f"✗ Looking for file at: {file_path.absolute()}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"✗ Invalid JSON in {file_path}: {str(e)}")
        sys.exit(1)


class AuthManager:
    """Manages signin → refresh flow for load testing"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.stats = {
            "signin_success": 0,
            "signin_failed": 0,
            "refresh_success": 0,
            "refresh_failed": 0,
        }

    async def signin_user(self, user: Dict, client: httpx.AsyncClient, user_index: int) -> Optional[Dict]:
        """Sign in a user and get token"""
        try:
            logger.info(f"Signing in user {user_index + 1}: {user['email']}")

            response = await client.post(
                f"{self.base_url}auth/signin",
                json={
                    "email": user["email"],
                    "password": user["password"]
                },
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                self.stats["signin_success"] += 1
                logger.success(f"✓ User {user_index + 1} signed in: {user['email']}")
                return {
                    "user_index": user_index,
                    "email": user["email"],
                    "id": data.get("id"),
                    "token": data.get("token"),  # This token will be used for refresh
                    "role": data.get("role")
                }
            else:
                self.stats["signin_failed"] += 1
                logger.error(f"✗ Signin failed user {user_index + 1}: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            self.stats["signin_failed"] += 1
            logger.error(f"✗ Exception signin user {user_index + 1}: {str(e)}")
            return None

    async def refresh_token(self, user_data: Dict, client: httpx.AsyncClient) -> Dict:
        """Use signin token to get refresh token"""
        try:
            user_index = user_data["user_index"]
            old_token = user_data["token"]

            logger.info(f"Refreshing token for user {user_index + 1}: {user_data['email']}")

            response = await client.post(
                f"{self.base_url}auth/refresh",
                json={"token": old_token},
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                new_token = data.get("token")
                self.stats["refresh_success"] += 1
                logger.success(f"✓ Token refreshed for user {user_index + 1}")
                return {
                    "user_index": user_index,
                    "email": user_data["email"],
                    "old_token": old_token,
                    "new_token": new_token,
                    "refresh_successful": True
                }
            else:
                self.stats["refresh_failed"] += 1
                error_detail = response.text[:200] if response.text else "No error message"
                logger.error(f"✗ Refresh failed user {user_index + 1}: {response.status_code} - {error_detail}")
                return {
                    "user_index": user_index,
                    "email": user_data["email"],
                    "refresh_successful": False,
                    "error": f"Status {response.status_code}: {error_detail}"
                }

        except Exception as e:
            self.stats["refresh_failed"] += 1
            logger.error(f"✗ Exception refresh user {user_index + 1}: {str(e)}")
            return {
                "user_index": user_index,
                "email": user_data["email"],
                "refresh_successful": False,
                "error": str(e)
            }

    async def process_initial_batch(self, users: List[Dict], batch_size: int):
        """Process first batch: signin → refresh with delays"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing first {batch_size} users (sequential with delays)")
        logger.info(f"{'='*70}\n")

        # Step 1: Sign in users (with delay between each)
        logger.info(f"Step 1: Signing in {batch_size} users ({SIGNIN_DELAY}s delay between each)...")
        signed_in = []
        async with httpx.AsyncClient() as client:
            for i in range(min(batch_size, len(users))):
                if i > 0:
                    await asyncio.sleep(SIGNIN_DELAY)
                result = await self.signin_user(users[i], client, i)
                if result:
                    signed_in.append(result)

        logger.info(f"✓ Signed in: {len(signed_in)}/{batch_size}\n")

        if not signed_in:
            logger.error("No users signed in. Cannot refresh tokens.")
            return []

        # Wait 2 seconds before starting refresh
        logger.info("Waiting 2 seconds before refreshing tokens...")
        await asyncio.sleep(2.0)

        # Step 2: Refresh tokens (with delay between each)
        logger.info(f"Step 2: Refreshing tokens for {len(signed_in)} users ({REFRESH_DELAY}s delay between each)...")
        refresh_results = []
        async with httpx.AsyncClient() as client:
            for i, user in enumerate(signed_in):
                if i > 0:
                    await asyncio.sleep(REFRESH_DELAY)
                result = await self.refresh_token(user, client)
                refresh_results.append(result)

        successful_refreshes = len([r for r in refresh_results if r.get("refresh_successful")])
        logger.info(f"✓ Refreshed: {successful_refreshes}/{len(signed_in)}\n")

        return refresh_results

    async def process_remaining_users_concurrent(self, remaining_users: List[Dict], start_index: int):
        """Process remaining users concurrently: signin → refresh in batches"""
        if not remaining_users:
            logger.info("No remaining users to process.\n")
            return []

        logger.info(f"\n{'='*70}")
        logger.info(f"Processing remaining {len(remaining_users)} users in batches")
        logger.info(f"Signin concurrency: {SIGNIN_CONCURRENCY} | Refresh concurrency: {REFRESH_CONCURRENCY}")
        logger.info(f"{'='*70}\n")

        all_refresh_results = []

        # Process in batches to avoid overwhelming the server
        batch_size = SIGNIN_CONCURRENCY * 2  # Process 2x concurrency at a time
        total_batches = (len(remaining_users) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            batch_start = batch_num * batch_size
            batch_end = min(batch_start + batch_size, len(remaining_users))
            batch = remaining_users[batch_start:batch_end]

            logger.info(f"\nBatch {batch_num + 1}/{total_batches}: Processing users {start_index + batch_start + 1} to {start_index + batch_end}")

            # Step 1: Concurrent signin for this batch
            logger.info(f"  Signing in {len(batch)} users...")
            signin_semaphore = asyncio.Semaphore(SIGNIN_CONCURRENCY)

            async def signin_limited(user, index):
                async with signin_semaphore:
                    try:
                        async with httpx.AsyncClient() as client:
                            result = await self.signin_user(user, client, index)
                            return result
                    except Exception as e:
                        logger.error(f"  ✗ Signin exception for user {index + 1}: {str(e)}")
                        return None

            signin_tasks = [signin_limited(user, start_index + batch_start + i) for i, user in enumerate(batch)]
            signin_results = await asyncio.gather(*signin_tasks, return_exceptions=False)
            signed_in = [r for r in signin_results if r is not None]

            logger.info(f"  ✓ Signed in: {len(signed_in)}/{len(batch)}")

            if not signed_in:
                logger.warning(f"  ⚠ No users signed in for batch {batch_num + 1}, skipping refresh")
                continue

            # Wait 2 seconds before refreshing this batch
            logger.info(f"  Waiting 2 seconds before refreshing...")
            await asyncio.sleep(2.0)

            # Step 2: Concurrent refresh for signed-in users
            logger.info(f"  Refreshing {len(signed_in)} tokens...")
            refresh_semaphore = asyncio.Semaphore(REFRESH_CONCURRENCY)

            async def refresh_limited(user_data):
                async with refresh_semaphore:
                    try:
                        async with httpx.AsyncClient() as client:
                            result = await self.refresh_token(user_data, client)
                            return result
                    except Exception as e:
                        logger.error(f"  ✗ Refresh exception for user {user_data.get('user_index', '?') + 1}: {str(e)}")
                        return {
                            "user_index": user_data.get("user_index"),
                            "email": user_data.get("email"),
                            "refresh_successful": False,
                            "error": str(e)
                        }

            refresh_tasks = [refresh_limited(user) for user in signed_in]
            refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=False)
            batch_refresh_results = [r for r in refresh_results if r is not None]

            successful_refreshes = len([r for r in batch_refresh_results if r.get("refresh_successful")])
            logger.info(f"  ✓ Refreshed: {successful_refreshes}/{len(signed_in)}")

            all_refresh_results.extend(batch_refresh_results)

            # Small delay between batches to avoid overwhelming server
            if batch_num < total_batches - 1:
                logger.info(f"  Waiting 1 second before next batch...")
                await asyncio.sleep(1.0)

        logger.info(f"\n✓ All batches complete: {len(all_refresh_results)} total refresh attempts\n")
        return all_refresh_results

    def save_refresh_tokens(self, refresh_results: List[Dict], output_file: Path):
        """Save refresh tokens to JSON"""
        logger.info(f"Saving refresh tokens to {output_file}...")

        token_data = {}
        for result in refresh_results:
            if result.get("refresh_successful"):
                email = result["email"]
                token_data[email] = {
                    "user_index": result["user_index"],
                    "email": email,
                    "old_token": result.get("old_token"),
                    "new_token": result.get("new_token"),
                    "refreshed_at": datetime.now().isoformat()
                }

        with open(output_file, "w") as f:
            json.dump(token_data, f, indent=2)

        logger.success(f"✓ Saved {len(token_data)} refresh tokens to {output_file}\n")
        return token_data


async def main():
    """Main execution"""
    start_time = time.time()

    # Load users from JSON file
    USERS = load_users_from_json(USERS_JSON_FILE)

    logger.info(f"\n{'='*70}")
    logger.info(f"Load Test: Signin → Refresh Token Generation")
    logger.info(f"BASE_URL: {BASE_URL}")
    logger.info(f"Total users: {len(USERS)}")
    logger.info(f"Initial batch (sequential): {INITIAL_BATCH_SIZE}")
    logger.info(f"Signin delay: {SIGNIN_DELAY}s | Refresh delay: {REFRESH_DELAY}s")
    logger.info(f"Remaining users: Signin concurrency={SIGNIN_CONCURRENCY}, Refresh concurrency={REFRESH_CONCURRENCY}")
    logger.info(f"{'='*70}\n")

    if len(USERS) < INITIAL_BATCH_SIZE:
        logger.error(f"Need at least {INITIAL_BATCH_SIZE} users")
        return

    auth_manager = AuthManager(BASE_URL)

    # Process first batch: signin → refresh (sequential with delays)
    initial_refresh_results = await auth_manager.process_initial_batch(
        USERS[:INITIAL_BATCH_SIZE],
        INITIAL_BATCH_SIZE
    )

    # Process remaining users: signin → refresh (concurrent)
    remaining_users = USERS[INITIAL_BATCH_SIZE:]
    remaining_refresh_results = []
    if remaining_users:
        remaining_refresh_results = await auth_manager.process_remaining_users_concurrent(
            remaining_users,
            INITIAL_BATCH_SIZE
        )

    # Combine all refresh results
    all_refresh_results = initial_refresh_results + remaining_refresh_results

    # Save refresh tokens
    token_data = auth_manager.save_refresh_tokens(all_refresh_results, OUTPUT_FILE)

    # Summary
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Sign-ins:  {auth_manager.stats['signin_success']} success, {auth_manager.stats['signin_failed']} failed")
    logger.info(f"Refreshes: {auth_manager.stats['refresh_success']} success, {auth_manager.stats['refresh_failed']} failed")
    logger.info(f"Tokens saved: {len(token_data)}")
    logger.info(f"Total time: {elapsed:.2f}s")
    logger.info(f"Avg per user: {elapsed/len(USERS):.3f}s")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())