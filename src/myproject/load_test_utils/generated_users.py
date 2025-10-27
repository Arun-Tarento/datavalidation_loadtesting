#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

DEFAULT_COUNT = 1000
DEFAULT_PREFIX = "loadtestuser"
DEFAULT_DOMAIN = "example.com"
DEFAULT_PASSWORD = "password"

OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / "users.json"

def atomic_write(path: Path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except Exception:
        pass

def load_existing():
    if OUT_FILE.exists():
        try:
            data = json.loads(OUT_FILE.read_text())
            if isinstance(data, list):
                return data
        except Exception:
            return []
    return []

def generate_users(count: int, prefix: str, domain: str, password: str):
    existing = load_existing()
    existing_usernames = {entry.get("name") or entry.get("username") for entry in existing if isinstance(entry, dict)}
    users = existing.copy()
    # start index should be one after the max existing numbered suffix, not just len(existing)
    max_idx = 0
    for u in existing:
        uname = u.get("name") or u.get("username", "")
        if uname.startswith(prefix + "_"):
            try:
                n = int(uname.rsplit("_", 1)[1])
                if n > max_idx:
                    max_idx = n
            except Exception:
                pass
    start_index = max_idx + 1

    i = start_index
    while len(users) < count:
        name = f"{prefix}_{i:04d}"
        if name in existing_usernames:
            i += 1
            continue
        email = f"{name}@{domain}"
        users.append({
            "name": name,
            "email": email,
            "password": password
        })
        existing_usernames.add(name)
        i += 1

    return users[:count]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of user entries to generate")
    p.add_argument("--prefix", type=str, default=DEFAULT_PREFIX, help="name/email prefix")
    p.add_argument("--domain", type=str, default=DEFAULT_DOMAIN, help="Email domain")
    p.add_argument("--password", type=str, default=DEFAULT_PASSWORD, help="Password for all users")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    users = generate_users(args.count, args.prefix, args.domain, args.password)
    atomic_write(OUT_FILE, users)

    print(f"✅ Generated {len(users)} users in {OUT_FILE}")
    if users:
        print(f"Example entry: {users[0]}")

if __name__ == "__main__":
    main()
