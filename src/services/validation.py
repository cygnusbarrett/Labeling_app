"""
Esquemas de validación con Marshmallow
Valida input en todos los endpoints POST/PUT antes de procesar
"""
from marshmallow import Schema, fields, validate, validates, ValidationError
import logging

logger = logging.getLogger(__name__)

class LoginSchema(Schema):
    """Esquema para validación de login"""
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=100),
        error_messages={'required': 'username es requerido'}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=256),
        error_messages={'required': 'password es requerido'}
    )


class CorrectionSchema(Schema):
    """Esquema para validación de correcciones de segmentos"""
    review_status = fields.Str(
        required=True,
        validate=validate.OneOf(['approved', 'corrected', 'discarded', 'pending']),
        error_messages={
            'required': 'review_status es requerido',
            'validator_failed': 'review_status debe ser "approved", "corrected", "discarded" o "pending"'
        }
    )
    status = fields.Str(
        required=False,
        validate=validate.OneOf(['approved', 'corrected', 'discarded', 'pending']),
        error_messages={'validator_failed': 'status inválido (backward compat)'}
    )
    text_revised = fields.Str(
        required=False,
        validate=validate.Length(min=1, max=5000),
        allow_none=True,
        error_messages={'validator_failed': 'text_revised debe tener entre 1 y 5000 caracteres'}
    )
    corrected_text = fields.Str(
        required=False,
        validate=validate.Length(min=1, max=5000),
        allow_none=True,
        error_messages={'validator_failed': 'corrected_text debe tener entre 1 y 5000 caracteres'}
    )
    discard_reason_type = fields.Str(
        required=False,
        validate=validate.OneOf(['not_chilean_spanish', 'other']),
        allow_none=True,
        error_messages={'validator_failed': 'discard_reason_type inválido'}
    )
    discard_reason_note = fields.Str(
        required=False,
        validate=validate.Length(min=1, max=1000),
        allow_none=True,
        error_messages={'validator_failed': 'discard_reason_note debe tener entre 1 y 1000 caracteres'}
    )
    
    @validates('text_revised')
    def validate_text_revised(self, value):
        """Validaciones adicionales para text_revised"""
        if value:
            # No permitir solo espacios
            if not value.strip():
                raise ValidationError("text_revised no puede estar vacío o solo espacios")
            
            # Limpieza básica
            if len(value) < 3:
                raise ValidationError("text_revised debe tener al menos 3 caracteres")


class CreateUserSchema(Schema):
    """Esquema para crear nuevos usuarios"""
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=100),
        error_messages={'required': 'username es requerido'}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=256),
        error_messages={'required': 'password es requerido (mín 8 caracteres)'}
    )
    role = fields.Str(
        required=False,
        validate=validate.OneOf(['admin', 'annotator']),
        missing='annotator',
        error_messages={'validator_failed': 'role debe ser "admin" o "annotator"'}
    )
    
    @validates('password')
    def validate_password_strength(self, value):
        """Valida que la contraseña sea fuerte"""
        if len(value) < 8:
            raise ValidationError("La contraseña debe tener al mínimo 8 caracteres")
        
        # Debe contener datos y letras (básico)
        has_digit = any(c.isdigit() for c in value)
        has_letter = any(c.isalpha() for c in value)
        
        if not (has_digit and has_letter):
            raise ValidationError("La contraseña debe contener letras y números")


class ProjectFilterSchema(Schema):
    """Esquema para filtrar proyectos (query parameters)"""
    status = fields.Str(
        required=False,
        validate=validate.OneOf(['active', 'completed', 'archived']),
        default='active'
    )
    limit = fields.Int(
        required=False,
        validate=validate.Range(min=1, max=100),
        default=20
    )
    offset = fields.Int(
        required=False,
        validate=validate.Range(min=0),
        default=0
    )


def validate_request_data(schema_class):
    """
    Decorador para validar datos de request con un schema
    Uso: @validate_request_data(CorrectionSchema)
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            schema = schema_class()
            try:
                # Obtener JSON del request
                data = request.get_json() or {}
                
                # Cargar y validar
                validated_data = schema.load(data)
                
                # Pasar datos validados al kwargs
                kwargs['validated_data'] = validated_data
                
                return f(*args, **kwargs)
                
            except ValidationError as err:
                logger.warning(f"Validation error: {err.messages}")
                from flask import jsonify
                return jsonify({'error': 'Validation error', 'details': err.messages}), 400
            except Exception as e:
                logger.error(f"Error durante validación: {e}")
                from flask import jsonify
                return jsonify({'error': 'Error processing request'}), 400
        
        wrapper.__name__ = f.__name__
        return wrapper
    
    return decorator
