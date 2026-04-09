#!/usr/bin/env python
"""
Script para listar todos los usuarios
Uso:
    python scripts/list_users.py
"""
import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import DatabaseManager
from services.database_service import DatabaseService
from config import Config

def main():
    print("👥 LISTA DE USUARIOS REGISTRADOS")
    print("=" * 50)

    # Configurar base de datos
    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_service = DatabaseService(db_manager)

    # Obtener usuarios
    users = db_service.get_all_users()

    if not users:
        print("❌ No hay usuarios registrados")
        return 1

    print(f"📊 Total de usuarios: {len(users)}")
    print()

    for user in users:
        role_icon = "👑" if user.role == "admin" else "👤"
        print(f"{role_icon} {user.username} (ID: {user.id}, Rol: {user.role})")

    print()
    print("🔑 Credenciales de acceso:")
    print("   http://localhost:8080/transcription/validator")

    return 0

if __name__ == '__main__':
    sys.exit(main())