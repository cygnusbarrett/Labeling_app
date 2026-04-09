"""
Servicio de transcripción - parseo de JSON y validación de palabras
"""
import json
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from models.database import TranscriptionProject, Word, User


class TranscriptionService:
    """Servicio para gestión de transcripciones de audio"""
    
    def __init__(self, config=None, base_path: str = None):
        """
        Inicializa el servicio de transcripción
        
        Args:
            config: Objeto Config con rutas configurables
            base_path: Ruta base a transcription_projects/ (deprecated, usar config)
        """
        if config is not None:
            # Usar configuración centralizada (SERVIDOR REMOTO)
            self.base_path = config.get_transcription_projects_path()
        elif base_path is not None:
            # Ruta explícita (compatibilidad)
            self.base_path = base_path
        else:
            # Fallback a ruta hardcodeada (desarrollo local)
            self.base_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'transcription_projects')
    
    def get_project_path(self, project_id: str) -> str:
        """Obtiene la ruta del proyecto"""
        return os.path.join(self.base_path, project_id)
    
    def get_metadata_path(self, project_id: str) -> str:
        """Obtiene la ruta del archivo metadata.json"""
        return os.path.join(self.get_project_path(project_id), 'metadata.json')
    
    def load_metadata(self, project_id: str) -> Dict:
        """
        Carga el archivo metadata.json del proyecto
        
        Returns:
            Diccionario con metadatos del proyecto
        
        Raises:
            FileNotFoundError: Si no existe metadata.json
            json.JSONDecodeError: Si el JSON es inválido
        """
        metadata_path = self.get_metadata_path(project_id)
        
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"metadata.json no encontrado: {metadata_path}")
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON inválido en {metadata_path}: {str(e)}", e.doc, e.pos)
    
    def load_transcript(self, project_id: str, transcript_filename: str) -> Dict:
        """
        Carga un archivo transcript.json
        
        Args:
            project_id: ID del proyecto
            transcript_filename: Nombre del archivo JSON (con extensión)
        
        Returns:
            Diccionario con la transcripción
        
        Raises:
            FileNotFoundError: Si no existe el archivo
            json.JSONDecodeError: Si el JSON es inválido
        """
        transcript_path = os.path.join(self.get_project_path(project_id), transcript_filename)
        
        if not os.path.exists(transcript_path):
            raise FileNotFoundError(f"Transcript no encontrado: {transcript_path}")
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON inválido en {transcript_path}: {str(e)}", e.doc, e.pos)
    
    def parse_words_from_transcript(
        self, 
        transcript_data: Dict,
        probability_threshold: float = 0.95
    ) -> List[Dict]:
        """
        Parsea un JSON de transcripción y extrae palabras por validar
        
        Args:
            transcript_data: Datos cargados del JSON
            probability_threshold: Umbral de probabilidad (default 0.95)
        
        Returns:
            Lista de palabras con probability < threshold
        
        Raises:
            ValueError: Si el formato del JSON es inválido
        """
        words_to_review = []
        
        # Soportar múltiples formatos de JSON
        all_words = []
        
        if 'words' in transcript_data:
            # Formato 1: {"words": [...]}
            all_words = transcript_data['words']
        elif 'segments' in transcript_data:
            # Formato 2: {"segments": [{"words": [...]}, ...]}
            # Extraer todas las palabras de todos los segmentos
            for segment in transcript_data['segments']:
                if 'words' in segment:
                    all_words.extend(segment['words'])
        elif isinstance(transcript_data, list):
            # Formato 3: [{...}, {...}] (array directo)
            all_words = transcript_data
        else:
            raise ValueError("Formato de transcripción no reconocido. Se espera 'words', 'segments', o array directo.")
        
        # Filtrar palabras por probability < threshold
        for idx, word_obj in enumerate(all_words):
            if not isinstance(word_obj, dict):
                continue
            
            probability = float(word_obj.get('probability', 1.0))
            
            if probability < probability_threshold:
                words_to_review.append({
                    'word_index': idx,
                    'word': word_obj.get('word', ''),
                    'speaker': word_obj.get('speaker', 'UNKNOWN'),
                    'probability': probability,
                    'start_time': float(word_obj.get('start', 0)),
                    'end_time': float(word_obj.get('end', 0)),
                    'alignment_score': word_obj.get('alignment_score', None)
                })
        
        return words_to_review
    
    def create_or_update_project(
        self,
        session,
        project_id: str,
        name: str,
        description: str = None
    ) -> TranscriptionProject:
        """
        Crea o actualiza un proyecto de transcripción en BD
        
        Args:
            session: Sesión de SQLAlchemy
            project_id: ID único del proyecto
            name: Nombre del proyecto
            description: Descripción opcional
        
        Returns:
            Objeto TranscriptionProject
        """
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        
        if project:
            print(f"Proyecto actualizado: {project_id}")
            project.name = name
            project.description = description
        else:
            project = TranscriptionProject(
                id=project_id,
                name=name,
                description=description,
                status='active'
            )
            session.add(project)
            print(f"Proyecto creado: {project_id}")
        
        session.commit()
        return project
    
    def import_transcript_to_db(
        self,
        session,
        project_id: str,
        audio_filename: str,
        transcript_filename: str,
        probability_threshold: float = 0.95,
        random_annotators: List[int] = None
    ) -> Tuple[TranscriptionProject, int]:
        """
        Importa una transcripción a la BD, creando registros de palabras
        
        Args:
            session: Sesión de SQLAlchemy
            project_id: ID del proyecto
            audio_filename: Nombre del archivo .wav
            transcript_filename: Nombre del archivo .json
            probability_threshold: Umbral de probabilidad para palabras a revisar
            random_annotators: Lista de IDs de anotadores para asignación. Si es None, no asigna.
        
        Returns:
            (TranscriptionProject, cantidad_de_palabras_agregadas)
        
        Raises:
            FileNotFoundError: Si los archivos no existen
            ValueError: Si hay error en formato
        """
        # Cargar transcripción
        transcript_data = self.load_transcript(project_id, transcript_filename)
        words_list = self.parse_words_from_transcript(transcript_data, probability_threshold)
        
        # Obtener o crear proyecto
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"Proyecto no encontrado: {project_id}")
        
        # Actualizar contadores
        project.words_to_review = len(words_list)
        
        # Importar palabras
        words_added = 0
        for word_data in words_list:
            # Verificar si ya existe (para evitar duplicados)
            existing = session.query(Word).filter_by(
                project_id=project_id,
                audio_filename=audio_filename,
                word_index=word_data['word_index']
            ).first()
            
            if existing:
                print(f"Palabra ya existe: {project_id}:{word_data['word_index']}")
                continue
            
            word = Word(
                project_id=project_id,
                audio_filename=audio_filename,
                word_index=word_data['word_index'],
                word=word_data['word'],
                speaker=word_data['speaker'],
                probability=word_data['probability'],
                start_time=word_data['start_time'],
                end_time=word_data['end_time'],
                alignment_score=word_data['alignment_score'],
                status='pending'
            )
            
            # Asignar anotador si se proporciona lista
            if random_annotators:
                import random
                word.annotator_id = random.choice(random_annotators)
            
            session.add(word)
            words_added += 1
        
        session.commit()
        print(f"Palabras agregadas al proyecto {project_id}: {words_added}")
        
        return project, words_added
    
    def get_project_stats(self, session, project_id: str, annotator_id: int = None) -> Dict:
        """
        Obtiene estadísticas de un proyecto
        
        Args:
            session: Sesión de SQLAlchemy
            project_id: ID del proyecto
            annotator_id: Si se especifica, retorna solo stats de este anotador
        
        Returns:
            Diccionario con estadísticas
        """
        query = session.query(Word).filter_by(project_id=project_id)
        
        if annotator_id:
            query = query.filter_by(annotator_id=annotator_id)
        
        total = query.count()
        pending = query.filter_by(status='pending').count()
        approved = query.filter_by(status='approved').count()
        corrected = query.filter_by(status='corrected').count()
        completed = approved + corrected
        
        progress = round((completed / total * 100), 2) if total > 0 else 0
        
        return {
            'total_words': total,
            'pending': pending,
            'approved': approved,
            'corrected': corrected,
            'completed': completed,
            'progress': progress,
            'annotator_id': annotator_id
        }
    
    def get_annotator_stats_for_project(self, session, project_id: str) -> List[Dict]:
        """
        Obtiene estadísticas por anotador en un proyecto
        
        Returns:
            Lista de dicts con stats por anotador
        """
        # Query para obtener anotadores únicos del proyecto
        annotators = session.query(Word.annotator_id).filter_by(
            project_id=project_id
        ).distinct().all()
        
        stats_list = []
        for (annotator_id,) in annotators:
            if not annotator_id:
                continue
            
            annotator = session.query(User).filter_by(id=annotator_id).first()
            if not annotator:
                continue
            
            word_stats = self.get_project_stats(session, project_id, annotator_id)
            word_stats['annotator_username'] = annotator.username
            word_stats['annotator_id'] = annotator_id
            stats_list.append(word_stats)
        
        return stats_list


# Instancia global del servicio
transcription_service = TranscriptionService()
