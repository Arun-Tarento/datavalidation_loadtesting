from pathlib import Path
from dotenv import set_key, load_dotenv

def update_env_var(key: str, value: str, env_path: Path | str = ".env"):
    env_path = Path(env_path)
    load_dotenv(dotenv_path=env_path)
    set_key(str(env_path), key, value)
