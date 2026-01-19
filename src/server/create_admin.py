from sqlalchemy.orm import Session
from src.server.app.database import engine
from src.server.app.models import User
from src.server.app.main import get_password_hash

def create_initial_admin():
    with Session(engine) as sess:
        # Check if any user exists
        user_count = sess.query(User).count()
        if user_count == 0:
            print("No users found. Creating default admin user...")
            admin = User(
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                name="Administrator",
                is_admin=True,
                receive_alerts=True
            )
            sess.add(admin)
            sess.commit()
            print("Default admin created: admin@example.com / admin123")
        else:
            print(f"Users already exist ({user_count}). Skipping default admin creation.")

if __name__ == "__main__":
    create_initial_admin()
