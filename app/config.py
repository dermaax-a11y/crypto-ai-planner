from __future__ import annotations

import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = os.getenv('APP_NAME', 'Crypto AI Planner')
    app_version: str = os.getenv('APP_VERSION', '1.1.0')
    host: str = os.getenv('HOST', '0.0.0.0')
    port: int = int(os.getenv('PORT', '8000'))
    app_env: str = os.getenv('APP_ENV', 'development')
    reload: bool = os.getenv('RELOAD', 'false').lower() == 'true'


@lru_cache
def get_settings() -> Settings:
    return Settings()
