import sys
import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(root_dir)

from sqlalchemy import create_engine, text
from config.settings import DATABASE_URL

def migrate():
    print(f"🔧 Starting Database Migration V5 (Auto-discovery Services)...")
    print(f"📂 Database URL: {DATABASE_URL}")
    
    engine = create_engine(DATABASE_URL, future=True)
    
    with engine.connect() as conn:
        # Add services column
        try:
            # TEXT is standard SQL
            conn.execute(text("ALTER TABLE metrics ADD COLUMN services TEXT"))
            print("   ✅ Added 'services' to 'metrics' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("   ℹ️  Column 'services' already exists.")
            else:
                print(f"   ⚠️  Could not add 'services': {e}")
        
        conn.commit()
    
    print("\n✅ Migration V5 completed.")

if __name__ == "__main__":
    migrate()
