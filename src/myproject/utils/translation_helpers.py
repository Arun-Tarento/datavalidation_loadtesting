import base64
import re
from pathlib import Path
from jiwer import wer as jiwer_wer
from myproject.db import SessionLocal, engine, Base
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv


_here = Path(__file__).resolve().parent
_env_candidates = [ _here / ".env",            
    _here.parent / ".env",     
    _here.parent.parent / ".env",  
    _here.parent.parent.parent / ".env"  ]
for p in _env_candidates:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break
    load_dotenv()

service_id = os.getenv("TRANSLATION_SERVICEID")


def translation_payload(
    service_id: str,
    source_text: str,
    source_language: str,
    target_language: str,
    source_script_code: Optional[str] = None,
    target_script_code: Optional[str] = None,
    data_tracking: bool = True
) -> Dict[str, Any]:
    
    payload = {
        "controlConfig": {
            "dataTracking": data_tracking
        },
        "config": {
            "serviceId": service_id,
            "language": {
                "sourceLanguage": source_language,
                "sourceScriptCode": source_script_code or "",
                "targetLanguage": target_language,
                "targetScriptCode": target_script_code or ""
            }
        },
        "input": [
            {"source": source_text}
        ]
    }
    return payload


def translation_build_headers_and_params(
    service_id: str, auth_type: str = "auth",  # "auth" → Bearer token, "api" → API key
    auth_token: Optional[str] = None, api_key: Optional[str] = None,) -> Dict[str, Dict]:
    
    params = {"serviceId": service_id}
    
    headers = {
        "Content-Type": "application/json",
    }
    if auth_type.lower() == "auth":
        token = auth_token or os.getenv("REFRESHED_AUTH_TOKEN") or os.getenv("AUTH_TOKEN")
        if not token:
            raise ValueError("No auth token found. Set REFRESHED_AUTH_TOKEN or AUTH_TOKEN in .env.")
        headers["x-auth-source"] = "AUTH_TOKEN"
        headers["Authorization"] = f"Bearer {token}"

    elif auth_type.lower() == "api":
        key = api_key or os.getenv("API_KEY")
        if not key:
            raise ValueError("No API key found. Set API_KEY in .env.")
        headers["x-auth-source"] = "API_KEY"
        headers["x-api-key"] = key

    else:
        raise ValueError("Invalid auth_type. Must be either 'auth' or 'api'.")

    return {"headers": headers, "params": params}    