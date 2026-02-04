
import sqlite3
from pathlib import Path
import sys

# Ajustar path para importar settings si fuera necesario
DB_PATH = Path(r"C:\Users\joaqu\Desktop\save\data\monitor.db")

def migrate_webhook_features():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Agregar campo webhook_enabled a servers
        cursor.execute("PRAGMA table_info(servers)")
        server_cols = [row[1] for row in cursor.fetchall()]
        if "webhook_enabled" not in server_cols:
            print("Adding webhook_enabled column to servers...")
            cursor.execute("ALTER TABLE servers ADD COLUMN webhook_enabled BOOLEAN DEFAULT 0")
        else:
            print("webhook_enabled already exists in servers.")

        # 2. Crear tabla data_monitoring
        print("Creating table data_monitoring if not exists...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_monitoring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id VARCHAR(255) NOT NULL,
            app VARCHAR(100) NOT NULL,
            cash_register_number INTEGER,
            user_name VARCHAR(255),
            flow VARCHAR(255),
            patent VARCHAR(50),
            vehicle_type VARCHAR(100),
            product VARCHAR(255),
            entity_id VARCHAR(255),
            working_day VARCHAR(255),
            client_created_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Crear índice para server_id
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_data_monitoring_server_id ON data_monitoring (server_id)")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_webhook_features()
