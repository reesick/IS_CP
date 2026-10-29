import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='IMAGESHIELD_',extra='ignore')
    data: Path = ROOT / 'data'
    ml_python: Path = ROOT / '.venv-ml/Scripts/python.exe'
    job_timeout: int = Field(default=1800,ge=60,le=86400)
    persistent_ml: bool = True
    model_idle_seconds: int = Field(default=300,ge=10,le=86400)
    unet_checkpointing: bool = False

settings = Settings()
DATA = settings.data.resolve()
DATA.mkdir(parents=True, exist_ok=True)
ML_PYTHON = settings.ml_python.resolve()
MAX_BYTES = 10 * 1024 * 1024
JOB_TIMEOUT = settings.job_timeout

def private_path(relative):
    path = DATA / relative
    if path.is_symlink() or not path.resolve().is_relative_to(DATA):
        raise ValueError('Unsafe private path')
    return path
