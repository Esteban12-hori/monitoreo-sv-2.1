import sys
import os

# Add 'server' directory to sys.path so we can import 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(current_dir) # .../server
sys.path.append(server_dir)

from sqlalchemy import create_engine, text
from app.config import DB_PATH
from app.models import Base

def migrate():
    print(f"🔧 Starting Database Migration...")
    print(f"📂 Database Path: {DB_PATH}")
    
    db_url = f"sqlite:///{DB_PATH}"
    engine = create_engine(db_url, future=True)
    
    # 1. Create any missing tables (safe to run, skips existing)
    print("1️⃣  Checking/Creating missing tables...")
    try:
        Base.metadata.create_all(engine)
        print("   ✅ Tables verified.")
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")

    # 2. Apply specific column migrations
    print("2️⃣  Checking/Applying column migrations...")
    with engine.connect() as conn:
        # Migration: Add report_interval to servers
        try:
            conn.execute(text("ALTER TABLE servers ADD COLUMN report_interval INTEGER DEFAULT 2400"))
            conn.commit()
            print("   ✅ Added 'report_interval' to 'servers' table.")
        except Exception as e:
            err = str(e).lower()
            if "duplicate column name" in err:
                print("   ℹ️  Column 'report_interval' already exists in 'servers'.")
            else:
                print(f"   ⚠️  Could not add 'report_interval': {e}")

    print("\n✅ Migration completed.")

if __name__ == "__main__":
    migrate()
