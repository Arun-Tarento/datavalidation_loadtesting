import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from pathlib import Path

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

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL not found. Please set it in .env.")

engine = create_engine(DATABASE_URL, future = True, echo=False, pool_pre_ping = True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True
)
Base = declarative_base()