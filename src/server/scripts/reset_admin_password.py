
from sqlalchemy.orm import Session
from src.server.app.database import engine
from src.server.app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def reset_admin():
    with Session(engine) as sess:
        email = "admin@example.com"
        password = "admin123"
        
        user = sess.query(User).filter_by(email=email).first()
        if user:
            print(f"User {email} found. Updating password...")
            user.password_hash = get_password_hash(password)
            user.is_admin = True
        else:
            print(f"User {email} not found. Creating...")
            user = User(
                email=email,
                password_hash=get_password_hash(password),
                name="Administrator",
                is_admin=True,
                receive_alerts=True
            )
            sess.add(user)
        
        sess.commit()
        print("Admin user ready: admin@example.com / admin123")

if __name__ == "__main__":
    reset_admin()
