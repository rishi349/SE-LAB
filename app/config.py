"""Application settings loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

MIN_JWT_SECRET_LENGTH = 32


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_path: str
    jwt_secret: str
    bcrypt_rounds: int = 12
    rate_limit_enabled: bool = True
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.jwt_secret or len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET must be set and at least {MIN_JWT_SECRET_LENGTH} characters long."
            )
        if not 4 <= self.bcrypt_rounds <= 16:
            raise RuntimeError("BCRYPT_ROUNDS must be between 4 and 16.")
        if not self.database_path:
            raise RuntimeError("DATABASE_PATH must be set.")


def load_settings() -> Settings:
    """Read settings from the process environment. A local .env file is loaded if present."""
    load_dotenv()
    return Settings(
        database_path=os.getenv("DATABASE_PATH", "data/ledger.db"),
        jwt_secret=os.getenv("JWT_SECRET", ""),
        bcrypt_rounds=int(os.getenv("BCRYPT_ROUNDS", "12")),
        rate_limit_enabled=_env_bool("RATE_LIMIT_ENABLED", True),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
