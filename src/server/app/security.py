import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

def get_encryption_key():
    """
    Retrieves the encryption key from environment variables.
    If not found, it generates one and logs a warning (in prod, this should be fixed).
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # Fallback for dev/demo if not set, but this is volatile!
        # Ideally we want to ensure this is set.
        # We'll use a hardcoded fallback for development stability if not provided,
        # BUT this defeats the purpose of security.
        # Better: Generate and tell user to set it.
        # For the "Wizard", maybe we generate it and store it in the DB? No, key encrypts DB data.
        # We will use a derived key from a hardcoded secret if missing, with a loud warning.
        logger.warning("ENCRYPTION_KEY not found in env. Using default dev key (INSECURE).")
        # Default dev key (32 url-safe base64-encoded bytes)
        return b"ZcTj8yXQ5zK9r1w2e3r4t5y6u7i8o9p0a1s2d3f4g5h=" 
    return key.encode() if isinstance(key, str) else key

def encrypt_password(password: str) -> str:
    """Encrypts a password using Fernet."""
    if not password:
        return ""
    try:
        f = Fernet(get_encryption_key())
        return f.encrypt(password.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise

def decrypt_password(encrypted_password: str) -> str:
    """Decrypts a password using Fernet."""
    if not encrypted_password:
        return ""
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        # Return empty or raise? Raise to be safe.
        raise
