import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from sqlalchemy import create_engine, text
from config.settings import DB_PATH

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    engine = create_engine(f"sqlite:///{DB_PATH}")
    
    with engine.connect() as conn:
        # Add net_sent_rate column
        try:
            conn.execute(text("ALTER TABLE metrics ADD COLUMN net_sent_rate FLOAT DEFAULT 0.0"))
            print("Added net_sent_rate column.")
        except Exception as e:
            print(f"net_sent_rate column might already exist: {e}")

        # Add net_recv_rate column
        try:
            conn.execute(text("ALTER TABLE metrics ADD COLUMN net_recv_rate FLOAT DEFAULT 0.0"))
            print("Added net_recv_rate column.")
        except Exception as e:
            print(f"net_recv_rate column might already exist: {e}")

if __name__ == "__main__":
    migrate()
