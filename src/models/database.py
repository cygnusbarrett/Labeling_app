"""
Modelos de base de datos SQLite para la aplicación de anotación colaborativa
"""
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Index, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash
import os

Base = declarative_base()

class User(Base):
    """Modelo de usuario"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default='annotator')  # 'annotator' o 'admin'
    
    # Relaciones
    words = relationship('Word', back_populates='annotator')
    
    # Índices para mejorar rendimiento
    __table_args__ = (
        Index('idx_user_role', 'role'),
        Index('idx_user_username', 'username'),
    )
    
    def __init__(self, username, password, role='annotator'):
        self.username = username
        self.set_password(password)
        self.role = role
    
    def set_password(self, password):
        """Establece la contraseña hasheada"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convierte el usuario a diccionario"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class DatabaseManager:
    """Manejador de la base de datos"""
    
    def __init__(self, database_url=None):
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///labeling_app.db")
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Crea todas las tablas"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Obtiene una sesión de base de datos"""
        return self.SessionLocal()
    
    def init_admin_user(self, username='admin', password='admin123'):
        """Inicializa el usuario administrador por defecto"""
        session = self.get_session()
        try:
            # Verificar si ya existe un admin
            admin = session.query(User).filter_by(username=username, role='admin').first()
            if not admin:
                admin = User(username=username, password=password, role='admin')
                session.add(admin)
                session.commit()
                print(f"Usuario administrador creado: {username}")
            else:
                print(f"Usuario administrador ya existe: {username}")
        finally:
            session.close()

class TranscriptionProject(Base):
    """Modelo de proyecto de transcripción de audio"""
    __tablename__ = 'transcription_projects'
    
    id = Column(String(100), primary_key=True)  # 'memoria_1970_1990'
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default='active')  # 'active', 'completed', 'archived'
    total_words = Column(Integer, nullable=False, default=0)  # Total de palabras en el proyecto
    words_to_review = Column(Integer, nullable=False, default=0)  # Palabras con probability < 0.95
    words_completed = Column(Integer, nullable=False, default=0)  # Palabras anotadas
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    words = relationship('Word', back_populates='project', cascade='all, delete-orphan')
    
    # Índices
    __table_args__ = (
        Index('idx_project_status', 'status'),
        Index('idx_project_created_at', 'created_at'),
    )
    
    def to_dict(self):
        """Convierte el proyecto a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'total_words': self.total_words,
            'words_to_review': self.words_to_review,
            'words_completed': self.words_completed,
            'progress': round((self.words_completed / self.words_to_review * 100), 2) if self.words_to_review > 0 else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __repr__(self):
        return f'<TranscriptionProject {self.id}>'

class Word(Base):
    """Modelo de palabra en transcripción de audio para validación"""
    __tablename__ = 'words'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), ForeignKey('transcription_projects.id'), nullable=False)
    audio_filename = Column(String(255), nullable=False)  # "D 394 caja 6 cinta 1 Osvaldo Muray lado B-01_short_full.wav"
    word_index = Column(Integer, nullable=False)  # Posición en el JSON (0-based)
    word = Column(String(255), nullable=False)  # Transcripción original
    speaker = Column(String(50), nullable=False)  # "SPEAKER_01", etc
    probability = Column(Float, nullable=False)  # 0.0-1.0
    start_time = Column(Float, nullable=False)  # Segundos
    end_time = Column(Float, nullable=False)  # Segundos
    alignment_score = Column(Float, nullable=True)  # Métrica opcional del JSON
    
    # Anotación
    status = Column(String(20), nullable=False, default='pending')  # 'pending', 'approved', 'corrected'
    annotator_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Quién anotó
    corrected_text = Column(Text, nullable=True)  # Corrección si difiere
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    project = relationship('TranscriptionProject', back_populates='words')
    annotator = relationship('User', back_populates='words')
    
    # Índices para búsqueda eficiente
    __table_args__ = (
        Index('idx_word_project_id', 'project_id'),
        Index('idx_word_status', 'status'),
        Index('idx_word_annotator_id', 'annotator_id'),
        Index('idx_word_project_status', 'project_id', 'status'),
        Index('idx_word_annotator_status', 'annotator_id', 'status'),
        Index('idx_word_probability', 'probability'),
        Index('idx_word_updated_at', 'updated_at'),
    )
    
    def to_dict(self, include_corrected=True):
        """Convierte la palabra a diccionario"""
        result = {
            'id': self.id,
            'project_id': self.project_id,
            'audio_filename': self.audio_filename,
            'word_index': self.word_index,
            'word': self.word,
            'speaker': self.speaker,
            'probability': self.probability,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'alignment_score': self.alignment_score,
            'status': self.status,
            'annotator_id': self.annotator_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        if include_corrected:
            result['corrected_text'] = self.corrected_text
        
        return result
    
    def __repr__(self):
        return f'<Word {self.project_id}:{self.word_index} "{self.word}">'
