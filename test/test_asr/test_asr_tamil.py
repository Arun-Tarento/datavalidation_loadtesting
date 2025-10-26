from myproject.utils.asr_helpers import encode_audio_to_base64, word_error_rate, normalize_text, asr_build_headers_and_params, asr_payload
import json
from pathlib import Path
import time
import pytest
import os
from dotenv import load_dotenv
from loguru import logger

_here = Path(__file__).resolve().parent
_env_candidates = [ _here / ".env",            
    _here.parent / ".env",     
    _here.parent.parent / ".env",  
    _here.parent.parent.parent / ".env" ]

for p in _env_candidates:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break

AUDIO_SAMPLE = Path(__file__).resolve().parent/"asr_samples"/"tamil_test_sample.wav"
SERVICE_ID = os.getenv("ASR_SERVICEID", "default_service")
TRANSCRIPTION_FORMAT = "transcript" 
#ENDPOINT_PATH = os.getenv("ASR_ENDPOINT_PATH", "/asr/v1/transcribe")
REFERENCE = "இந்த மழையில் நான் சென்னையில் இருந்தேன் மழையால் வீடுகளில் பாம்பும் அட்டையும் மீனும் சொந்தம் கொண்டாடியதைத் தொலைக்காட்சியில் பார்த்துக் கொண்டிருந்தேன்"
WER_THRESHOLD = float(os.getenv("ASR_WER_THRESHOLD", 0.5)) 


def test_asr(api_client, base_url, auth_token_refreshed, setup_logger):
    logger.info("Starting ASR test…")
    assert AUDIO_SAMPLE.exists(), f"Audio sample not found at {AUDIO_SAMPLE}"
    #token = auth_token_refreshed 
    token = "eyJhbGciOiJIUzI1NiIsInRvayI6ImFjY2VzcyIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMmQ0ZTE2Zi03NDBiLTRmZmMtOGIzZS1lY2M0ZGUxZjNiZTYiLCJuYW1lIjoidGVzdGNvbnN1bWVyIiwiZXhwIjoxNzYzNjYyODEzLjkyNTUyNzgsImlhdCI6MTc2MTA3MDgxMy45MjU1Mjg4LCJzZXNzX2lkIjoiZWZkNjUwYjEtNWFhMS00NjhlLTk3NTQtMGZhZDEzZDlkNGZlIn0.rJvCjW39NcB3eL7c4hTSPhI_NkJRQ9hFoHHnmHSeyJs"


    audio_b64 = encode_audio_to_base64(AUDIO_SAMPLE)
    payload = asr_payload(
        serviceId=SERVICE_ID,
        sourceLanguage="ta",              
        sourceScriptCode="Taml",          
        samplingRate=16000,
        encoding="base64",
        audioContent=audio_b64,
        transcription_format=TRANSCRIPTION_FORMAT,
        bestTokenCount=1,
    )
    auth_token = token # prefer token from env if present
    api_key = os.getenv("API_KEY")                  # fallback
    auth_type = "auth"
    auth = asr_build_headers_and_params(
        service_id=SERVICE_ID,
        auth_type=auth_type,
        auth_token=token,
        api_key=api_key )
    
    headers = auth["headers"]
    params = auth["params"]
    logger.info("headers : {}".format(headers))
    logger.info("params : {}".format(params))
    
    max_retries = 3
    backoff = 2
    last_err = None
    url = "/services/inference/asr" 
    
    resp = api_client.post(url, json=payload, headers=headers, params=params, timeout=120.0)
    logger.info("Status code {}".format(resp.status_code))
    logger.debug("ASR test response body : {}".format(resp.json()["output"][0]["source"]))

