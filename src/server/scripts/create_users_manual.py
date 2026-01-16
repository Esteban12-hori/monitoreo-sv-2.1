import sys
import os
import getpass
import argparse

# Agregar el directorio padre (server) al path para poder importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import Session, engine, User, get_password_hash
from sqlalchemy import select

def create_user(email, password, name, is_admin=False):
    try:
        with Session(engine) as session:
            user = session.execute(select(User).where(User.email == email)).scalars().first()
            if user:
                print(f"Usuario {email} ya existe. Actualizando contraseña...")
                user.password_hash = get_password_hash(password)
                user.is_admin = is_admin
                user.must_change_password = True # Force password change on manual reset
            else:
                print(f"Creando usuario {email}...")
                user = User(
                    email=email,
                    name=name,
                    password_hash=get_password_hash(password),
                    is_admin=is_admin,
                    must_change_password=True # Force password change on creation
                )
                session.add(user)
            session.commit()
            print(f"Usuario {email} configurado correctamente.")
    except Exception as e:
        print(f"Error configurando {email}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crear usuario manualmente")
    parser.add_argument("--email", help="Email del usuario", required=True)
    parser.add_argument("--name", help="Nombre del usuario", required=True)
    parser.add_argument("--admin", action="store_true", help="Es administrador")
    args = parser.parse_args()

    print(f"Configurando usuario: {args.email}")
    password = getpass.getpass("Ingrese contraseña: ")
    confirm_password = getpass.getpass("Confirme contraseña: ")

    if password != confirm_password:
        print("Las contraseñas no coinciden.")
        sys.exit(1)
    
    if len(password) < 6:
         print("La contraseña debe tener al menos 6 caracteres.")
         sys.exit(1)

    create_user(args.email, password, args.name, args.admin)
    print("Finalizado.")
