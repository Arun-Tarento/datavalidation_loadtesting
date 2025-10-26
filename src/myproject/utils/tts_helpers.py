import base64
import re
from pathlib import Path
from jiwer import wer as jiwer_wer
from myproject.db import SessionLocal, engine, Base
from typing import Optional, Dict, Any, List, Tuple, Union
import os
from dotenv import load_dotenv
import io
import math
import time
import wave 
import contextlib
import tempfile



# _here = Path(__file__).resolve().parent
# _env_candidates = [ _here / ".env",            
#     _here.parent / ".env",     
#     _here.parent.parent / ".env",  
#     _here.parent.parent.parent / ".env"  ]
# for p in _env_candidates:
#     if p.exists():
#         load_dotenv(dotenv_path=p)
#         break
#     load_dotenv()



def make_tts_payload(
    service_id: str,
    source_text: str,
    source_language: Optional[str] = None,
    source_script_code: str = "",
    gender: str = "male",
    sampling_rate: int = 16000,
    audio_format: str = "wav",
    audio_duration: float = 5.0,
    data_tracking: bool = True,
) -> dict:
    """
    Build a TTS request payload matching the provided schema.
    audio_duration is the expected duration in seconds (informational; many TTS systems
    will approximate duration).
    """
    return {
        "controlConfig": {"dataTracking": data_tracking},
        "config": {
            "serviceId": service_id,
            "gender": gender,
            "samplingRate": sampling_rate,
            "audioFormat": audio_format,
            "language": {
                "sourceLanguage": source_language,
                "sourceScriptCode": source_script_code or "",
            },
        },
        "input": [
            {
                "source": source_text,
                "audioDuration": audio_duration,
            }
        ],
    }

def tts_headers_and_params( service_id: str,
                                auth_type: str = "auth",  # 'auth' for Bearer token, 'api' for API key
                                auth_token: Optional[str] = None,
                                api_key: Optional[str] = None,
                            ) -> Dict[str, Dict]:

    params = {"serviceId": service_id}
    headers = {
        "Content-Type": "application/json"
    }
    if auth_type.lower() == "auth":
        token = auth_token or os.getenv("REFRESHED_AUTH_TOKEN")
        if not token:
            raise ValueError("No auth token provided or found in .env (AUTH_TOKEN)")
        headers["x-auth-source"] = "AUTH_TOKEN"
        headers["Authorization"] = f"Bearer {token}"

       
    elif auth_type.lower() == "api":
    
        key = api_key or os.getenv("API_KEY")
        if not key:
            raise ValueError("No API key provided or found in .env (API_KEY)")
        headers["x-auth-source"] = "API_KEY"
        headers["x-api-key"] = key
    else:
        raise ValueError("Invalid auth_type. Must be either 'auth' or 'api'.")

    return {"headers": headers, "params": params}


def save_base64_wav(b64_audio: str, file_path: Path) -> Path:
    file_path = Path(file_path)
    raw = base64.b64decode(b64_audio)
    file_path.write_bytes(raw)
    return file_path

                            