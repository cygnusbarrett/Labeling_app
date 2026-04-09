"""
Rutas API para validación de transcripciones de audio
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from functools import wraps
from datetime import datetime, timezone
from models.database import TranscriptionProject, Word, User, DatabaseManager
from services.audio_service import AudioService
from services.transcription_service import TranscriptionService
from services.jwt_service import jwt_service
from config import Config
import io
import os

# Blueprint
transcription_bp = Blueprint('transcription_api', __name__, url_prefix='/api/v2/transcriptions')

# Inicializar servicios
_db_manager = None
_audio_service = None
_transcription_service = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        config = Config.from_env()
        _db_manager = DatabaseManager(config.DATABASE_URL)
    return _db_manager

def get_audio_service():
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioService()
    return _audio_service

def get_transcription_service():
    global _transcription_service
    if _transcription_service is None:
        config = Config.from_env()
        _transcription_service = TranscriptionService(config=config)
    return _transcription_service

# ==================== DECORADORES ====================

def jwt_required(f):
    """Requiere JWT token válido"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token no proporcionado'}), 401
        
        try:
            payload = jwt_service.verify_access_token(token)
            request.user_id = payload.get('user_id')
            request.username = payload.get('username')
            request.user_role = payload.get('role')
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Token inválido o expirado'}), 401
    return decorated

