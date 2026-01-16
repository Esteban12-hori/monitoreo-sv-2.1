from pathlib import Path

# Configuración de testing
DEBUG = True
LOG_LEVEL = "DEBUG"

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "test.db"
