from myproject.utils.tts_helpers import make_tts_payload, tts_headers_and_params, save_base64_wav
from dotenv import load_dotenv
import os
import pytest
from loguru import logger
from pathlib import Path

from myproject.utils.asr_helpers import encode_audio_to_base64, word_error_rate, normalize_text, asr_build_headers_and_params, asr_payload
import json






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

output_dir = Path(__file__).resolve().parent / "generated_audio"
output_dir.mkdir(exist_ok=True)


service_id = os.getenv("TTS_SERVICEID")
token = os.getenv("REFRESHED_AUTH_TOKEN")
source_text = "हैलो, क्या हाल हैं ?"
source_language = "hi"
source_script_code = "Deva"
def test_tts_hindi(api_client, base_url, auth_token_refreshed, setup_logger, request):
    payload = make_tts_payload(
    service_id = service_id,
    source_text = source_text,
    source_language = source_language,
    source_script_code = source_script_code,
    gender = "male",
    sampling_rate = int(16000),
    audio_format = "wav",
    audio_duration = 2.0,
    data_tracking = True)

    handP = tts_headers_and_params( service_id = service_id,
                                auth_type = "auth")  # 'auth' for Bearer token, 'api' for API key ):
    headers = handP["headers"]
    params = handP["params"]
    url = "/services/inference/tts" 

    resp = api_client.post(url, json=payload, headers=headers, params=params, timeout=120.0)

    logger.info("Status code {}".format(resp.status_code))
    logger.debug("ASR test response body : {}".format([key for key, values in resp.json().items()]))
    data = resp.json() if hasattr(resp, "json") else {}
    b64 = None
    if isinstance(data, dict):
        b64 = data["audio"][0]["audioContent"]
    else:
        pytest.fail(f"No base64 audio found in response JSON: {data}")


    test_name = request.node.name              
    wav_file_store = output_dir/f"{test_name}_output.wav"
    # logger.info("Base64 audio {}".format(b64))
    save_base64_wav(b64, wav_file_store)
  
    
    


    #############################################################################################################################################

    # url = "/services/inference/asr" 
    # AUDIO_SAMPLE = Path(__file__).resolve().parent/"output.wav"
    # SERVICE_ID = os.getenv("ASR_SERVICEID", "default_service")
    # TRANSCRIPTION_FORMAT = "transcript" 
    # #ENDPOINT_PATH = os.getenv("ASR_ENDPOINT_PATH", "/asr/v1/transcribe")
    # #REFERENCE = "यह फ़िलिपीन्ज़ का दूसरा सबसे सक्रीय ज्वालामुखी है जिसके तैंतीस ज्ञात विस्फोट हो चुके हैं"
    # WER_THRESHOLD = float(os.getenv("ASR_WER_THRESHOLD", 0.5)) 


    
    # logger.info("Starting ASR test…")
    # assert AUDIO_SAMPLE.exists(), f"Audio sample not found at {AUDIO_SAMPLE}"
    # #token = auth_token_refreshed 


    # audio_b64 = encode_audio_to_base64(AUDIO_SAMPLE)
    # payload = asr_payload(
    #     serviceId=SERVICE_ID,
    #     sourceLanguage="hi",               # Hindi ISO code
    #     sourceScriptCode="Deva",          # Devanagari script code
    #     samplingRate=16000,
    #     encoding="base64",
    #     audioContent=audio_b64,
    #     transcription_format=TRANSCRIPTION_FORMAT,
    #     bestTokenCount=1,
    # )
    # auth_token = token # prefer token from env if present
    # api_key = os.getenv("API_KEY")                  # fallback
    # auth_type = "auth"
    # auth = asr_build_headers_and_params(
    #     service_id=SERVICE_ID,
    #     auth_type=auth_type,
    #     auth_token=token,
    #     api_key=api_key )
    
    # headers = auth["headers"]
    # params = auth["params"]
    # logger.info("headers : {}".format(headers))
    # logger.info("params : {}".format(params))
    
    # max_retries = 3
    # backoff = 2
    # last_err = None
    # url = "/services/inference/asr" 
    
    # resp = api_client.post(url, json=payload, headers=headers, params=params, timeout=120.0)

    # logger.info("Status code {}".format(resp.status_code))
    # logger.debug("ASR test response body : {}".format(resp.json()["output"][0]["source"]))