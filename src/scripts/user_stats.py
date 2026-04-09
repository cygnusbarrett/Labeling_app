#!/usr/bin/env python
"""
Script para mostrar estadísticas detalladas de usuarios y progreso
Uso:
    python scripts/user_stats.py
"""
import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import DatabaseManager, User, Word, TranscriptionProject
from config import Config

def main():
    print("📊 ESTADÍSTICAS DE USUARIOS Y PROGRESO")
    print("=" * 60)

    # Configurar base de datos
    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    session = db_manager.get_session()

    try:
        # Obtener usuarios
        users = session.query(User).all()
        projects = session.query(TranscriptionProject).all()

        if not users:
            print("❌ No hay usuarios registrados")
            return 1

        print(f"👥 Total de usuarios: {len(users)}")
        print(f"📁 Total de proyectos: {len(projects)}")
        print()

        # Estadísticas por usuario
        for user in users:
            role_icon = "👑" if user.role == "admin" else "👤"
            print(f"{role_icon} {user.username} (ID: {user.id})")

            # Contar palabras asignadas
            assigned_words = session.query(Word).filter_by(annotator_id=user.id).count()
            completed_words = session.query(Word).filter(
                Word.annotator_id == user.id,
                Word.status.in_(['approved', 'corrected'])
            ).count()

            pending_words = assigned_words - completed_words

            print(f"   📝 Palabras asignadas: {assigned_words}")
            print(f"   ✅ Completadas: {completed_words}")
            print(f"   ⏳ Pendientes: {pending_words}")

            if assigned_words > 0:
                progress = (completed_words / assigned_words) * 100
                print(f"   📊 Progreso: {progress:.1f}%")
            print()

        # Estadísticas generales
        print("🌍 ESTADÍSTICAS GENERALES")
        print("-" * 30)

        total_words = session.query(Word).count()
        completed_total = session.query(Word).filter(
            Word.status.in_(['approved', 'corrected'])
        ).count()

        print(f"📊 Total palabras en BD: {total_words}")
        print(f"✅ Palabras completadas: {completed_total}")
        print(f"⏳ Palabras pendientes: {total_words - completed_total}")

        if total_words > 0:
            overall_progress = (completed_total / total_words) * 100
            print(f"📊 Progreso general: {overall_progress:.1f}%")

        # Proyectos
        if projects:
            print()
            print("📁 PROYECTOS")
            print("-" * 15)
            for project in projects:
                print(f"📂 {project.name}")
                print(f"   ID: {project.id}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
    finally:
        session.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())