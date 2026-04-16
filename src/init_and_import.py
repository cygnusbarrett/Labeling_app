#!/usr/bin/env python3
"""
Script para inicializar la BD e importar datos de forma segura
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from models.database import DatabaseManager, Base
from config import Config

print("📊 Inicializando base de datos...")

try:
    # 1. Crear DatabaseManager
    db_manager = DatabaseManager()
    
    # 2. Crear todas las tablas desde cero
    print("  ├─ Eliminando tablas existentes...")
    Base.metadata.drop_all(bind=db_manager.engine)
    
    print("  ├─ Creando tablas nuevas...")
    Base.metadata.create_all(bind=db_manager.engine)
    
    print("  ├─ Inicializando usuario admin...")
    db_manager.init_admin_user()
    
    # 3. Verificar que las tablas existen
    from sqlalchemy import inspect
    inspector = inspect(db_manager.engine)
    tables = inspector.get_table_names()
    print(f"  └─ Tablas creadas: {tables}")
    
    # Verificar columnas de la tabla words
    word_columns = {col['name']: col['type'] for col in inspector.get_columns('words')}
    print(f"\n📋 Columnas en tabla 'words':")
    for col_name in sorted(word_columns.keys()):
        print(f"   - {col_name}: {word_columns[col_name]}")
    
    if 'segment_id' in word_columns:
        print("\n✅ Columna 'segment_id' encontrada en tabla 'words'")
    else:
        print("\n❌ ERROR: Columna 'segment_id' NO encontrada en tabla 'words'")
        sys.exit(1)
    
    print("\n✅ Base de datos inicializada correctamente\n")
    
except Exception as e:
    print(f"\n❌ Error durante inicialización: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Ahora intentar la importación
print("=" * 60)
print("📥 Iniciando importación de segmentos...")
print("=" * 60 + "\n")

try:
    from scripts.import_segments import import_project_segments
    
    project_id = "memoria_1970_1990"
    project_dir = Path(__file__).parent / "data" / "transcription_projects" / project_id
    
    if not project_dir.exists():
        print(f"❌ Directorio del proyecto no encontrado: {project_dir}")
        sys.exit(1)
    
    print(f"Proyecto: {project_id}")
    print(f"Directorio: {project_dir}\n")
    
    import_project_segments(db_manager, project_id, str(project_dir))
    
    print("\n" + "=" * 60)
    print("✅ IMPORTACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error durante importación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
