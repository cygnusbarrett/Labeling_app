#!/usr/bin/env python3
"""
Script para migrar datos de SQLite a PostgreSQL
Uso: python migrate_to_postgresql.py
"""
import os
import logging
import sys
from pathlib import Path

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_to_postgresql():
    """Migra datos de SQLite a PostgreSQL"""
    
    # Cargar config
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import Config
    from models.database import DatabaseManager, Base, User, TranscriptionProject, Segment, Word
    
    config = Config.from_env()
    
    # Verificar que está en producción y que DATABASE_URL es PostgreSQL
    if 'sqlite' in config.DATABASE_URL.lower():
        logger.error("❌ DATABASE_URL debe apuntar a PostgreSQL, no SQLite")
        logger.error(f"   Valor actual: {config.DATABASE_URL}")
        sys.exit(1)
    
    logger.info("🚀 Iniciando migración de SQLite a PostgreSQL")
    logger.info(f"   Origen: sqlite:///labeling_app.db")
    logger.info(f"   Destino: {config.DATABASE_URL}")
    
    # Crear conexión a PostgreSQL
    try:
        db_postgres = DatabaseManager(config.DATABASE_URL)
        logger.info("✅ Conectado a PostgreSQL")
    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")
        sys.exit(1)
    
    # Crear tablas en PostgreSQL
    try:
        db_postgres.create_tables()
        logger.info("✅ Tablas creadas en PostgreSQL")
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        sys.exit(1)
    
    # Conectar a SQLite como origen
    try:
        db_sqlite = DatabaseManager("sqlite:///labeling_app.db")
        logger.info("✅ Conectado a SQLite (origen)")
    except Exception as e:
        logger.error(f"❌ Error conectando a SQLite: {e}")
        sys.exit(1)
    
    # Migrar datos
    try:
        sqlite_session = db_sqlite.get_session()
        postgres_session = db_postgres.get_session()
        
        # 1. Migrar usuarios
        logger.info("📦 Migrando usuarios...")
        users = sqlite_session.query(User).all()
        postgres_session.bulk_insert_mappings(User, [
            {
                'id': user.id,
                'username': user.username,
                'password_hash': user.password_hash,
                'role': user.role
            }
            for user in users
        ])
        postgres_session.commit()
        logger.info(f"✅ {len(users)} usuarios migrados")
        
        # 2. Migrar proyectos
        logger.info("📦 Migrando proyectos de transcripción...")
        projects = sqlite_session.query(TranscriptionProject).all()
        postgres_session.bulk_insert_mappings(TranscriptionProject, [
            {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'total_words': project.total_words,
                'words_to_review': project.words_to_review,
                'words_completed': project.words_completed,
                'created_at': project.created_at,
                'updated_at': project.updated_at,
                'completed_at': project.completed_at
            }
            for project in projects
        ])
        postgres_session.commit()
        logger.info(f"✅ {len(projects)} proyectos migrados")
        
        # 3. Migrar segmentos
        logger.info("📦 Migrando segmentos...")
        segments = sqlite_session.query(Segment).all()
        
        segment_mappings = []
        for i, segment in enumerate(segments):
            if (i + 1) % 100 == 0:
                logger.info(f"   ... {i + 1}/{len(segments)} segmentos")
            
            segment_mappings.append({
                'id': segment.id,
                'project_id': segment.project_id,
                'audio_filename': segment.audio_filename,
                'segment_index': segment.segment_index,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'text': segment.text,
                'speaker': segment.speaker,
                'text_revised': segment.text_revised,
                'review_status': segment.review_status,
                'annotator_id': segment.annotator_id,
                'low_prob_word_count': segment.low_prob_word_count,
                'created_at': segment.created_at,
                'updated_at': segment.updated_at,
                'completed_at': segment.completed_at
            })
        
        if segment_mappings:
            postgres_session.bulk_insert_mappings(Segment, segment_mappings)
            postgres_session.commit()
        logger.info(f"✅ {len(segments)} segmentos migrados")
        
        # 4. Migrar palabras
        logger.info("📦 Migrando palabras...")
        words = sqlite_session.query(Word).all()
        batch_size = 1000
        
        for batch_start in range(0, len(words), batch_size):
            batch_end = min(batch_start + batch_size, len(words))
            if (batch_start // batch_size + 1) % 5 == 0 or batch_end == len(words):
                logger.info(f"   ... {batch_end}/{len(words)} palabras")
            
            word_batch = words[batch_start:batch_end]
            word_mappings = [
                {
                    'id': word.id,
                    'segment_id': word.segment_id,
                    'project_id': word.project_id,
                    'audio_filename': word.audio_filename,
                    'word_index': word.word_index,
                    'word': word.word,
                    'speaker': word.speaker,
                    'probability': word.probability,
                    'start_time': word.start_time,
                    'end_time': word.end_time,
                    'alignment_score': word.alignment_score
                }
                for word in word_batch
            ]
            postgres_session.bulk_insert_mappings(Word, word_mappings)
        postgres_session.commit()
        logger.info(f"✅ {len(words)} palabras migradas")
        
        sqlite_session.close()
        postgres_session.close()
        
        logger.info("")
        logger.info("="*60)
        logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("="*60)
        logger.info(f"  Usuarios:    {len(users)}")
        logger.info(f"  Proyectos:   {len(projects)}")
        logger.info(f"  Segmentos:   {len(segments)}")
        logger.info(f"  Palabras:    {len(words)}")
        logger.info("")
        logger.info("📋 Próximos pasos:")
        logger.info("  1. Verificar que los datos estén en PostgreSQL:")
        logger.info("     psql -U labeling_user -d labeling_db -c 'SELECT COUNT(*) FROM users;'")
        logger.info("  2. Actualizar DATABASE_URL en tu .env a PostgreSQL")
        logger.info("  3. Hacer backups de ambas bases de datos")
        logger.info("  4. Reemplazar SQLite por PostgreSQL en producción")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error durante migración: {e}")
        postgres_session.rollback()
        sys.exit(1)

if __name__ == '__main__':
    migrate_to_postgresql()
