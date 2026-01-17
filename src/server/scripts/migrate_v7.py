import sys
from pathlib import Path
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sqlalchemy import create_engine, text
from config.settings import DB_PATH

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    engine = create_engine(f"sqlite:///{DB_PATH}")
    
    with engine.connect() as conn:
        # Add processes column
        try:
            conn.execute(text("ALTER TABLE metrics ADD COLUMN processes TEXT"))
            print("Added processes column.")
        except Exception as e:
            print(f"processes column might already exist: {e}")

if __name__ == "__main__":
    migrate()
