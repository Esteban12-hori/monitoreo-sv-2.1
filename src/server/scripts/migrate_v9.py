
import sys
import os

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.models import Base, UserGroup, NotificationRule, user_group_association

def migrate():
    print("Migrating database to V9 (User Groups and Notification Rules)...")
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
