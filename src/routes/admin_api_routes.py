"""
Rutas API para administración - Panel administrativo Phase 2
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from functools import wraps
from datetime import datetime, timezone
from models.database import User, TranscriptionProject, Segment, SegmentDiscardReason, DatabaseManager
from services.jwt_service import jwt_service
from config import Config
import logging
import io
import os

logger = logging.getLogger(__name__)

# Blueprint
admin_bp = Blueprint('admin_api', __name__, url_prefix='/api/v1/admin')

# Inicializar servicios
_db_manager = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        config = Config.from_env()
        _db_manager = DatabaseManager(config.DATABASE_URL)
    return _db_manager

# ==================== DECORADORES ====================

def admin_required(f):
    """Requiere ser admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            payload = jwt_service.verify_access_token(token)
            if payload.get('role') != 'admin':
                return jsonify({'error': 'User is not admin'}), 403

            # Compatibilidad de claims: algunos tokens usan `user_id`, otros `id`.
            current_user_id = payload.get('user_id', payload.get('id'))
            if current_user_id is None:
                logger.error(f"Admin token missing user id claim: {payload}")
                return jsonify({'error': 'Invalid token payload'}), 401

            request.current_user = payload
            request.current_user_id = current_user_id
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Admin token error: {e}")
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated

