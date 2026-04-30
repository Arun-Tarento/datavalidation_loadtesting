import sys
import shutil
from pathlib import Path


VALID_ENVS = ["staging", "sandbox"]


def switch_environment(env_name):
    """Switch to specified environment by copying env file to testing/.env"""
    src = Path(f"testing/.{env_name}.env")
    target = Path("testing/.env")

    if env_name not in VALID_ENVS:
        print(f"❌ Unknown environment '{env_name}'. Valid options: {', '.join(VALID_ENVS)}")
        sys.exit(1)

    if not src.exists():
        print(f"❌ Environment file not found: {src}")
        sys.exit(1)

    shutil.copy(src, target)
    print(f"✅ Switched to '{env_name}' environment")
    print(f"   Source : {src}")
    print(f"   Active : {target}")


def show_current():
    """Show the currently active environment."""
    target = Path("testing/.env")
    if not target.exists():
        print("⚠️  No active environment. Run: python testing/switch_env.py <staging|sandbox>")
        return
    for line in target.read_text().splitlines():
        if line.startswith("ENVIRONMENT="):
            print(f"🌍 Current environment: {line.split('=', 1)[1]}")
            return
    print("⚠️  Could not determine current environment from testing/.env")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_current()
    elif len(sys.argv) == 2:
        switch_environment(sys.argv[1])
    else:
        print("Usage:")
        print("  python testing/switch_env.py              # show current env")
        print("  python testing/switch_env.py staging      # switch to staging")
        print("  python testing/switch_env.py sandbox      # switch to sandbox")
        sys.exit(1)
