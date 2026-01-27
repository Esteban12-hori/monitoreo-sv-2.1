
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.server.app.database import SessionLocal
from src.server.app.models import User
from config.settings import DB_PATH
from passlib.context import CryptContext

# Setup exact same context as main.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_login(email, password):
    print(f"DB Path: {DB_PATH}")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found in DB!")
            return
        
        print(f"User found: {user.email}")
        print(f"Stored hash: {user.password_hash}")
        
        is_valid = pwd_context.verify(password, user.password_hash)
        print(f"Password '{password}' valid? {is_valid}")
        
        if not is_valid:
            print("Trying to hash password manually to compare...")
            new_hash = pwd_context.hash(password)
            print(f"New hash for '{password}': {new_hash}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_login("admin@example.com", "Admin123!")
