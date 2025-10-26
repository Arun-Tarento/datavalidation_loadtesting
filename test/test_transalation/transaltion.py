from myproject.utils.translation_helpers import translation_payload, translation_build_headers_and_params
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

