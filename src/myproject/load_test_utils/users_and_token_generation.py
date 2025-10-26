import os
import time
import json
import queue
import random
import threading
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import requests
from loguru import logger

# Workflow:
# 1) Create N user entries (email/password) and save to test_data/users.json (idempotent).
# 2) Sign in users in parallel and write access_token to entries.
# 3) After MIN_SIGNED_BEFORE_REFRESH signed-in, start refresh worker pool that converts access_token -> refresh_token.
# 4) Persist results to test_data/users_tokens.json atomically.

BASE_URL = os.getenv("BASE_URL", "https://staging.example.com")
OUT_DIR = Path("test_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = OUT_DIR / "users.json"               # initial list of emails/passwords
TOKENS_FILE = OUT_DIR / "users_tokens.json"  
MIN_SIGNED_BEFORE_REFRESH = int(os.getenv("MIN_SIGNED_BEFORE_REFRESH", "4"))

SIGNIN_CONCURRENCY = int(os.getenv("SIGNIN_CONCURRENCY", "20"))
REFRESH_CONCURRENCY = int(os.getenv("REFRESH_CONCURRENCY", "8"))

THROTTLE_BETWEEN_CALLS = float(os.getenv("THROTTLE_SEC", "0.02"))  # 50 calls/sec roughly
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "2"))

EMAIL_PREFIX = os.getenv("EMAIL_PREFIX", "perf_test_user")
PASSWORD_TEMPLATE = os.getenv("PASSWORD_TEMPLATE", "Test@12345")
SIGNUP_PATH = "auth/signup"
SIGNIN_PATH = "auth/signin"
REFRESH_PATH = "auth/refresh"



def atomic_write_json(path: Path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except Exception:
        pass


