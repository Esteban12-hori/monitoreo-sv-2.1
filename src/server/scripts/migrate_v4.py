import sys
import os

# Add root directory to sys.path (c:\Users\joaqu\Desktop\save)
# __file__ is src/server/scripts/migrate_v4.py
# dirname is src/server/scripts
# ../.. is src
# ../../.. is root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(root_dir)

from sqlalchemy import create_engine, text
from config.settings import DB_PATH

def migrate():
    print(f"🔧 Starting Database Migration V4...")
    print(f"📂 Database Path: {DB_PATH}")
    
    db_url = f"sqlite:///{DB_PATH}"
    engine = create_engine(db_url, future=True)
    
    with engine.connect() as conn:
        # Add net_bytes_sent
        try:
            conn.execute(text("ALTER TABLE metrics ADD COLUMN net_bytes_sent FLOAT DEFAULT 0"))
            print("   ✅ Added 'net_bytes_sent' to 'metrics' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("   ℹ️  Column 'net_bytes_sent' already exists.")
            else:
                print(f"   ⚠️  Could not add 'net_bytes_sent': {e}")
        
        # Add net_bytes_recv
        try:
            conn.execute(text("ALTER TABLE metrics ADD COLUMN net_bytes_recv FLOAT DEFAULT 0"))
            print("   ✅ Added 'net_bytes_recv' to 'metrics' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("   ℹ️  Column 'net_bytes_recv' already exists.")
            else:
                print(f"   ⚠️  Could not add 'net_bytes_recv': {e}")
                
        # Add uptime_seconds
        try:
            conn.execute(text("ALTER TABLE metrics ADD COLUMN uptime_seconds FLOAT DEFAULT 0"))
            print("   ✅ Added 'uptime_seconds' to 'metrics' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("   ℹ️  Column 'uptime_seconds' already exists.")
            else:
                print(f"   ⚠️  Could not add 'uptime_seconds': {e}")

        conn.commit()
    
    print("\n✅ Migration V4 completed.")

if __name__ == "__main__":
    migrate()
