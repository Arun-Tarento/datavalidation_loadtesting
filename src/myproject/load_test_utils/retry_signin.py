#!/usr/bin/env python3
"""
Retry signin and token generation for specific users (by email or index).

Usage:
    # Retry specific users by email
    python retry_signin.py --emails user1@example.com user2@example.com

    # Retry specific users by index (0-based)
    python retry_signin.py --indices 0 5 10

    # Retry all users
    python retry_signin.py --all
"""

import asyncio
import httpx
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger
try:
    logger.remove()
except Exception:
    pass

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
if not BASE_URL.endswith("/"):
    BASE_URL += "/"

USERS_JSON_FILE = SCRIPT_DIR / "users.json"
OUTPUT_FILE = SCRIPT_DIR / "refresh_token.json"
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
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"✗ Invalid JSON in {file_path}: {str(e)}")
        sys.exit(1)


def load_existing_tokens(file_path: Path) -> Dict:
    """Load existing refresh tokens"""
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


async def signin_user(user: Dict, client: httpx.AsyncClient, user_index: int) -> Optional[Dict]:
    """Sign in a user and get token"""
    try:
        logger.info(f"Signing in user {user_index + 1}: {user['email']}")

        response = await client.post(
            f"{BASE_URL}auth/signin",
            json={
                "email": user["email"],
                "password": user["password"]
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            logger.success(f"✓ User {user_index + 1} signed in: {user['email']}")
            return {
                "user_index": user_index,
                "email": user["email"],
                "id": data.get("id"),
                "token": data.get("token"),
                "role": data.get("role")
            }
        else:
            logger.error(f"✗ Signin failed user {user_index + 1}: {response.status_code} - {response.text[:200]}")
            return None

    except Exception as e:
        logger.error(f"✗ Exception signin user {user_index + 1}: {str(e)}")
        return None


async def refresh_token(user_data: Dict, client: httpx.AsyncClient) -> Dict:
    """Use signin token to get refresh token"""
    try:
        user_index = user_data["user_index"]
        old_token = user_data["token"]

        logger.info(f"Refreshing token for user {user_index + 1}: {user_data['email']}")

        response = await client.post(
            f"{BASE_URL}auth/refresh",
            json={"token": old_token},
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            new_token = data.get("token")
            logger.success(f"✓ Token refreshed for user {user_index + 1}")
            return {
                "user_index": user_index,
                "email": user_data["email"],
                "old_token": old_token,
                "new_token": new_token,
                "refresh_successful": True
            }
        else:
            logger.error(f"✗ Refresh failed user {user_index + 1}: {response.status_code}")
            return {
                "user_index": user_index,
                "email": user_data["email"],
                "refresh_successful": False,
                "error": f"Status {response.status_code}"
            }

    except Exception as e:
        logger.error(f"✗ Exception refresh user {user_index + 1}: {str(e)}")
        return {
            "user_index": user_index,
            "email": user_data["email"],
            "refresh_successful": False,
            "error": str(e)
        }


async def retry_users(users_to_retry: List[tuple]):
    """Retry signin and refresh for specific users"""
    logger.info(f"\n{'='*70}")
    logger.info(f"Retrying {len(users_to_retry)} users")
    logger.info(f"BASE_URL: {BASE_URL}")
    logger.info(f"{'='*70}\n")

    signin_success = 0
    signin_failed = 0
    refresh_success = 0
    refresh_failed = 0

    async with httpx.AsyncClient() as client:
        # Step 1: Sign in
        logger.info("Step 1: Signing in users (2s delay between each)...")
        signed_in = []
        for i, (user_index, user) in enumerate(users_to_retry):
            if i > 0:
                await asyncio.sleep(2.0)  # 2 second delay between signin requests
            result = await signin_user(user, client, user_index)
            if result:
                signed_in.append(result)
                signin_success += 1
            else:
                signin_failed += 1

        logger.info(f"✓ Signed in: {len(signed_in)}/{len(users_to_retry)}\n")

        if not signed_in:
            logger.error("No users signed in successfully")
            return {}

        # Wait 2 seconds before starting refresh
        logger.info("Waiting 2 seconds before refreshing tokens...")
        await asyncio.sleep(2.0)

        # Step 2: Refresh tokens
        logger.info("Step 2: Refreshing tokens (2s delay between each)...")
        refresh_results = []
        for i, user in enumerate(signed_in):
            if i > 0:
                await asyncio.sleep(2.0)  # 2 second delay between refresh requests
            result = await refresh_token(user, client)
            refresh_results.append(result)
            if result.get("refresh_successful"):
                refresh_success += 1
            else:
                refresh_failed += 1

        logger.info(f"✓ Refreshed: {refresh_success}/{len(signed_in)}\n")

    # Update existing token file
    existing_tokens = load_existing_tokens(OUTPUT_FILE)

    for result in refresh_results:
        if result.get("refresh_successful"):
            email = result["email"]
            existing_tokens[email] = {
                "user_index": result["user_index"],
                "email": email,
                "old_token": result.get("old_token"),
                "new_token": result.get("new_token"),
                "refreshed_at": datetime.now().isoformat()
            }

    # Save updated tokens
    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing_tokens, f, indent=2)

    logger.success(f"✓ Updated {OUTPUT_FILE} with new tokens\n")

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Sign-ins:  {signin_success} success, {signin_failed} failed")
    logger.info(f"Refreshes: {refresh_success} success, {refresh_failed} failed")
    logger.info(f"Total tokens in file: {len(existing_tokens)}")
    logger.info(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Retry signin for specific users")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--emails", nargs="+", help="Email addresses to retry")
    group.add_argument("--indices", nargs="+", type=int, help="User indices (0-based) to retry")
    group.add_argument("--all", action="store_true", help="Retry all users")

    args = parser.parse_args()

    # Load all users
    all_users = load_users_from_json(USERS_JSON_FILE)

    # Determine which users to retry
    users_to_retry = []

    if args.all:
        users_to_retry = [(i, user) for i, user in enumerate(all_users)]
        logger.info(f"Retrying all {len(users_to_retry)} users")

    elif args.emails:
        for email in args.emails:
            for i, user in enumerate(all_users):
                if user["email"] == email:
                    users_to_retry.append((i, user))
                    break
            else:
                logger.warning(f"Email not found: {email}")
        logger.info(f"Found {len(users_to_retry)} users to retry")

    elif args.indices:
        for idx in args.indices:
            if 0 <= idx < len(all_users):
                users_to_retry.append((idx, all_users[idx]))
            else:
                logger.warning(f"Index out of range: {idx}")
        logger.info(f"Found {len(users_to_retry)} users to retry")

    if not users_to_retry:
        logger.error("No valid users to retry")
        sys.exit(1)

    # Retry the users
    asyncio.run(retry_users(users_to_retry))


if __name__ == "__main__":
    main()
