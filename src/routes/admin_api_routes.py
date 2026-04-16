"""
Rutas API para administración - Panel administrativo Phase 2
"""
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from datetime import datetime, timezone
from models.database import User, TranscriptionProject, Segment, DatabaseManager
from services.jwt_service import jwt_service
from config import Config
import logging

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
            request.current_user = payload
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
    """Elimina un usuario"""
    try:
        if user_id == request.current_user['id']:
            return jsonify({'error': 'Cannot delete yourself'}), 403
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            session.close()
            return jsonify({'error': 'User not found'}), 404
        
        username = user.username
        session.delete(user)
        session.commit()
        session.close()
        
        return jsonify({'message': f'User {username} deleted'}), 200
        
    except Exception as e:
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
        
        # Contar segmentos asignados y completados
        total_assigned = session.query(Segment).filter_by(annotator_id=user_id).count()
        completed = session.query(Segment).filter_by(
            annotator_id=user_id
        ).filter(Segment.review_status.in_(['approved', 'corrected'])).count()
        
        session.close()
        
        return jsonify({
            'user_id': user_id,
            'username': user.username,
            'total_segments': total_assigned,
            'approved_segments': completed,
            'corrected_segments': completed,
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
        
        total_segments = session.query(Segment).filter_by(project_id=project_id).count()
        pending = session.query(Segment).filter_by(project_id=project_id, review_status='pending').count()
        approved = session.query(Segment).filter_by(project_id=project_id, review_status='approved').count()
        corrected = session.query(Segment).filter_by(project_id=project_id, review_status='corrected').count()
        
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
            'words_completed_percentage': round(((approved + corrected) / total_segments * 100), 2) if total_segments > 0 else 0,
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
                query = query.filter_by(review_status='pending')
            elif status == 'completed':
                query = query.filter(Segment.review_status.in_(['approved', 'corrected']))
        
        segments = query.all()
        session.close()
        
        return jsonify({
            'words': [  # Mantener nombre 'words' por compatibility
                {
                    'id': s.id,
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
        
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        segment = session.query(Segment).filter_by(
            id=segment_id, 
            project_id=project_id
        ).first()
        
        if not segment:
            session.close()
            return jsonify({'error': 'Segment not found'}), 404
        
        segment.annotator_id = annotator_id
        segment.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.close()
        
        return jsonify({'message': 'Segment assigned', 'segment_id': segment_id}), 200
        
    except Exception as e:
        logger.error(f"Error assigning segment: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== ESTADÍSTICAS GLOBALES ====================

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
