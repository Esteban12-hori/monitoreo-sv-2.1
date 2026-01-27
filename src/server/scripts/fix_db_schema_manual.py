
import sqlite3
from pathlib import Path
import sys

# Ajustar path para importar settings si fuera necesario, pero lo haré hardcoded para ser directo y evitar errores de import
DB_PATH = Path(r"C:\Users\joaqu\Desktop\save\data\monitor.db")

def fix_database():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check users table columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns in users: {columns}")

        if "phone_number" not in columns:
            print("Adding phone_number column...")
            cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR(50)")
        else:
            print("phone_number column already exists.")

        if "webhook_url" not in columns:
            print("Adding webhook_url column...")
            cursor.execute("ALTER TABLE users ADD COLUMN webhook_url VARCHAR(500)")
        else:
            print("webhook_url column already exists.")
            
        conn.commit()
        print("Database schema fixed successfully.")

    except Exception as e:
        print(f"Error modifying database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()
