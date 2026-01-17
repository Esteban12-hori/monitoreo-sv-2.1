
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from src.server.app.database import engine

def migrate():
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('alert_rules')]
    
    with Session(engine) as sess:
        try:
            if 'condition_field' not in columns:
                print("Adding condition_field to alert_rules...")
                sess.execute(text("ALTER TABLE alert_rules ADD COLUMN condition_field VARCHAR(100)"))
            
            if 'condition_op' not in columns:
                print("Adding condition_op to alert_rules...")
                sess.execute(text("ALTER TABLE alert_rules ADD COLUMN condition_op VARCHAR(10)"))

            if 'condition_value' not in columns:
                print("Adding condition_value to alert_rules...")
                sess.execute(text("ALTER TABLE alert_rules ADD COLUMN condition_value FLOAT"))

            if 'duration_seconds' not in columns:
                print("Adding duration_seconds to alert_rules...")
                sess.execute(text("ALTER TABLE alert_rules ADD COLUMN duration_seconds INTEGER DEFAULT 0"))

            if 'severity' not in columns:
                print("Adding severity to alert_rules...")
                sess.execute(text("ALTER TABLE alert_rules ADD COLUMN severity VARCHAR(20) DEFAULT 'warning'"))

            sess.commit()
            print("Migration v8 (Advanced Alert Rules) completed successfully.")
        except Exception as e:
            sess.rollback()
            print(f"Error executing migration: {e}")

if __name__ == "__main__":
    migrate()
