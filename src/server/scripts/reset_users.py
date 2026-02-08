import sys
import os
# Add src/server to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add root to path (for config)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.models import Base, User, SMTPConfig
from app.database import engine
from app.main import get_password_hash
from sqlalchemy.orm import Session
from sqlalchemy import text

def reset_system():
    
    # Drop specific tables to reset them
    print("Resetting User and SMTP tables...")
    try:
        User.__table__.drop(engine)
        print("Dropped users table.")
    except Exception as e:
        print(f"Users table might not exist or error: {e}")

    try:
        SMTPConfig.__table__.drop(engine)
        print("Dropped smtp_config table.")
    except Exception as e:
        print(f"SMTPConfig table might not exist or error: {e}")

    # Re-create all tables (this will create the new ones we just dropped)
    print("Re-creating tables...")
    Base.metadata.create_all(engine)

    with Session(engine) as sess:
        print("Creating admin user...")
        admin_user = User(
            email="admin@example.com",
            name="Administrator",
            password_hash=get_password_hash("admin"),
            is_admin=True,
            must_change_password=True,
            receive_alerts=True
        )
        sess.add(admin_user)

        print("Creating default Joaquin user...")
        joaquin_user = User(
            email="joaquinesteban.x@gmail.com",
            name="Joaquin Esteban",
            password_hash=get_password_hash("admin1234"),
            is_admin=True,
            must_change_password=True,
            receive_alerts=True
        )
        sess.add(joaquin_user)

        sess.commit()
        print("Admin user created with password 'admin'.")
        print("User joaquinesteban.x@gmail.com created with password 'admin1234'.")

if __name__ == "__main__":
    reset_system()
