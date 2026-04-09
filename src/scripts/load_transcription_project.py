#!/usr/bin/env python3
"""
Script para cargar el primer audio de prueba en la base de datos
Uso:
    python scripts/load_transcription_project.py
"""
import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.database import DatabaseManager
from services.transcription_service import TranscriptionService
from config import Config

def main():
    """Carga el proyecto memoria_1970_1990 con el audio de ejemplo"""
    
    print("=" * 70)
    print("SCRIPT DE CARGA: Transcripción de Audio Osvaldo Muray")
    print("=" * 70)
    
    # Configurar base de datos
    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_manager.create_tables()
    
    # Instanciar servicio de transcripción
    transcription_service = TranscriptionService(config=config)
    
    session = db_manager.get_session()
    
    try:
        # Datos del proyecto
        project_id = "memoria_1970_1990"
        project_name = "Archivo de Audio - Memoria 1970-1990"
        project_description = "Gran repositorio de audios de época 1970-1990"
        
        # Buscar automáticamente archivos .wav y .json que coincidan por nombre base
        project_dir = os.path.join(config.get_transcription_projects_path(), project_id)
        wav_files = [f for f in os.listdir(project_dir) if f.endswith('.wav')]
        json_files = [f for f in os.listdir(project_dir) if f.endswith('.json')]
        
        if not wav_files:
            raise FileNotFoundError(f"No se encontraron archivos .wav en {project_dir}")
        
        # Encontrar parejas (wav y json con mismo nombre base)
        pairs = []
        for wav_file in wav_files:
            # Nombre base sin extensión
            base_name = os.path.splitext(wav_file)[0]
            json_file = f"{base_name}.json"
            
            if json_file in json_files:
                pairs.append((wav_file, json_file))
        
        if not pairs:
            print(f"\n❌ Error: No se encontraron parejas de archivos .wav y .json")
            print(f"   WAV files: {wav_files}")
            print(f"   JSON files: {json_files}")
            return 1
        
        print(f"\n📁 Proyecto: {project_id}")
        print(f"📝 Nombre: {project_name}")
        print(f"📊 Encontradas {len(pairs)} pareja(s) de audio-transcripción")
        
        # Crear proyecto
        print(f"\n⏳ Creando proyecto...")
        project = transcription_service.create_or_update_project(
            session, project_id, project_name, project_description
        )
        print(f"✅ Proyecto creado: {project.id}")
        
        # Importar todas las transcripciones encontradas
        total_words_added = 0
        for audio_filename, transcript_filename in pairs:
            print(f"\n📄 Procesando: {audio_filename}")
            print(f"   Transcripción: {transcript_filename}")
            
            try:
                project, words_added = transcription_service.import_transcript_to_db(
                    session, 
                    project_id, 
                    audio_filename, 
                    transcript_filename,
                    probability_threshold=0.95,
                    random_annotators=None  # Se asignarán manualmente después
                )
                print(f"   ✅ {words_added} palabras importadas")
                total_words_added += words_added
            except Exception as e:
                print(f"   ⚠️  Error procesando {audio_filename}: {str(e)}")
                continue
        
        print(f"\n✅ Total: {total_words_added} palabras importadas")
        
        # Mostrar estadísticas
        print(f"\n📊 Estadísticas del Proyecto:")
        print(f"   - Total de palabras: {project.total_words}")
        print(f"   - Palabras a revisar (prob < 0.95): {project.words_to_review}")
        print(f"   - Palabras completadas: {project.words_completed}")
        print(f"   - Estado: {project.status}")
        
        # Obtener primeras palabras para mostrar
        print(f"\n📋 Primeras 5 palabras para revisar:")
        from models.database import Word
        first_words = session.query(Word).filter_by(
            project_id=project_id,
            status='pending'
        ).limit(5).all()
        
        for i, word in enumerate(first_words, 1):
            print(f"   {i}. [{word.speaker}] '{word.word}' (prob: {word.probability:.3f})")
            print(f"      Tiempo: {word.start_time:.2f}s - {word.end_time:.2f}s")
        
        print(f"\n✨ Transcripción cargada exitosamente")
        print(f"\n🔗 Próximos pasos:")
        print(f"   1. Asignar palabras a anotadores (usando API POST /api/v2/transcriptions/projects/...)")
        print(f"   2. Acceder a /transcription/validator para anotar")
        print(f"   3. Ver estadísticas en /stats")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n💡 Asegúrate de que existen archivos en:")
        print(f"   data/transcription_projects/memoria_1970_1990/")
        print(f"   - Archivos .wav (ej: audio_name.wav)")
        print(f"   - Archivos .json con igual nombre base (ej: audio_name.json)")
        return 1
    
    except Exception as e:
        print(f"\n❌ Error inesperado:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        session.close()
    
    return 0

if __name__ == '__main__':
    exit(main())
