
import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = BASE_DIR / "data" / "monitor.db"

def fix_schema():
    print(f"Checking database at: {DB_PATH}")
    if not DB_PATH.exists():
        print("Database not found, skipping manual fix (will be created by app).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Check/Add webhook_enabled to servers
    try:
        cursor.execute("SELECT webhook_enabled FROM servers LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding webhook_enabled column to servers table...")
        try:
            cursor.execute("ALTER TABLE servers ADD COLUMN webhook_enabled BOOLEAN DEFAULT 0")
            conn.commit()
            print("Column added.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("Column webhook_enabled already exists.")

    # 2. Check/Create data_monitoring table
    # This is usually handled by Base.metadata.create_all(engine) in main.py, 
    # but checking here doesn't hurt.
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_monitoring'")
    if not cursor.fetchone():
        print("Table data_monitoring does not exist (will be created by app startup).")
    else:
        print("Table data_monitoring exists.")

    conn.close()

if __name__ == "__main__":
    fix_schema()
