import os
import base64
import hashlib
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

def get_encryption_key():
    """
    Retrieves the Fernet encryption key from the ENCRYPTION_KEY env variable.

    In production/testing the key MUST be provided; otherwise we raise an error
    instead of silently falling back to a publicly-known key (which would make
    every stored secret trivially decryptable). Only in development we allow a
    deterministic fallback derived from the host, with a loud warning.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if key:
        return key.encode() if isinstance(key, str) else key

    env = os.getenv("ENV", "development").lower()
    if env != "development":
        raise RuntimeError(
            "ENCRYPTION_KEY no está configurada. Genera una con "
            "`python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"` y expórtala en el entorno."
        )

    # Solo en desarrollo: clave derivada de forma determinista (NO segura para producción).
    logger.warning(
        "ENCRYPTION_KEY no encontrada. Usando clave de desarrollo derivada (INSEGURA). "
        "Configura ENCRYPTION_KEY antes de desplegar en producción."
    )
    seed = (os.getenv("USER", "") + "monitoreo-dev-fallback").encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(digest)

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
