from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Detectar entorno: development, production, testing
ENV = os.getenv("ENV", "development")

BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# Mover data a root/data
DB_PATH = BASE_DIR / "data" / "monitor.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Default to SQLite
    DATABASE_URL = f"sqlite:///{DB_PATH}"

DEFAULT_ALERTS = {
    "cpu_total_percent": 90.0,
    "memory_used_percent": 90.0,
    "disk_used_percent": 90.0,
}

ALLOWED_ORIGINS = ["*"]

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")
CACHE_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "500"))

# Configuración de Email (SMTP)(Legacy Env Vars - now mostly in DB, but keeping for fallbacks/defaults if needed)
# ... (User wants configuration in DB mostly, but encryption key here)

# Encryption Key for Credentials
# Should be loaded from env, handled in security.py but good to have reference here if needed
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Importar configuraciones específicas del entorno
try:
    if ENV == "production":
        from .production import *
    elif ENV == "testing":
        from .testing import *
    else:
        from .development import *
except ImportError as e:
    print(f"Warning: Could not load environment config for {ENV}: {e}")
