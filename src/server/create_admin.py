import os
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
            email = os.getenv("ADMIN_EMAIL", "admin@example.com")
            password = os.getenv("ADMIN_PASSWORD", "admin123")
            if not os.getenv("ADMIN_PASSWORD"):
                print("ADVERTENCIA: ADMIN_PASSWORD no configurada; usando contraseña por "
                      "defecto. Deberá cambiarse en el primer inicio de sesión.")
            admin = User(
                email=email,
                password_hash=get_password_hash(password),
                name="Administrator",
                is_admin=True,
                receive_alerts=True,
                must_change_password=True
            )
            sess.add(admin)
            sess.commit()
            print(f"Default admin created: {email} (cambio de contraseña requerido)")
        else:
            print(f"Users already exist ({user_count}). Skipping default admin creation.")

if __name__ == "__main__":
    create_initial_admin()
