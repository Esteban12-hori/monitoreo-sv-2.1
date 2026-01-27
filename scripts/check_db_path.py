
import sys
import os
from pathlib import Path
sys.path.append(os.getcwd())
from config.settings import DB_PATH

print(f"DB_PATH resolved: {DB_PATH}")
print(f"DB_PATH absolute: {DB_PATH.absolute()}")
print(f"Exists? {DB_PATH.exists()}")

if not DB_PATH.exists():
    print(f"Parent exists? {DB_PATH.parent.exists()}")
    # List parent content
    if DB_PATH.parent.exists():
        print(f"Parent content: {list(DB_PATH.parent.iterdir())}")
