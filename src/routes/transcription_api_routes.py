"""
Rutas API para validación de transcripciones de audio
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from functools import wraps
from datetime import datetime, timezone
from models.database import TranscriptionProject, Word, Segment, User, DatabaseManager, SegmentDiscardReason
from services.audio_service import AudioService
from services.transcription_service import TranscriptionService
from services.jwt_service import jwt_service
from services.rate_limiter import rate_limit_service
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


def resolve_available_audio_filename(audio_service, project_id, stored_filename):
    """
    Resuelve el archivo de audio disponible en disco sin requerir conversión previa.
    Intenta variantes comunes (.wav/.mp3 y sufijo _full).
    """
    candidates = []

    def add_candidate(name):
        if name and name not in candidates:
            candidates.append(name)

    add_candidate(stored_filename)

    stem, ext = os.path.splitext(stored_filename)
    ext = ext.lower()

    # Alternar entre wav/mp3 manteniendo el mismo stem
    if ext == '.wav':
        add_candidate(f'{stem}.mp3')
    elif ext == '.mp3':
        add_candidate(f'{stem}.wav')

    # Compatibilidad con naming *_full.{wav|json} y audio base .mp3
    if stem.endswith('_full'):
        base_stem = stem[:-5]
        add_candidate(f'{base_stem}.mp3')
        add_candidate(f'{base_stem}.wav')
        add_candidate(f'{base_stem}_full.mp3')
        add_candidate(f'{base_stem}_full.wav')
    else:
        add_candidate(f'{stem}_full.wav')
        add_candidate(f'{stem}_full.mp3')

    for candidate in candidates:
        if audio_service.audio_exists(project_id, candidate):
            return candidate

    return None

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
            user_id = payload.get('user_id', payload.get('id'))
            if user_id is None:
                return jsonify({'error': 'Token inválido: user_id faltante'}), 401
            try:
                request.user_id = int(user_id)
            except (TypeError, ValueError):
                return jsonify({'error': 'Token inválido: user_id inválido'}), 401
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
    """
    Lista elementos para validación de un proyecto.
    IMPORTANTE: Esta ruta retorna SEGMENTOS (no palabras individuales).
    Cada segmento incluye sus palabras asociadas para contexto.
    """
    try:
        from sqlalchemy.orm import joinedload
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        try:
            # Verificar que el proyecto existe
            project = session.query(TranscriptionProject).filter_by(id=project_id).first()
            if not project:
                return jsonify({'error': 'Proyecto no encontrado'}), 404
            
            # Parámetros de paginación
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))
            status = request.args.get('status', 'pending')  # Maps to review_status for Segments
            
            # Construir query base de Segmentos con eager loading de words
            query = session.query(Segment).options(
                joinedload(Segment.words)
            ).filter_by(project_id=project_id)
            
            # Filtrar por estado (review_status en segmentos)
            if status:
                query = query.filter_by(review_status=status)
                # La cola de revisión solo considera segmentos con palabras bajo el umbral
                if status == 'pending':
                    query = query.filter(Segment.low_prob_word_count > 0)
            
            # Filtrar por rol: anotadores ven solo sus segmentos asignados
            user = session.query(User).filter_by(id=request.user_id).first()
            if not user:
                return jsonify({'error': 'Usuario no encontrado para el token'}), 401
            if user.role != 'admin':
                query = query.filter(Segment.annotator_id == request.user_id)

            # Orden estable para evitar mezcla visual de segmentos
            query = query.order_by(
                Segment.audio_filename.asc(),
                Segment.segment_index.asc(),
                Segment.start_time.asc(),
                Segment.id.asc()
            )
            
            total = query.count()
            segments = query.offset(offset).limit(limit).all()
            
            # Formato compatible con frontend: retornamos "words" pero son segmentos
            result = {
                'total': total,
                'limit': limit,
                'offset': offset,
                'segments': [s.to_dict() for s in segments],
                # Para compatibilidad: también retornamos como 'words'
                'words': [
                    {
                        'id': s.id,
                        'project': s.project_id,
                        'audio_filename': s.audio_filename,
                        'text': s.text,  # El texto completo del segmento
                        'text_revised': s.text_revised,
                        'speaker': s.speaker,
                        'start_time': s.start_time,
                        'end_time': s.end_time,
                        'review_status': s.review_status,
                        'annotator_id': s.annotator_id,
                        'low_prob_word_count': s.low_prob_word_count,
                        'words': [w.to_dict() for w in s.words],  # Palabras asociadas para contexto
                    }
                    for s in segments
                ]
            }
            
            return jsonify(result), 200
            
        finally:
            session.close()
        
    except Exception as e:
        current_app.logger.error(f'Error en list_words: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/words/<int:word_id>', methods=['GET'])
@jwt_required
def get_word(project_id, word_id):
    """
    Obtiene detalles de un segmento (el word_id es en realidad segment_id).
    Retorna el segmento completo con todas sus palabras asociadas.
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # Buscar el segmento (no la palabra)
        segment = session.query(Segment).filter_by(
            id=word_id,
            project_id=project_id
        ).first()
        
        if not segment:
            session.close()
            return jsonify({'error': 'Segmento no encontrado'}), 404
        
        # Verificar acceso
        user = session.query(User).filter_by(id=request.user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'Usuario no encontrado para el token'}), 401
        if user.role != 'admin' and segment.annotator_id != request.user_id:
            # Allow if not assigned yet or if assigned to this user
            if segment.annotator_id is not None and segment.annotator_id != request.user_id:
                session.close()
                return jsonify({'error': 'Acceso denegado'}), 403
        
        session.close()
        
        return jsonify({
            'word': segment.to_dict(include_words=True)  # Returns as 'word' for backward compatibility
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error en get_word: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/words/<int:word_id>/audio', methods=['GET'])
@jwt_required
def get_word_audio(project_id, word_id):
    """
    Descarga el audio del segmento (word_id es en realidad segment_id).
    Extrae el audio entre start_time y end_time del segmento.
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # Buscar el segmento
        segment = session.query(Segment).filter_by(
            id=word_id,
            project_id=project_id
        ).first()
        
        if not segment:
            session.close()
            return jsonify({'error': 'Segmento no encontrado'}), 404
        
        # Verificar acceso
        user = session.query(User).filter_by(id=request.user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'Usuario no encontrado para el token'}), 401
        if user.role != 'admin' and segment.annotator_id != request.user_id:
            if segment.annotator_id is not None:
                session.close()
                return jsonify({'error': 'Acceso denegado'}), 403
        
        session.close()
        
        audio_service = get_audio_service()

        try:
            margin = float(request.args.get('margin', 0.2))
            
            # Soporte para rango personalizado (contexto extendido)
            start_override = request.args.get('start_override', type=float)
            end_override = request.args.get('end_override', type=float)
            
            if start_override is not None and end_override is not None:
                audio_start = max(0, start_override - margin)
                audio_end = end_override + margin
            else:
                audio_start = max(0, segment.start_time - margin)
                audio_end = segment.end_time + margin

            # Resolver archivo existente en disco sin modificar formatos fuente
            resolved_audio_filename = resolve_available_audio_filename(
                audio_service,
                project_id,
                segment.audio_filename
            )
            if not resolved_audio_filename:
                current_app.logger.error(
                    f'Archivo de audio no encontrado para "{segment.audio_filename}" '
                    f'en proyecto "{project_id}"'
                )
                return jsonify({'error': 'Archivo de audio no encontrado'}), 404

            # Extraer segmento desde el formato fuente (wav/mp3) y retornarlo como WAV en memoria
            audio_bytes = audio_service.get_audio_segment_as_wav(
                project_id=project_id,
                audio_filename=resolved_audio_filename,
                start_time=audio_start,
                end_time=audio_end,
                margin_seconds=0.0,  # margin ya aplicado en audio_start/audio_end
                sr=16000
            )
            
            current_app.logger.info(
                f'Audio segmento: "{segment.text[:50]}..." '
                f'file={resolved_audio_filename} '
                f'({segment.start_time:.2f}-{segment.end_time:.2f}s) '
                f'con margen {margin}s = {len(audio_bytes)} bytes'
            )
            
            return send_file(
                io.BytesIO(audio_bytes),
                mimetype='audio/wav',
                as_attachment=False,
                download_name=f"segment_{word_id}.wav"
            )
        except Exception as e:
            current_app.logger.error(f'Error procesando audio: {str(e)}', exc_info=True)
            return jsonify({'error': f'Error al procesar audio: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f'Error en get_word_audio: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@transcription_bp.route('/projects/<project_id>/words/<int:word_id>/context', methods=['GET'])
@jwt_required
def get_segment_context(project_id, word_id):
    """
    Devuelve los segmentos adyacentes (anterior y siguiente) para dar contexto.
    También devuelve el rango de tiempo extendido para reproducir audio con contexto.
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()

        # Segmento actual
        segment = session.query(Segment).filter_by(
            id=word_id,
            project_id=project_id
        ).first()

        if not segment:
            session.close()
            return jsonify({'error': 'Segmento no encontrado'}), 404

        # Buscar segmento anterior (mismo audio, segment_index - 1)
        prev_seg = session.query(Segment).filter_by(
            project_id=project_id,
            audio_filename=segment.audio_filename,
            segment_index=segment.segment_index - 1
        ).first()

        # Buscar segmento siguiente (mismo audio, segment_index + 1)
        next_seg = session.query(Segment).filter_by(
            project_id=project_id,
            audio_filename=segment.audio_filename,
            segment_index=segment.segment_index + 1
        ).first()

        # Rango de tiempo extendido
        extended_start = prev_seg.start_time if prev_seg else segment.start_time
        extended_end = next_seg.end_time if next_seg else segment.end_time

        result = {
            'segment_id': segment.id,
            'extended_start': extended_start,
            'extended_end': extended_end,
            'prev': {
                'id': prev_seg.id,
                'text': prev_seg.text,
                'start_time': prev_seg.start_time,
                'end_time': prev_seg.end_time
            } if prev_seg else None,
            'next': {
                'id': next_seg.id,
                'text': next_seg.text,
                'start_time': next_seg.start_time,
                'end_time': next_seg.end_time
            } if next_seg else None
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f'Error en get_segment_context: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ==================== ENDPOINTS PARA ANOTACIÓN ====================

@transcription_bp.route('/words/<int:word_id>', methods=['POST'])
@jwt_required
@rate_limit_service.limit_submit  # 60 submisiones por minuto
def submit_correction(word_id):
    """
    Envía una corrección para un segmento (word_id es en realidad segment_id).
    Actualiza el texto revisado y el estado del segmento.
    """
    session = None
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        data = request.get_json()
        review_status = data.get('review_status', data.get('status'))  # Support both names
        text_revised = data.get('text_revised', data.get('corrected_text'))
        discard_reason_type = (data.get('discard_reason_type') or '').strip()
        discard_reason_note = (data.get('discard_reason_note') or '').strip()
        
        if review_status not in ['approved', 'corrected', 'pending', 'discarded']:
            session.close()
            return jsonify({'error': 'review_status debe ser "approved", "corrected", "discarded" o "pending"'}), 400

        if review_status == 'discarded':
            valid_discard_reasons = {'not_chilean_spanish', 'other'}
            if discard_reason_type not in valid_discard_reasons:
                session.close()
                return jsonify({'error': 'discard_reason_type debe ser "not_chilean_spanish" o "other"'}), 400
            if discard_reason_type == 'other' and not discard_reason_note:
                session.close()
                return jsonify({'error': 'discard_reason_note es requerido cuando discard_reason_type = "other"'}), 400
        
        # Buscar el segmento
        segment = session.query(Segment).filter_by(id=word_id).first()
        
        if not segment:
            session.close()
            return jsonify({'error': f'Segmento {word_id} no encontrado'}), 404
        
        # Verificar permisos
        user = session.query(User).filter_by(id=request.user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'Usuario no encontrado para el token'}), 401
        is_admin = user.role == 'admin'
        
        # Admin puede editar cualquier segmento
        # Anotadores pueden editar segmentos sin asignar o asignados a ellos
        if not is_admin:
            if segment.annotator_id and segment.annotator_id != request.user_id:
                session.close()
                return jsonify({'error': 'Acceso denegado - segmento no asignado a ti'}), 403
        
        # Actualizar segmento
        segment.review_status = review_status
        if text_revised:
            segment.text_revised = text_revised
        elif review_status == 'discarded':
            # Mantener el texto original visible aunque se descarte.
            segment.text_revised = segment.text

        if review_status == 'discarded':
            discard_reason = session.query(SegmentDiscardReason).filter_by(segment_id=segment.id).first()
            if not discard_reason:
                discard_reason = SegmentDiscardReason(
                    segment_id=segment.id,
                    project_id=segment.project_id,
                    annotator_id=request.user_id,
                    reason_type=discard_reason_type,
                    reason_note=discard_reason_note or None
                )
                session.add(discard_reason)
            else:
                discard_reason.annotator_id = request.user_id
                discard_reason.reason_type = discard_reason_type
                discard_reason.reason_note = discard_reason_note or None
                discard_reason.updated_at = datetime.now(timezone.utc)
        elif segment.discard_reason:
            # Si el segmento deja de estar descartado, limpiar motivo anterior.
            session.delete(segment.discard_reason)
        
        # Si no estaba asignado, asignarlo ahora
        if not segment.annotator_id:
            segment.annotator_id = request.user_id
        
        # Timestamps
        segment.updated_at = datetime.now(timezone.utc)
        if review_status in ['approved', 'corrected', 'discarded']:
            segment.completed_at = datetime.now(timezone.utc)
        else:
            segment.completed_at = None
        
        # Actualizar estadísticas del proyecto
        project = session.query(TranscriptionProject).filter_by(id=segment.project_id).first()
        if project:
            # Recalcular estadísticas después del cambio
            session.flush()  # Asegurar que los cambios se vean en las consultas
            
            completed = session.query(Segment).filter(
                Segment.project_id == segment.project_id,
                Segment.low_prob_word_count > 0,
                Segment.review_status.in_(['approved', 'corrected', 'discarded'])
            ).count()
            total = session.query(Segment).filter(
                Segment.project_id == segment.project_id,
                Segment.low_prob_word_count > 0
            ).count()
            
            project.words_completed = completed
            project.words_to_review = total
            
            current_app.logger.info(f'Segmento {word_id} actualizado: status={review_status}, proyecto stats: {completed}/{total}')
        
        # Capture values before closing session
        segment_id = segment.id
        final_review_status = segment.review_status
        
        session.commit()
        session.close()
        
        return jsonify({
            'message': 'Segmento actualizado',
            'segment_id': segment_id,
            'review_status': final_review_status,
            'discard_reason_type': discard_reason_type if final_review_status == 'discarded' else None,
            'discard_reason_note': discard_reason_note if final_review_status == 'discarded' else None
        }), 200
        
    except Exception as e:
        if session:
            try:
                session.rollback()
                session.close()
            except:
                pass
        current_app.logger.error(f'Error en submit_correction: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# ==================== ENDPOINTS PARA ESTADÍSTICAS ====================

@transcription_bp.route('/projects/<project_id>/stats', methods=['GET'])
@jwt_required
def get_stats(project_id):
    """Obtiene estadísticas del proyecto - BASADO EN SEGMENTOS"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            session.close()
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        # Obtener usuario
        user = session.query(User).filter_by(id=request.user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'Usuario no encontrado para el token'}), 401
        
        # Estadísticas generales por estado de segmento
        reviewable_base = session.query(Segment).filter(
            Segment.project_id == project_id,
            Segment.low_prob_word_count > 0
        )
        total_segments = reviewable_base.count()
        pending_segments = reviewable_base.filter(Segment.review_status == 'pending').count()
        approved_segments = reviewable_base.filter(Segment.review_status == 'approved').count()
        corrected_segments = reviewable_base.filter(Segment.review_status == 'corrected').count()
        discarded_segments = reviewable_base.filter(Segment.review_status == 'discarded').count()
        
        # Si es admin, mostrar stats por anotador
        if user and user.role == 'admin':
            annotators = session.query(User).filter_by(role='annotator').all()
            stats_by_annotator = {}
            
            for annotator in annotators:
                annotator_total = session.query(Segment).filter(
                    Segment.project_id == project_id,
                    Segment.annotator_id == annotator.id,
                    Segment.low_prob_word_count > 0
                ).count()
                annotator_completed = session.query(Segment).filter(
                    Segment.project_id == project_id,
                    Segment.annotator_id == annotator.id,
                    Segment.low_prob_word_count > 0,
                    Segment.review_status.in_(['approved', 'corrected', 'discarded'])
                ).count()
                annotator_discarded = session.query(Segment).filter(
                    Segment.project_id == project_id,
                    Segment.annotator_id == annotator.id,
                    Segment.low_prob_word_count > 0,
                    Segment.review_status == 'discarded'
                ).count()
                
                stats_by_annotator[annotator.username] = {
                    'total': annotator_total,
                    'completed': annotator_completed,
                    'discarded': annotator_discarded,
                    'pending': annotator_total - annotator_completed,
                    'progress': round((annotator_completed / annotator_total * 100) if annotator_total > 0 else 0, 2)
                }
            
            session.close()
            
            return jsonify({
                'project_id': project_id,
                'project_name': project.name,
                'total_segments': total_segments,
                'pending_segments': pending_segments,
                'approved_segments': approved_segments,
                'corrected_segments': corrected_segments,
                'discarded_segments': discarded_segments,
                'overall_progress': round(((approved_segments + corrected_segments + discarded_segments) / total_segments * 100) if total_segments > 0 else 0, 2),
                'by_annotator': stats_by_annotator
            }), 200
        else:
            # Si es anotador, mostrar solo sus stats
            user_total = session.query(Segment).filter(
                Segment.project_id == project_id,
                Segment.annotator_id == request.user_id,
                Segment.low_prob_word_count > 0
            ).count()
            user_completed = session.query(Segment).filter(
                Segment.project_id == project_id,
                Segment.annotator_id == request.user_id,
                Segment.low_prob_word_count > 0,
                Segment.review_status.in_(['approved', 'corrected', 'discarded'])
            ).count()
            user_discarded = session.query(Segment).filter(
                Segment.project_id == project_id,
                Segment.annotator_id == request.user_id,
                Segment.low_prob_word_count > 0,
                Segment.review_status == 'discarded'
            ).count()
            
            session.close()
            
            return jsonify({
                'project_id': project_id,
                'project_name': project.name,
                'total_segments': total_segments,
                'pending_segments': pending_segments,
                'discarded_segments': discarded_segments,
                'my_total': user_total,
                'my_completed': user_completed,
                'my_discarded': user_discarded,
                'my_pending': user_total - user_completed,
                'my_progress': round((user_completed / user_total * 100) if user_total > 0 else 0, 2)
            }), 200
        
    except Exception as e:
        session.close()
        current_app.logger.error(f'Error en get_stats: {str(e)}', exc_info=True)
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


# ==================== ENDPOINTS PARA SEGMENTOS (Nueva arquitectura) ====================

@transcription_bp.route('/projects/<project_id>/segments', methods=['GET'])
@jwt_required
def list_segments(project_id):
    """
    Lista segmentos de un proyecto
    Query params:
    - status: 'pending', 'approved', 'corrected', 'discarded' (default: pending)
    - limit: Límite de resultados (default: 100)
    - offset: Offset para paginación (default: 0)
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # Validar que el proyecto exista
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            session.close()
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        # Parámetros
        status = request.args.get('status', 'pending')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Listar segmentos
        query = session.query(Segment).filter_by(project_id=project_id, review_status=status)
        query = query.order_by(
            Segment.audio_filename.asc(),
            Segment.segment_index.asc(),
            Segment.start_time.asc(),
            Segment.id.asc()
        )
        total = query.count()
        segments = query.limit(limit).offset(offset).all()
        
        # Convertir a dict ANTES de cerrar la sesión (para evitar DetachedInstanceError)
        segments_data = [s.to_dict() for s in segments]
        
        session.close()
        
        return jsonify({
            'segments': segments_data,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error en list_segments: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/segments/<int:segment_id>', methods=['GET'])
@jwt_required
def get_segment(project_id, segment_id):
    """
    Obtiene detalles completos de un segmento (incluyendo sus palabras)
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        segment = session.query(Segment).filter_by(
            id=segment_id,
            project_id=project_id
        ).first()
        
        if not segment:
            session.close()
            return jsonify({'error': 'Segmento no encontrado'}), 404
        
        result = segment.to_dict(include_words=True)
        session.close()
        
        return jsonify({'segment': result}), 200
        
    except Exception as e:
        current_app.logger.error(f'Error en get_segment: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/segments/<int:segment_id>/audio', methods=['GET'])
@jwt_required
def get_segment_audio(project_id, segment_id):
    """
    Descarga el audio de un segmento específico
    Query params:
    - margin: Margen de tiempo adicional antes/después (segundos, default: 0.2)
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        segment = session.query(Segment).filter_by(
            id=segment_id,
            project_id=project_id
        ).first()
        
        if not segment:
            session.close()
            return jsonify({'error': 'Segmento no encontrado'}), 404
        
        # Parámetro de margen
        margin = request.args.get('margin', 0.2, type=float)
        
        # Obtener servicio de audio
        audio_service = get_audio_service()
        
        # Ruta del archivo de audio
        audio_dir = os.path.join(
            os.path.dirname(__file__),
            '..',
            'data',
            'transcription_projects',
            project_id
        )
        
        # Extraer y enviar audio
        audio_bytes = audio_service.extract_frame_segment(
            project_dir=audio_dir,
            filename=segment.audio_filename,
            start_time=segment.start_time - margin,
            end_time=segment.end_time + margin
        )
        
        session.close()
        
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype='audio/wav',
            as_attachment=True,
            download_name=f'segment_{segment.segment_index}.wav'
        )
        
    except Exception as e:
        current_app.logger.error(f'Error en get_segment_audio: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/segments/<int:segment_id>', methods=['POST'])
@jwt_required
def submit_segment_correction(segment_id):
    """
    Envía una corrección de segmento
    POST body:
    {
        "text_revised": "Texto corregido del segmento completo",
        "review_status": "approved" o "corrected"
    }
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        data = request.get_json()
        text_revised = data.get('text_revised')
        review_status = data.get('review_status', 'corrected')
        discard_reason_type = (data.get('discard_reason_type') or '').strip()
        discard_reason_note = (data.get('discard_reason_note') or '').strip()
        
        # Validar entrada
        if review_status not in ['approved', 'corrected', 'discarded']:
            session.close()
            return jsonify({'error': 'review_status debe ser "approved", "corrected" o "discarded"'}), 400

        if review_status == 'discarded':
            valid_discard_reasons = {'not_chilean_spanish', 'other'}
            if discard_reason_type not in valid_discard_reasons:
                session.close()
                return jsonify({'error': 'discard_reason_type debe ser "not_chilean_spanish" o "other"'}), 400
            if discard_reason_type == 'other' and not discard_reason_note:
                session.close()
                return jsonify({'error': 'discard_reason_note es requerido cuando discard_reason_type = "other"'}), 400
        
        # Obtener segmento
        segment = session.query(Segment).filter_by(id=segment_id).first()
        if not segment:
            session.close()
            return jsonify({'error': 'Segmento no encontrado'}), 404
        
        # Actualizar segmento
        segment.text_revised = text_revised
        segment.review_status = review_status
        segment.annotator_id = request.user_id
        segment.updated_at = datetime.now(timezone.utc)
        
        if review_status == 'discarded':
            if not segment.text_revised:
                segment.text_revised = segment.text
            discard_reason = session.query(SegmentDiscardReason).filter_by(segment_id=segment.id).first()
            if not discard_reason:
                discard_reason = SegmentDiscardReason(
                    segment_id=segment.id,
                    project_id=segment.project_id,
                    annotator_id=request.user_id,
                    reason_type=discard_reason_type,
                    reason_note=discard_reason_note or None
                )
                session.add(discard_reason)
            else:
                discard_reason.annotator_id = request.user_id
                discard_reason.reason_type = discard_reason_type
                discard_reason.reason_note = discard_reason_note or None
                discard_reason.updated_at = datetime.now(timezone.utc)
        elif segment.discard_reason:
            session.delete(segment.discard_reason)

        if review_status in ['approved', 'corrected', 'discarded']:
            segment.completed_at = datetime.now(timezone.utc)
        else:
            segment.completed_at = None

        segment_data = segment.to_dict()
        
        session.commit()
        session.close()
        
        return jsonify({
            'message': 'Segmento actualizado',
            'segment': segment_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error en submit_segment_correction: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/projects/<project_id>/segments/stats', methods=['GET'])
@jwt_required
def get_segments_stats(project_id):
    """
    Obtiene estadísticas de segmentos de un proyecto
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            session.close()
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        
        reviewable_base = session.query(Segment).filter(
            Segment.project_id == project_id,
            Segment.low_prob_word_count > 0
        )
        total = reviewable_base.count()
        pending = reviewable_base.filter(Segment.review_status == 'pending').count()
        approved = reviewable_base.filter(Segment.review_status == 'approved').count()
        corrected = reviewable_base.filter(Segment.review_status == 'corrected').count()
        discarded = reviewable_base.filter(Segment.review_status == 'discarded').count()
        
        session.close()
        
        return jsonify({
            'total_segments': total,
            'pending': pending,
            'approved': approved,
            'corrected': corrected,
            'discarded': discarded,
            'progress': round((approved + corrected + discarded) / total * 100, 2) if total > 0 else 0
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error en get_segments_stats: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500
