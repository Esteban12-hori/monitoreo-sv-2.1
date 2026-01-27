
import sys
import os
# Add project root to path
sys.path.append(os.getcwd())

from src.server.app.database import SessionLocal
from src.server.app.models import User
from passlib.context import CryptContext

# Setup exact same context as main.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_login(email, password):
    print(f"Connecting to DB...")
    db = SessionLocal()
    try:
        print(f"Querying user {email}...")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found in DB!")
            # List all users
            users = db.query(User).all()
            print(f"All users found: {[u.email for u in users]}")
            return
        
        print(f"User found: {user.email}")
        print(f"Stored hash: {user.hashed_password}")
        
        is_valid = pwd_context.verify(password, user.hashed_password)
        print(f"Password '{password}' valid? {is_valid}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_login("admin@example.com", "Admin123!")
