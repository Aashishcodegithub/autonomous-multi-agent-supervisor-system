# api/security.py
import os
import logging
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")  # <-- Reads your API key from .env

logger = logging.getLogger("erp-api.security")
if not API_KEY:
    # Previously we raised an exception here to require an API key at import-time.
    # To allow running the app without an API key (e.g., for local development),
    # we no longer raise. The validator below becomes a no-op when `API_KEY` is unset.
    logger.warning("API_KEY not found in .env — running with authentication disabled (dev mode).")
    # raise Exception("API_KEY not found in .env file!")


async def validate_api_key(x_api_key: str = Header(None)):
    """
    Validates the X-API-Key header if `API_KEY` is configured.
    When `API_KEY` is unset, validation is a no-op to allow running without auth (development).
    """
    if not API_KEY:
        return None
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return x_api_key
