import base64
import re
from pathlib import Path
from jiwer import wer as jiwer_wer
from myproject.db import SessionLocal, engine, Base
from typing import Optional, List, Dict, Any
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

def encode_audio_to_base64(path: str | Path) -> str:
    p = Path(path)
    data = p.read_bytes()
    return base64.b64encode(data).decode("ascii")


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s, flags=re.U)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def word_error_rate(reference: str, hypothesis: str) -> float:
    """
    Use jiwer to compute WER. Both texts should be normalized before calling.
    """
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    return jiwer_wer(ref, hyp)


def asr_payload(serviceId: str,
                sourceLanguage: str,
                sourceScriptCode: str, samplingRate: int = 16000,encoding: str = "base64",
                preProcessors: Optional[List[str]] = None, 
                postProcessors: Optional[List[str]] = None, 
                audioContent: str = "",
                audioUri:str =None, 
                modelId: Optional[str] = None,
                transcription_format: str = "transcript",
                bestTokenCount: int = 1 ):
    
    if preProcessors is None:
        preProcessors = []
    if postProcessors is None:
        postProcessors = []
    audio_dict: Dict[str, str] = {}
    if audioContent:
        audio_dict["audioContent"] = audioContent
    if audioUri:
        audio_dict["audioUri"] = audioUri

    if not audio_dict:
        raise ValueError("Either audioContent or audioUri must be provided")    
    

    config: Dict[str, Any] = {
        "audioFormat": "wav",
        "language": {
            "sourceLanguage": sourceLanguage,
            "sourceScriptCode": sourceScriptCode,
        },
        "encoding": encoding,
        "samplingRate": samplingRate,
        "serviceId": serviceId,
        "preProcessors": preProcessors,
        "postProcessors": postProcessors,
        "transcriptionFormat": {"value": transcription_format},
        "bestTokenCount": bestTokenCount,
    }
    if modelId:
        config["modelId"] = modelId

    payload = {
        "controlConfig": {"dataTracking": True},
        "config": config,
        "audio": [audio_dict],
    }

    return payload


def asr_build_headers_and_params( service_id: str,
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
