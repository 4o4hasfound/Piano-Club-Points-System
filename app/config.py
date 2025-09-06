from pathlib import Path
import os
import secrets
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)  # make sure folder exists

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Pick DB from env (Railway)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool,      # serverless-friendly: don't hold idle conns
        "pool_pre_ping": True,      # validate connections
    }

class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'app.sqlite'}"