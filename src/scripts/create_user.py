#!/usr/bin/env python
"""
Script para crear usuarios adicionales
Uso:
    python scripts/create_user.py <username> <password> [role]
"""
import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import DatabaseManager, User
from config import Config

def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/create_user.py <username> <password> [role]")
        print("Ejemplos:")
        print("  python scripts/create_user.py juan 1234 annotator")
        print("  python scripts/create_user.py maria admin123 admin")
        return 1

    username = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else 'annotator'

    if role not in ['admin', 'annotator']:
        print("❌ Error: role debe ser 'admin' o 'annotator'")
        return 1

    print(f"👤 Creando usuario: {username}")
    print(f"🔐 Contraseña: {password}")
    print(f"👑 Rol: {role}")

    # Configurar base de datos
    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    session = db_manager.get_session()

    try:
        # Verificar si el usuario ya existe
        existing_user = session.query(User).filter_by(username=username).first()
        if existing_user:
            print("❌ Error: El usuario ya existe")
            return 1

        # Crear usuario
        user = User(username=username, password=password, role=role)
        session.add(user)
        session.commit()

        print("✅ Usuario creado exitosamente!")
        print(f"   ID: {user.id}")
        print(f"   Usuario: {user.username}")
        print(f"   Rol: {user.role}")
        return 0
    finally:
        session.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())