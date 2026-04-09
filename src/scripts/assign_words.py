#!/usr/bin/env python
"""
Script para asignar palabras a usuarios
Uso:
    python scripts/assign_words.py <username> <num_words>
"""
import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import DatabaseManager, User, Word
from config import Config

def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/assign_words.py <username> <num_words>")
        print("Ejemplos:")
        print("  python scripts/assign_words.py annotator1 50")
        print("  python scripts/assign_words.py juan 25")
        return 1

    username = sys.argv[1]
    try:
        num_words = int(sys.argv[2])
    except ValueError:
        print("❌ Error: num_words debe ser un número")
        return 1

    print(f"👤 Asignando palabras a: {username}")
    print(f"📊 Cantidad: {num_words}")

    # Configurar base de datos
    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    session = db_manager.get_session()

    try:
        # Verificar que el usuario existe
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print(f"❌ Error: Usuario '{username}' no existe")
            return 1

        if user.role == 'admin':
            print("⚠️  Advertencia: Asignando palabras a un admin")

        # Encontrar palabras sin asignar
        unassigned_words = session.query(Word).filter_by(annotator_id=None).limit(num_words).all()

        if len(unassigned_words) < num_words:
            print(f"⚠️  Solo hay {len(unassigned_words)} palabras sin asignar")
            num_words = len(unassigned_words)

        # Asignar palabras
        assigned_count = 0
        for word in unassigned_words:
            word.annotator_id = user.id
            assigned_count += 1

        session.commit()

        print(f"✅ Asignadas {assigned_count} palabras a {username}")
        print(f"   Usuario ID: {user.id}")
        print(f"   Rol: {user.role}")

        # Mostrar estadísticas actualizadas
        total_assigned = session.query(Word).filter_by(annotator_id=user.id).count()
        print(f"   Total asignadas ahora: {total_assigned}")

    finally:
        session.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())