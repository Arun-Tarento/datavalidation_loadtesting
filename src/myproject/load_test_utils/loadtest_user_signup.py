#!/usr/bin/env python3
"""
Concurrent user signup for load testing.

Flow:
1. Load users from users.json
2. Sign up users concurrently with configurable concurrency limit
3. Save signup results to signup_results.json
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

# Configure logger
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

USERS_JSON_FILE = SCRIPT_DIR / "users.json"
OUTPUT_FILE = SCRIPT_DIR / "signup_results.json"
MAX_CONCURRENT = int(os.getenv("SIGNUP_CONCURRENCY", "20"))
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


class SignupManager:
    """Manages concurrent user signup"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.stats = {
            "signup_success": 0,
            "signup_failed": 0,
        }

    async def signup_user(self, user: Dict, client: httpx.AsyncClient, user_index: int) -> Optional[Dict]:
        """Sign up a single user"""
        try:
            logger.info(f"Signing up user {user_index + 1}: {user['email']}")

            response = await client.post(
                f"{self.base_url}auth/signup",
                json={
                    "name": user["name"],
                    "email": user["email"],
                    "password": user["password"]
                },
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 201:
                data = response.json()
                self.stats["signup_success"] += 1
                logger.success(f"✓ User {user_index + 1} signed up: {user['email']}")
                return {
                    "user_index": user_index,
                    "name": user["name"],
                    "email": user["email"],
                    "id": data.get("id"),
                    "api_key": data.get("api_key"),
                    "role": data.get("role"),
                    "signed_up_at": datetime.now().isoformat()
                }
            else:
                self.stats["signup_failed"] += 1
                logger.error(f"✗ Signup failed user {user_index + 1}: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            self.stats["signup_failed"] += 1
            logger.error(f"✗ Exception signup user {user_index + 1}: {str(e)}")
            return None

    async def signup_users_concurrent(self, users: List[Dict]):
        """Process all users concurrently with semaphore"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Signing up {len(users)} users concurrently")
        logger.info(f"Max concurrent: {MAX_CONCURRENT}")
        logger.info(f"{'='*70}\n")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def signup_limited(user, index):
            async with semaphore:
                async with httpx.AsyncClient() as client:
                    return await self.signup_user(user, client, index)

        # Process in chunks to show progress
        total = len(users)
        chunk_size = 50
        all_results = []

        for chunk_start in range(0, total, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total)
            chunk = users[chunk_start:chunk_end]

            logger.info(f"Processing users {chunk_start + 1} to {chunk_end}...")

            tasks = [signup_limited(user, chunk_start + i) for i, user in enumerate(chunk)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = [r for r in results if r and not isinstance(r, Exception)]
            all_results.extend(successful)

            logger.info(f"✓ Chunk complete: {len(successful)}/{len(chunk)} successful")

        logger.info(f"\n✓ Total signed up: {len(all_results)}/{total}\n")
        return all_results

    def save_signup_results(self, signup_results: List[Dict], output_file: Path):
        """Save signup results to JSON"""
        logger.info(f"Saving signup results to {output_file}...")

        results_data = {
            "total_users": len(signup_results),
            "signed_up_at": datetime.now().isoformat(),
            "users": signup_results
        }

        with open(output_file, "w") as f:
            json.dump(results_data, f, indent=2)

        logger.success(f"✓ Saved {len(signup_results)} signup results to {output_file}\n")
        return results_data


async def main():
    """Main execution"""
    start_time = time.time()

    # Load users from JSON file
    USERS = load_users_from_json(USERS_JSON_FILE)

    logger.info(f"\n{'='*70}")
    logger.info(f"Load Test User Signup")
    logger.info(f"BASE_URL: {BASE_URL}")
    logger.info(f"Total users: {len(USERS)}")
    logger.info(f"Max concurrent: {MAX_CONCURRENT}")
    logger.info(f"{'='*70}\n")

    signup_manager = SignupManager(BASE_URL)

    # Sign up all users concurrently
    signup_results = await signup_manager.signup_users_concurrent(USERS)

    # Save signup results
    signup_manager.save_signup_results(signup_results, OUTPUT_FILE)

    # Summary
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Signups:   {signup_manager.stats['signup_success']} success, {signup_manager.stats['signup_failed']} failed")
    logger.info(f"Total time: {elapsed:.2f}s")
    logger.info(f"Avg per user: {elapsed/len(USERS):.3f}s")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
