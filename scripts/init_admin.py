
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.server.app.database import SessionLocal
from src.server.app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def init_admin():
    print("Connecting to DB...")
    db = SessionLocal()
    try:
        email = "admin@example.com"
        password = "Admin123!"
        
        # Check if exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists. Updating password...")
            user.password_hash = get_password_hash(password)
            user.is_admin = True
            user.must_change_password = False # Let's avoid forced change for now to test login
        else:
            print(f"Creating user {email}...")
            user = User(
                email=email,
                name="Admin User",
                password_hash=get_password_hash(password),
                is_admin=True,
                must_change_password=False
            )
            db.add(user)
        
        db.commit()
        print("Admin user configured successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    init_admin()
