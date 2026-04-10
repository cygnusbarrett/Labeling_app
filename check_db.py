#!/usr/bin/env python3
"""Script para inspeccionar y validar la base de datos"""
import sys
import os

# Agregar la ruta del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Cargar env vars
env_file = os.path.join(os.path.dirname(__file__), 'envs/web_app.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from models.database import DatabaseManager, User

print("=" * 80)
print("🔍 INSPECCIÓN DE BASE DE DATOS")
print("=" * 80)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///labeling_app.db')
print(f"📁 DATABASE_URL: {DATABASE_URL}")

db_manager = DatabaseManager(DATABASE_URL)
session = db_manager.get_session()

try:
    users = session.query(User).all()
    print(f"\n👥 Total de usuarios en BD: {len(users)}")
    
    for user in users:
        print(f"\n   📌 Usuario: {user.username}")
        print(f"      └─ ID: {user.id}")
        print(f"      └─ Role: {user.role}")
        print(f"      └─ Password hash: {user.password_hash[:50]}...")
        
        # Probar contraseña
        test_pwd = "admin123"
        is_valid = user.check_password(test_pwd)
        print(f"      └─ ✓ check_password('{test_pwd}'): {is_valid}")
    
    # Si no hay admin, créalo
    admin = session.query(User).filter_by(username='admin', role='admin').first()
    if not admin:
        print(f"\n❌ NO EXISTE USUARIO ADMIN - Creando ahora...")
        admin = User(username='admin', password='admin123', role='admin')
        session.add(admin)
        session.commit()
        print(f"✅ Admin creado: admin / admin123")
        
        # Verificar que se envío correctamente
        admin = session.query(User).filter_by(username='admin').first()
        print(f"✅ Verificación: admin existe? {admin is not None}")
        if admin:
            print(f"   └─ Hash: {admin.password_hash[:50]}...")
            print(f"   └─ check_password('admin123'): {admin.check_password('admin123')}")
    else:
        print(f"\n✅ Admin ya existe")
        
finally:
    session.close()

print("\n" + "=" * 80)