def admin_required(f):
    """Requiere rol admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        db_manager = get_db_manager()
        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=request.user_id).first()
            if not user or user.role != 'admin':
                return jsonify({'error': 'Acceso denegado. Se requiere rol admin.'}), 403
            return f(*args, **kwargs)
        finally:
            session.close()
    return decorated

# ==================== ENDPOINTS PARA PROYECTOS ====================

@transcription_bp.route('/projects', methods=['GET'])
@jwt_required
def list_projects():
    """
    Lista proyectos de transcripción
    Query params: status ('active', 'completed', 'archived')
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        status = request.args.get('status')
        
        query = session.query(TranscriptionProject)
        if status:
            query = query.filter_by(status=status)
        
        projects = query.all()
        session.close()
        
        return jsonify({
            'projects': [
                {
                    'id': p.id,
                    'name': p.name,
                    'status': p.status,
                    'total_words': p.total_words,
                    'words_to_review': p.words_to_review,
                    'words_completed': p.words_completed,
                    'created_at': p.created_at.isoformat() if p.created_at else None,
                }
                for p in projects
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>', methods=['GET'])
@jwt_required
def get_project(project_id):
    """Obtiene detalles de un proyecto"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        session.close()
        
        if not project:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        return jsonify({
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'total_words': project.total_words,
                'words_to_review': project.words_to_review,
                'words_completed': project.words_completed,
                'created_at': project.created_at.isoformat() if project.created_at else None,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ENDPOINTS PARA PALABRAS ====================

@transcription_bp.route('/projects/<project_id>/words', methods=['GET'])
@jwt_required
def list_words(project_id):
    """Lista palabras pendientes de un proyecto (filtrado por rol)"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # Verificar que el proyecto existe
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            session.close()
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        # Parámetros de paginación
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status', 'pending')
        
        # Construir query base
        query = session.query(Word).filter_by(project_id=project_id)
        
        if status:
            query = query.filter_by(status=status)
        
        # Filtrar por rol: anotadores ven solo sus palabras asignadas
        user = session.query(User).filter_by(id=request.user_id).first()
        if user and user.role != 'admin':
            query = query.filter_by(annotator_id=request.user_id)
        
        total = query.count()
        words = query.offset(offset).limit(limit).all()
        session.close()
        
        return jsonify({
            'total': total,
            'limit': limit,
            'offset': offset,
            'words': [
                {
                    'id': w.id,
                    'word': w.word,
                    'speaker': w.speaker,
                    'probability': w.probability,
                    'start_time': w.start_time,
                    'end_time': w.end_time,
                    'alignment_score': w.alignment_score,
                    'status': w.status,
                    'annotator_id': w.annotator_id,
                }
                for w in words
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/words/<int:word_id>', methods=['GET'])
@jwt_required
def get_word(project_id, word_id):
    """Obtiene detalles de una palabra"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        word = session.query(Word).filter_by(id=word_id, project_id=project_id).first()
        
        if not word:
            session.close()
            return jsonify({'error': 'Palabra no encontrada'}), 404
        
        # Verificar acceso
        user = session.query(User).filter_by(id=request.user_id).first()
        if user and user.role != 'admin' and word.annotator_id != request.user_id:
            session.close()
            return jsonify({'error': 'Acceso denegado'}), 403
        
        session.close()
        
        return jsonify({
            'word': {
                'id': word.id,
                'project_id': word.project_id,
                'audio_filename': word.audio_filename,
                'word': word.word,
                'speaker': word.speaker,
                'probability': word.probability,
                'start_time': word.start_time,
                'end_time': word.end_time,
                'alignment_score': word.alignment_score,
                'status': word.status,
                'annotator_id': word.annotator_id,
                'corrected_text': word.corrected_text,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/words/<int:word_id>/audio', methods=['GET'])
@jwt_required
def get_word_audio(project_id, word_id):
    """Descarga segmento de audio para una palabra"""
    try:
        import wave
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        word = session.query(Word).filter_by(id=word_id, project_id=project_id).first()
        
        if not word:
            session.close()
            return jsonify({'error': 'Palabra no encontrada'}), 404
        
        # Verificar acceso
        user = session.query(User).filter_by(id=request.user_id).first()
        if user and user.role != 'admin' and word.annotator_id != request.user_id:
            session.close()
            return jsonify({'error': 'Acceso denegado'}), 403
        
        session.close()
        
        # Obtener ruta del audio
        audio_service = get_audio_service()
        project_path = audio_service.get_project_path(project_id)
        audio_path = os.path.join(project_path, word.audio_filename)
        
        if not os.path.exists(audio_path):
            current_app.logger.error(f'Archivo de audio no encontrado: {audio_path}')
            return jsonify({'error': f'Archivo de audio no encontrado'}), 404
        
        try:
            margin = float(request.args.get('margin', 0.2))
            
            # Leer archivo WAV y extraer segmento
            with wave.open(audio_path, 'rb') as wav_file:
                # Obtener parámetros
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                
                # Calcular índices de frames
                start_frame = max(0, int((word.start_time - margin) * framerate))
                end_frame = min(n_frames, int((word.end_time + margin) * framerate))
                
                # Leer datos
                wav_file.setpos(start_frame)
                frames = wav_file.readframes(end_frame - start_frame)
            
            # Crear nuevo archivo WAV en memoria
            output_buffer = io.BytesIO()
            with wave.open(output_buffer, 'wb') as output_wav:
                output_wav.setnchannels(n_channels)
                output_wav.setsampwidth(sample_width)
                output_wav.setframerate(framerate)
                output_wav.writeframes(frames)
            
            output_buffer.seek(0)
            audio_bytes = output_buffer.getvalue()
            
            current_app.logger.info(
                f'Audio segmento: {word.word} '
                f'({word.start_time:.2f}-{word.end_time:.2f}s) '
                f'con margen {margin}s = {len(audio_bytes)} bytes'
            )
            
            return send_file(
                io.BytesIO(audio_bytes),
                mimetype='audio/wav',
                as_attachment=False,
                download_name=f"word_{word_id}.wav"
            )
        except Exception as e:
            current_app.logger.error(f'Error procesando audio: {str(e)}', exc_info=True)
            return jsonify({'error': f'Error al procesar audio: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f'Error en get_word_audio: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# ==================== ENDPOINTS PARA ANOTACIÓN ====================

@transcription_bp.route('/words/<int:word_id>', methods=['POST'])
@jwt_required
def submit_correction(word_id):
    """Envía una corrección de palabra"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        data = request.get_json()
        status = data.get('status')
        corrected_text = data.get('corrected_text')
        
        if status not in ['approved', 'corrected']:
            session.close()
            return jsonify({'error': 'Status debe ser "approved" o "corrected"'}), 400
        
        word = session.query(Word).filter_by(id=word_id).first()
        
        if not word:
            session.close()
            return jsonify({'error': 'Palabra no encontrada'}), 404
        
        # Verificar que el usuario tenga permiso
        user = session.query(User).filter_by(id=request.user_id).first()
        is_admin = user and user.role == 'admin'
        is_assigned = word.annotator_id == request.user_id
        
        # Admin puede editar cualquier palabra, anotadores solo sus asignadas
        if not is_admin and not is_assigned:
            session.close()
            return jsonify({'error': 'Acceso denegado - palabra no asignada a ti'}), 403
        
        # Actualizar palabra
        word.status = status
        if corrected_text:
            word.corrected_text = corrected_text
        word.completed_at = datetime.now(timezone.utc)
        
        # Actualizar proyecto
        project = session.query(TranscriptionProject).filter_by(id=word.project_id).first()
        if project:
            completed = session.query(Word).filter(
                Word.project_id == word.project_id,
                Word.status.in_(['approved', 'corrected'])
            ).count()
            project.words_completed = completed
        
        session.commit()
        session.close()
        
        return jsonify({'message': 'Palabra actualizada'}), 200
        
    except Exception as e:
        current_app.logger.error(f'Error en submit_correction: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# ==================== ENDPOINTS PARA ESTADÍSTICAS ====================

@transcription_bp.route('/projects/<project_id>/stats', methods=['GET'])
@jwt_required
def get_stats(project_id):
    """Obtiene estadísticas del proyecto"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            session.close()
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        # Obtener usuario
        user = session.query(User).filter_by(id=request.user_id).first()
        
        # Si es admin, mostrar stats por anotador
        if user and user.role == 'admin':
            annotators = session.query(User).filter_by(role='annotator').all()
            stats_by_annotator = {}
            
            for annotator in annotators:
                total = session.query(Word).filter_by(
                    project_id=project_id,
                    annotator_id=annotator.id
                ).count()
                completed = session.query(Word).filter_by(
                    project_id=project_id,
                    annotator_id=annotator.id,
                    status__in=['approved', 'corrected']
                ).count()
                
                stats_by_annotator[annotator.username] = {
                    'total': total,
                    'completed': completed,
                    'pending': total - completed,
                    'progress': round((completed / total * 100) if total > 0 else 0, 2)
                }
            
            session.close()
            
            return jsonify({
                'project_id': project_id,
                'project_name': project.name,
                'total_words': project.total_words,
                'words_completed': project.words_completed,
                'words_pending': project.total_words - project.words_completed,
                'overall_progress': round((project.words_completed / project.total_words * 100) if project.total_words > 0 else 0, 2),
                'by_annotator': stats_by_annotator
            }), 200
        else:
            # Si es anotador, mostrar solo sus stats
            total = session.query(Word).filter_by(
                project_id=project_id,
                annotator_id=request.user_id
            ).count()
            completed = session.query(Word).filter_by(
                project_id=project_id,
                annotator_id=request.user_id,
                status__in=['approved', 'corrected']
            ).count()
            
            session.close()
            
            return jsonify({
                'project_id': project_id,
                'project_name': project.name,
                'my_total': total,
                'my_completed': completed,
                'my_pending': total - completed,
                'my_progress': round((completed / total * 100) if total > 0 else 0, 2)
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ENDPOINTS PARA ADMIN ====================

@transcription_bp.route('/projects', methods=['POST'])
@jwt_required
@admin_required
def create_project():
    """Crea un nuevo proyecto (admin)"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        data = request.get_json()
        project_id = data.get('project_id')
        name = data.get('name')
        description = data.get('description')
        
        if not project_id or not name:
            session.close()
            return jsonify({'error': 'project_id y name son requeridos'}), 400
        
        transcription_service = get_transcription_service()
        project = transcription_service.create_or_update_project(
            session, project_id, name, description
        )
        
        session.commit()
        session.close()
        
        return jsonify({'message': 'Proyecto creado', 'project_id': project.id}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/import', methods=['POST'])
@jwt_required
@admin_required
def import_transcripts(project_id):
    """Importa transcripción desde JSON (admin)"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        data = request.get_json()
        audio_filename = data.get('audio_filename')
        transcript_filename = data.get('transcript_filename')
        probability_threshold = float(data.get('probability_threshold', 0.95))
        random_annotators = data.get('random_annotators')
        
        if not audio_filename or not transcript_filename:
            session.close()
            return jsonify({'error': 'audio_filename y transcript_filename requeridos'}), 400
        
        transcription_service = get_transcription_service()
        project, words_added = transcription_service.import_transcript_to_db(
            session,
            project_id,
            audio_filename,
            transcript_filename,
            probability_threshold=probability_threshold,
            random_annotators=random_annotators
        )
        
        session.commit()
        session.close()
        
        return jsonify({
            'message': f'{words_added} palabras importadas',
            'project_id': project.id,
            'words_added': words_added
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/words/<int:word_id>/assign', methods=['POST'])
@jwt_required
@admin_required
def assign_word(project_id, word_id):
    """Asigna una palabra a un anotador (admin)"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        data = request.get_json()
        annotator_id = data.get('annotator_id')
        
        if not annotator_id:
            session.close()
            return jsonify({'error': 'annotator_id requerido'}), 400
        
        word = session.query(Word).filter_by(id=word_id, project_id=project_id).first()
        if not word:
            session.close()
            return jsonify({'error': 'Palabra no encontrada'}), 404
        
        annotator = session.query(User).filter_by(id=annotator_id).first()
        if not annotator:
            session.close()
            return jsonify({'error': 'Anotador no encontrado'}), 404
        
        word.annotator_id = annotator_id
        session.commit()
        session.close()
        
        return jsonify({'message': 'Palabra asignada'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
