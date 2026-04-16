#!/usr/bin/env python3
"""
Script para importar transcripciones de archivos JSON a la base de datos
como Segmentos + Palabras, estructura preparada para validación colaborativa.

Uso:
    python import_segments.py <project_id>
    python import_segments.py memoria_1970_1990  # Importa el proyecto específico
    python import_segments.py  # Importa todos los proyectos disponibles
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import DatabaseManager, TranscriptionProject, Segment, Word
from config import Config

def import_project_segments(db_manager, project_id, project_dir):
    """
    Importa todos los segmentos de un proyecto desde JSONs
    
    Args:
        db_manager: DatabaseManager instance
        project_id: ID del proyecto (ej: 'memoria_1970_1990')
        project_dir: Ruta al directorio del proyecto
    """
    session = db_manager.get_session()
    
    try:
        # Verificar/crear el proyecto
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            metadata_path = Path(project_dir) / 'metadata.json'
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    project = TranscriptionProject(
                        id=project_id,
                        name=metadata.get('name', project_id),
                        description=metadata.get('description', ''),
                        status='active'
                    )
            else:
                project = TranscriptionProject(
                    id=project_id,
                    name=project_id.replace('_', ' ').title(),
                    status='active'
                )
            session.add(project)
            print(f"✅ Proyecto creado: {project.name}")
        
        # Procesar archivos JSON
        json_files = list(Path(project_dir).glob('*.json'))
        json_files = [f for f in json_files if f.name != 'metadata.json']
        
        print(f"📁 Encontrados {len(json_files)} archivo(s) JSON")
        
        total_segments = 0
        total_words = 0
        segments_with_issues = 0
        
        for json_file in json_files:
            print(f"\n📖 Procesando: {json_file.name}...")
            
            # Convertir el nombre del JSON al nombre del archivo de audio WAV
            audio_filename = json_file.name.replace('.json', '.wav')
            
            with open(json_file) as f:
                data = json.load(f)
            
            segments_data = data.get('segments', [])
            print(f"   └─ {len(segments_data)} segmentos")
            
            for segment_idx, segment_data in enumerate(segments_data):
                # Crear Segment
                segment = Segment(
                    project_id=project_id,
                    audio_filename=audio_filename,
                    segment_index=segment_idx,
                    start_time=segment_data['start'],
                    end_time=segment_data['end'],
                    text=segment_data['text'],
                    speaker=segment_data.get('speaker', 'UNKNOWN'),
                    review_status='pending'
                )
                
                session.add(segment)
                session.flush()  # Para obtener el ID del segment
                
                # Procesar palabras y detectar probabilidades bajas
                low_prob_count = 0
                words_data = segment_data.get('words', [])
                
                for word_idx, word_data in enumerate(words_data):
                    word = Word(
                        segment_id=segment.id,
                        project_id=project_id,
                        audio_filename=json_file.name,
                        word_index=word_idx,
                        word=word_data['word'],
                        speaker=word_data.get('speaker', 'UNKNOWN'),
                        probability=word_data['probability'],
                        start_time=word_data['start'],
                        end_time=word_data['end'],
                        alignment_score=word_data.get('alignment_score')
                    )
                    session.add(word)
                    
                    # Contar palabras con baja probabilidad
                    if word_data['probability'] < 0.95:
                        low_prob_count += 1
                
                # Si hay palabras con baja probabilidad, marcar segmento
                segment.low_prob_word_count = low_prob_count
                if low_prob_count > 0:
                    segment.review_status = 'pending'
                    segments_with_issues += 1
                else:
                    segment.review_status = 'approved'  # Sin problemas, ya validado
                
                total_segments += 1
                total_words += len(words_data)
            
            session.commit()
        
        # Actualizar estadísticas del proyecto
        project.total_words = total_words
        project.words_to_review = segments_with_issues  # Segmentos con palabras bajas
        project.words_completed = 0
        session.commit()
        
        print(f"\n✅ IMPORTACIÓN COMPLETADA")
        print(f"   └─ Total segmentos: {total_segments}")
        print(f"   └─ Total palabras: {total_words}")
        print(f"   └─ Segmentos para revisar: {segments_with_issues}")
        
        return total_segments, total_words, segments_with_issues
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

def main():
    """Función principal"""
    import os
    from pathlib import Path
    
    # Cargar configuración
    config = Config.from_env()
    
    # Ruta a proyectos
    base_data_dir = Path(__file__).parent.parent / 'data' / 'transcription_projects'
    
    # Determinar qué proyecto(s) importar
    if len(sys.argv) > 1:
        project_ids = [sys.argv[1]]
    else:
        # Importar todos los proyectos disponibles
        project_ids = [d.name for d in base_data_dir.iterdir() if d.is_dir()]
    
    # Conectar a BD
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_manager.create_tables()
    
    print("=" * 80)
    print("📥 IMPORTADOR DE SEGMENTOS DE TRANSCRIPCIÓN")
    print("=" * 80)
    
    grand_total_segments = 0
    grand_total_words = 0
    
    for project_id in project_ids:
        project_dir = base_data_dir / project_id
        
        if not project_dir.exists():
            print(f"❌ Proyecto no encontrado: {project_id}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"Importando proyecto: {project_id}")
        print(f"{'=' * 80}")
        
        total_segs, total_words, segs_issue = import_project_segments(
            db_manager,
            project_id,
            project_dir
        )
        
        grand_total_segments += total_segs
        grand_total_words += total_words
    
    print(f"\n{'=' * 80}")
    print(f"✅ RESUMEN FINAL")
    print(f"{'=' * 80}")
    print(f"Total segmentos importados: {grand_total_segments}")
    print(f"Total palabras importadas: {grand_total_words}")
    print(f"\nVerificación: python check_db.py")

if __name__ == '__main__':
    main()
