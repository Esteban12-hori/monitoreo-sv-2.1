
import sys
import os
sys.path.append(os.getcwd())
from src.server.app.database import SessionLocal
from src.server.app.models import User

def list_users():
    db = SessionLocal()
    users = db.query(User).all()
    for u in users:
        print(f"ID: {u.id}, Email: '{u.email}', Name: '{u.name}', Admin: {u.is_admin}")
        print(f"Hash: {u.password_hash}")
    db.close()

if __name__ == "__main__":
    list_users()
