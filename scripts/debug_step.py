
print("Step 1: Start")
import os
print("Step 2: os imported")
import sqlite3
print("Step 3: sqlite3 imported")
try:
    from passlib.context import CryptContext
    print("Step 4: passlib imported")
except ImportError as e:
    print(f"Step 4 Failed: {e}")

print("Step 5: End imports")