# ==================== USUARIOS ====================

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """Lista todos los usuarios"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        users = session.query(User).all()
        session.close()
        
        return jsonify({
            'users': [
                {
                    'id': u.id,
                    'username': u.username,
                    'role': u.role
                }
                for u in users
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    """Crea un nuevo usuario"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'annotator')
        
        if not username or len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
        
        if not password or len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        if role not in ['admin', 'annotator']:
            return jsonify({'error': 'Invalid role'}), 400
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # Verificar si existe
        existing = session.query(User).filter_by(username=username).first()
        if existing:
            session.close()
            return jsonify({'error': 'User already exists'}), 409
        
        # Crear usuario
        user = User(username=username, password=password, role=role)
        session.add(user)
        session.commit()
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
        session.close()
        
        return jsonify({'message': f'User {username} created', 'user': user_data}), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Elimina un usuario y revierte sus anotaciones para mantener consistencia"""
    session = None
    try:
        current_admin_id = getattr(request, 'current_user_id', None)
        if current_admin_id is None:
            current_admin_id = request.current_user.get('user_id', request.current_user.get('id'))

        try:
            current_admin_id = int(current_admin_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid current user id in token'}), 401

        if user_id == current_admin_id:
            return jsonify({'error': 'Cannot delete yourself'}), 403
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'User not found'}), 404
        
        username = user.username
        now_utc = datetime.now(timezone.utc)

        # 1) Identificar proyectos impactados para recalcular métricas al final.
        affected_project_ids = [
            pid for (pid,) in session.query(Segment.project_id).filter(
                Segment.annotator_id == user_id
            ).distinct().all()
        ]

        # 2) Obtener IDs de segmentos tocados por el usuario.
        affected_segment_ids = [
            sid for (sid,) in session.query(Segment.id).filter(
                Segment.annotator_id == user_id
            ).all()
        ]

        # 3) Revertir TODO el trabajo del usuario: deja segmentos como al inicio.
        reverted_segments = session.query(Segment).filter(
            Segment.annotator_id == user_id
        ).update(
            {
                Segment.annotator_id: None,
                Segment.review_status: 'pending',
                Segment.text_revised: None,
                Segment.completed_at: None,
                Segment.updated_at: now_utc
            },
            synchronize_session=False
        )

        # 4) Borrar motivos de descarte ligados a segmentos trabajados por el usuario.
        deleted_discard_reasons_by_segment = 0
        if affected_segment_ids:
            deleted_discard_reasons_by_segment = session.query(SegmentDiscardReason).filter(
                SegmentDiscardReason.segment_id.in_(affected_segment_ids)
            ).delete(synchronize_session=False)

        # 5) Limpieza defensiva de filas que sigan apuntando al usuario.
        deleted_discard_reasons_by_user = session.query(SegmentDiscardReason).filter(
                SegmentDiscardReason.annotator_id == user_id
        ).delete(synchronize_session=False)

        # 6) Recalcular words_completed para cada proyecto afectado.
        completed_statuses = ['approved', 'corrected', 'discarded']
        for project_id in affected_project_ids:
            completed_count = session.query(Segment).filter(
                Segment.project_id == project_id,
                Segment.review_status.in_(completed_statuses)
            ).count()
            session.query(TranscriptionProject).filter_by(id=project_id).update(
                {
                    TranscriptionProject.words_completed: completed_count,
                    TranscriptionProject.updated_at: now_utc
                },
                synchronize_session=False
            )

        session.delete(user)
        session.commit()
        session.close()
        
        return jsonify({
            'message': f'User {username} deleted',
            'reverted_segments': int(reverted_segments or 0),
            'deleted_discard_reasons': int((deleted_discard_reasons_by_segment or 0) + (deleted_discard_reasons_by_user or 0)),
            # Compatibilidad con payload anterior
            'unassigned_segments': int(reverted_segments or 0),
            'updated_discard_reasons': 0
        }), 200
        
    except Exception as e:
        if session:
            try:
                session.rollback()
                session.close()
            except Exception:
                pass
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>/stats', methods=['GET'])
@admin_required
def get_user_stats(user_id):
    """Obtiene estadísticas de un usuario"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Contar segmentos asignados y completados (solo revisables: low_prob_word_count > 0)
        user_base = session.query(Segment).filter(
            Segment.annotator_id == user_id,
            Segment.low_prob_word_count > 0
        )
        total_assigned = user_base.count()
        approved = user_base.filter(Segment.review_status == 'approved').count()
        corrected = user_base.filter(Segment.review_status == 'corrected').count()
        discarded = user_base.filter(Segment.review_status == 'discarded').count()
        completed = user_base.filter(
            Segment.review_status.in_(['approved', 'corrected', 'discarded'])
        ).count()
        
        session.close()
        
        return jsonify({
            'user_id': user_id,
            'username': user.username,
            'total_segments': total_assigned,
            'approved_segments': approved,
            'corrected_segments': corrected,
            'discarded_segments': discarded,
            'pending_segments': total_assigned - completed,
            'words_completed_percentage': round((completed / total_assigned * 100), 2) if total_assigned > 0 else 0
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== PROYECTOS ====================

@admin_bp.route('/projects', methods=['GET'])
@admin_required
def list_projects():
    """Lista todos los proyectos"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        projects = session.query(TranscriptionProject).all()
        session.close()
        
        return jsonify({
            'projects': [
                {
                    'id': p.id,
                    'name': p.name,
                    'description': p.description
                }
                for p in projects
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/projects/<project_id>/stats', methods=['GET'])
@admin_required
def get_project_stats(project_id):
    """Obtiene estadísticas de un proyecto"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            session.close()
            return jsonify({'error': 'Project not found'}), 404
        
        reviewable_base = session.query(Segment).filter(
            Segment.project_id == project_id,
            Segment.low_prob_word_count > 0
        )
        total_segments = reviewable_base.count()
        pending = reviewable_base.filter(Segment.review_status == 'pending').count()
        approved = reviewable_base.filter(Segment.review_status == 'approved').count()
        corrected = reviewable_base.filter(Segment.review_status == 'corrected').count()
        discarded = reviewable_base.filter(Segment.review_status == 'discarded').count()
        
        # Contar anotadores
        from sqlalchemy import func, distinct
        total_annotators = session.query(func.count(distinct(Segment.annotator_id))).filter_by(project_id=project_id).scalar() or 0
        
        session.close()
        
        return jsonify({
            'project_id': project_id,
            'total_segments': total_segments,
            'pending_segments': pending,
            'approved_segments': approved,
            'corrected_segments': corrected,
            'discarded_segments': discarded,
            'words_completed_percentage': round(((approved + corrected + discarded) / total_segments * 100), 2) if total_segments > 0 else 0,
            'total_annotators': total_annotators
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting project stats: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== SEGMENTOS ====================

@admin_bp.route('/projects/<project_id>/segments', methods=['GET'])
@admin_required
def list_segments(project_id):
    """Lista segmentos de un proyecto"""
    try:
        status = request.args.get('status', 'all')
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        query = session.query(Segment).filter_by(project_id=project_id)
        
        if status != 'all':
            if status == 'pending':
                query = query.filter_by(review_status='pending').filter(
                    Segment.annotator_id.is_(None),
                    Segment.low_prob_word_count > 0
                )
            elif status == 'completed':
                query = query.filter(Segment.review_status.in_(['approved', 'corrected', 'discarded']))

        query = query.order_by(
            Segment.audio_filename.asc(),
            Segment.segment_index.asc(),
            Segment.start_time.asc(),
            Segment.id.asc()
        )

        segments = query.all()
        session.close()
        
        return jsonify({
            'words': [  # Mantener nombre 'words' por compatibility
                {
                    'id': s.id,
                    'audio_filename': s.audio_filename,
                    'segment_index': s.segment_index,
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'text': s.text,
                    'status': s.review_status,
                    'assigned_to': s.annotator_id,
                    'created_at': s.created_at.isoformat() if s.created_at else None
                }
                for s in segments
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing segments: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/projects/<project_id>/segments/<int:segment_id>/assign', methods=['POST'])
@admin_required
def assign_segment(project_id, segment_id):
    """Asigna un segmento a un anotador"""
    try:
        data = request.get_json()
        annotator_id = data.get('annotator_id')
        
        if not annotator_id:
            return jsonify({'error': 'annotator_id required'}), 400

        try:
            annotator_id = int(annotator_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'annotator_id must be an integer'}), 400
        
        db_manager = get_db_manager()
        session = db_manager.get_session()

        annotator = session.query(User).filter_by(id=annotator_id).first()
        if not annotator:
            session.close()
            return jsonify({'error': 'Annotator not found'}), 404
        
        # Asignación atómica: solo asigna si sigue libre (annotator_id IS NULL).
        # Esto evita que un segundo request sobreescriba la asignación por carrera.
        updated_rows = session.query(Segment).filter(
            Segment.id == segment_id,
            Segment.project_id == project_id,
            Segment.annotator_id.is_(None)
        ).update(
            {
                Segment.annotator_id: annotator_id,
                Segment.updated_at: datetime.now(timezone.utc)
            },
            synchronize_session=False
        )

        if updated_rows == 1:
            session.commit()
            session.close()
            return jsonify({'message': 'Segment assigned', 'segment_id': segment_id}), 200

        session.rollback()
        segment = session.query(Segment).filter_by(
            id=segment_id,
            project_id=project_id
        ).first()

        if not segment:
            session.close()
            return jsonify({'error': 'Segment not found'}), 404

        if segment.annotator_id is not None and int(segment.annotator_id) == annotator_id:
            session.close()
            return jsonify({
                'message': 'Segment already assigned to this annotator',
                'segment_id': segment_id,
                'annotator_id': annotator_id
            }), 200

        session.close()
        return jsonify({
            'error': 'Segment already assigned to another annotator',
            'segment_id': segment_id,
            'assigned_to': segment.annotator_id
        }), 409
        
    except Exception as e:
        logger.error(f"Error assigning segment: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/projects/<project_id>/segments/<int:segment_id>/unassign', methods=['POST'])
@admin_required
def unassign_segment(project_id, segment_id):
    """Desasigna un segmento (lo devuelve al pool de asignables)"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        segment = session.query(Segment).filter_by(
            id=segment_id,
            project_id=project_id
        ).first()
        
        if not segment:
            session.close()
            return jsonify({'error': 'Segment not found'}), 404
        
        segment.annotator_id = None
        segment.review_status = 'pending'
        segment.text_revised = None
        segment.completed_at = None
        segment.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.close()
        
        return jsonify({'message': 'Segment unassigned', 'segment_id': segment_id}), 200

    except Exception as e:
        logger.error(f"Error unassigning segment: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/projects/<project_id>/assigned', methods=['GET'])
@admin_required
def list_assigned_segments(project_id):
    """Lista segmentos asignados agrupados por usuario"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # Obtener todos los segmentos asignados
        segments = session.query(Segment).filter(
            Segment.project_id == project_id,
            Segment.annotator_id.isnot(None)
        ).order_by(
            Segment.annotator_id.asc(),
            Segment.audio_filename.asc(),
            Segment.segment_index.asc(),
            Segment.start_time.asc(),
            Segment.id.asc()
        ).all()
        
        # Agrupar por usuario
        by_user = {}
        for s in segments:
            uid = s.annotator_id
            if uid not in by_user:
                user = session.query(User).filter_by(id=uid).first()
                by_user[uid] = {
                    'user_id': uid,
                    'username': user.username if user else f'user_{uid}',
                    'segments': []
                }
            by_user[uid]['segments'].append({
                'id': s.id,
                'audio_filename': s.audio_filename,
                'segment_index': s.segment_index,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'text': s.text,
                'status': s.review_status,
                'completed_at': s.completed_at.isoformat() if s.completed_at else None
            })
        
        session.close()
        
        return jsonify({'assigned': list(by_user.values())}), 200
        
    except Exception as e:
        logger.error(f"Error listing assigned segments: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== ESTADÍSTICAS GLOBALES ====================

@admin_bp.route('/users/<int:user_id>/annotations', methods=['GET'])
@admin_required
def get_user_annotations(user_id):
    """Lista todas las anotaciones (segmentos completados) de un usuario"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()

        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'User not found'}), 404

        segments = session.query(Segment).filter(
            Segment.annotator_id == user_id,
            Segment.review_status.in_(['approved', 'corrected', 'discarded'])
        ).order_by(Segment.completed_at.desc()).all()

        result = []
        for s in segments:
            result.append({
                'id': s.id,
                'project_id': s.project_id,
                'segment_index': s.segment_index,
                'text': s.text,
                'text_revised': s.text_revised,
                'review_status': s.review_status,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'completed_at': s.completed_at.isoformat() if s.completed_at else None
            })

        session.close()

        return jsonify({
            'user_id': user_id,
            'username': user.username,
            'annotations': result,
            'total': len(result)
        }), 200

    except Exception as e:
        logger.error(f"Error getting user annotations: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/annotations/export', methods=['GET'])
@admin_required
def export_all_annotations():
    """Exporta anotaciones (incluye descartes y su motivo) de todos los usuarios a Excel"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        db_manager = get_db_manager()
        session = db_manager.get_session()

        segments = session.query(Segment).filter(
            Segment.review_status.in_(['approved', 'corrected', 'discarded'])
        ).order_by(Segment.completed_at.desc()).all()

        # Pre-load annotator usernames
        annotator_ids = set(s.annotator_id for s in segments if s.annotator_id)
        users_map = {}
        if annotator_ids:
            users = session.query(User).filter(User.id.in_(annotator_ids)).all()
            users_map = {u.id: u.username for u in users}

        # Pre-load motivos de descarte por segmento
        discarded_segment_ids = [s.id for s in segments if s.review_status == 'discarded']
        discard_reasons_map = {}
        if discarded_segment_ids:
            discard_reasons = session.query(SegmentDiscardReason).filter(
                SegmentDiscardReason.segment_id.in_(discarded_segment_ids)
            ).all()
            discard_reasons_map = {r.segment_id: r for r in discard_reasons}

        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'transcription_projects')

        wb = Workbook()
        ws = wb.active
        ws.title = 'Anotaciones'

        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        headers = [
            'Ruta del Audio',
            'Timestamp (inicio - fin)',
            'Estado',
            'Segmento Original',
            'Segmento Modificado',
            'Motivo Descarte',
            'Anotador',
            'Fecha de Anotación'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        def fmt_time(seconds):
            m, sec = divmod(seconds, 60)
            h, m = divmod(int(m), 60)
            return f'{h:02d}:{int(m):02d}:{sec:05.2f}'

        status_labels = {
            'approved': 'Aprobada',
            'corrected': 'Corregida',
            'discarded': 'Descartada'
        }
        reason_labels = {
            'not_chilean_spanish': 'No es español chileno',
            'other': 'Otro'
        }

        for row_idx, s in enumerate(segments, 2):
            audio_path = os.path.join(data_dir, s.project_id, s.audio_filename)
            timestamp = f'{fmt_time(s.start_time)} - {fmt_time(s.end_time)}'
            completed = s.completed_at.strftime('%Y-%m-%d %H:%M') if s.completed_at else '\u2014'
            username = users_map.get(s.annotator_id, '\u2014')
            status_label = status_labels.get(s.review_status, s.review_status or '\u2014')

            discard_reason = discard_reasons_map.get(s.id)
            discard_reason_text = '\u2014'
            if s.review_status == 'discarded':
                if discard_reason:
                    if discard_reason.reason_type == 'other':
                        discard_reason_text = discard_reason.reason_note or 'Otro'
                    else:
                        discard_reason_text = reason_labels.get(
                            discard_reason.reason_type,
                            discard_reason.reason_type or '\u2014'
                        )
                else:
                    discard_reason_text = 'Sin motivo registrado'
            elif s.review_status == 'approved':
                discard_reason_text = 'Aprobada'
            elif s.review_status == 'corrected':
                discard_reason_text = 'Corregida'

            row_data = [
                audio_path,
                timestamp,
                status_label,
                s.text,
                s.text_revised or s.text,
                discard_reason_text,
                username,
                completed
            ]

            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.border = thin_border
                cell.alignment = Alignment(vertical='top', wrap_text=True)

        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 14
        ws.column_dimensions['D'].width = 45
        ws.column_dimensions['E'].width = 45
        ws.column_dimensions['F'].width = 36
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 20

        session.close()

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f'anotaciones_todas_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting annotations: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/annotations/<int:segment_id>', methods=['PUT'])
@admin_required
def edit_annotation(segment_id):
    """Permite al admin editar el texto revisado de una anotación"""
    try:
        data = request.get_json()
        text_revised = data.get('text_revised')
        review_status = data.get('review_status')

        if not text_revised:
            return jsonify({'error': 'text_revised required'}), 400

        db_manager = get_db_manager()
        session = db_manager.get_session()

        segment = session.query(Segment).filter_by(id=segment_id).first()
        if not segment:
            session.close()
            return jsonify({'error': 'Segment not found'}), 404

        segment.text_revised = text_revised
        if review_status in ('approved', 'corrected'):
            segment.review_status = review_status
        segment.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.close()

        return jsonify({'message': 'Annotation updated', 'segment_id': segment_id}), 200

    except Exception as e:
        logger.error(f"Error editing annotation: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/annotations/<int:segment_id>/revert', methods=['POST'])
@admin_required
def revert_annotation(segment_id):
    """Revierte una anotación: la vuelve a estado pending sin anotador"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()

        segment = session.query(Segment).filter_by(id=segment_id).first()
        if not segment:
            session.close()
            return jsonify({'error': 'Segment not found'}), 404

        segment.annotator_id = None
        segment.review_status = 'pending'
        segment.text_revised = None
        segment.completed_at = None
        segment.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.close()

        return jsonify({'message': 'Annotation reverted', 'segment_id': segment_id}), 200

    except Exception as e:
        logger.error(f"Error reverting annotation: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/annotations/bulk-revert', methods=['POST'])
@admin_required
def bulk_revert_annotations():
    """Revierte múltiples anotaciones a estado pending"""
    try:
        data = request.get_json()
        segment_ids = data.get('segment_ids', [])

        if not segment_ids:
            return jsonify({'error': 'segment_ids required'}), 400

        db_manager = get_db_manager()
        session = db_manager.get_session()

        reverted = 0
        for sid in segment_ids:
            segment = session.query(Segment).filter_by(id=sid).first()
            if segment:
                segment.annotator_id = None
                segment.review_status = 'pending'
                segment.text_revised = None
                segment.completed_at = None
                segment.updated_at = datetime.now(timezone.utc)
                reverted += 1

        session.commit()
        session.close()

        return jsonify({'message': f'{reverted} annotations reverted', 'reverted': reverted}), 200

    except Exception as e:
        logger.error(f"Error bulk reverting annotations: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_global_stats():
    """Obtiene estadísticas globales del sistema"""
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        total_users = session.query(User).count()
        admin_count = session.query(User).filter_by(role='admin').count()
        annotator_count = total_users - admin_count
        
        total_projects = session.query(TranscriptionProject).count()
        total_segments = session.query(Segment).count()
        completed_segments = session.query(Segment).filter(
            Segment.review_status.in_(['approved', 'corrected'])
        ).count()
        
        session.close()
        
        return jsonify({
            'total_users': total_users,
            'admins': admin_count,
            'annotators': annotator_count,
            'total_projects': total_projects,
            'total_segments': total_segments,
            'completed_segments': completed_segments,
            'completion_percentage': round((completed_segments / total_segments * 100), 2) if total_segments > 0 else 0
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        return jsonify({'error': str(e)}), 500
