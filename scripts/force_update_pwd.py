
import sqlite3
import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
new_hash = pwd_context.hash("Admin123!")
print(f"Generated hash: {new_hash}")

db_paths = [
    r"c:\Users\joaqu\Desktop\save\data\monitor.db",
    r"c:\Users\joaqu\Desktop\save\src\server\data\monitor.db"
]

for db_path in db_paths:
    if os.path.exists(db_path):
        print(f"Updating DB at: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT email, hashed_password FROM users WHERE email='admin@example.com'")
            user = cursor.fetchone()
            
            if user:
                print(f"User found. Old hash: {user[1]}")
                cursor.execute("UPDATE users SET hashed_password=? WHERE email='admin@example.com'", (new_hash,))
                conn.commit()
                print("Password updated successfully.")
            else:
                print("User admin@example.com not found in this DB.")
                
            conn.close()
        except Exception as e:
            print(f"Error updating {db_path}: {e}")
    else:
        print(f"DB not found at: {db_path}")
