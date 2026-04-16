"""
Servicio para gestión de audio - recorte on-demand y validación
"""
from __future__ import annotations
import os
import json
from typing import Tuple, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    import numpy as np

try:
    import librosa
    import soundfile as sf
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("WARNING: librosa/soundfile no disponibles. Audio processing deshabilitado.")


class AudioService:
    """Servicio para manejo de archivos de audio"""
    
    def __init__(self, config=None, base_path: str = None):
        """
        Inicializa el servicio de audio
        
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
        
        self.cache = {}  # Cache de audios cargados en RAM
    
    def get_project_path(self, project_id: str) -> str:
        """Obtiene la ruta del proyecto"""
        return os.path.join(self.base_path, project_id)
    
    def get_audio_path(self, project_id: str, audio_filename: str) -> str:
        """Obtiene la ruta completa del archivo de audio"""
        return os.path.join(self.get_project_path(project_id), audio_filename)
    
    def audio_exists(self, project_id: str, audio_filename: str) -> bool:
        """Verifica si existe el archivo de audio"""
        path = self.get_audio_path(project_id, audio_filename)
        return os.path.exists(path) and os.path.isfile(path)
    
    def load_audio(self, project_id: str, audio_filename: str, sr: int = 16000) -> Tuple[np.ndarray, int]:
        """
        Carga un archivo de audio en memoria
        
        Args:
            project_id: ID del proyecto
            audio_filename: Nombre del archivo de audio
            sr: Sample rate objetivo (16000 Hz = 16 kHz estándar)
        
        Returns:
            (audio_array, sample_rate)
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            RuntimeError: Si librosa no está disponible
        """
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa no está disponible. Instala con: pip install librosa soundfile")
        
        audio_path = self.get_audio_path(project_id, audio_filename)
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")
        
        # Verificar cache
        cache_key = f"{project_id}:{audio_filename}"
        if cache_key in self.cache:
            return self.cache[cache_key], sr
        
        try:
            # Cargar audio con librosa
            print(f"Cargando audio: {audio_path}")
            y, sr_original = librosa.load(audio_path, sr=sr)
            self.cache[cache_key] = y
            print(f"Audio cargado: {len(y)} muestras a {sr} Hz ({len(y)/sr:.2f}s)")
            return y, sr
        except Exception as e:
            raise RuntimeError(f"Error al cargar audio: {str(e)}")
    
    def get_audio_segment(
        self, 
        project_id: str, 
        audio_filename: str, 
        start_time: float, 
        end_time: float,
        margin_seconds: float = 0.2,
        sr: int = 16000
    ) -> Tuple[np.ndarray, int]:
        """
        Extrae un segmento de audio basado en timestamps
        
        Args:
            project_id: ID del proyecto
            audio_filename: Nombre del archivo de audio
            start_time: Tiempo inicio en segundos
            end_time: Tiempo fin en segundos
            margin_seconds: Margen a agregar antes/después (0.2s)
            sr: Sample rate
        
        Returns:
            (segmento_audio, sample_rate)
        
        Raises:
            ValueError: Si los timestamps son inválidos
            RuntimeError: Si hay error en el procesamiento
        """
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa no está disponible")
        
        if start_time < 0 or end_time <= start_time:
            raise ValueError(f"Timestamps inválidos: start={start_time}, end={end_time}")
        
        try:
            # Cargar audio completo
            y, sr = self.load_audio(project_id, audio_filename, sr)
            
            # Calcular índices en muestras
            start_sample = max(0, int((start_time - margin_seconds) * sr))
            end_sample = min(len(y), int((end_time + margin_seconds) * sr))
            
            # Validar rangos
            if start_sample >= len(y):
                raise ValueError(f"start_time fuera de rango: {start_time}s (audio: {len(y)/sr:.2f}s)")
            
            # Extraer segmento
            segment = y[start_sample:end_sample]
            
            if len(segment) == 0:
                raise ValueError(f"Segmento vacío: {start_time}-{end_time}s")
            
            return segment, sr
        
        except Exception as e:
            raise RuntimeError(f"Error al extraer segmento: {str(e)}")
    
    def get_audio_segment_as_wav(
        self,
        project_id: str,
        audio_filename: str,
        start_time: float,
        end_time: float,
        margin_seconds: float = 0.2,
        sr: int = 16000
    ) -> bytes:
        """
        Retorna un segmento de audio como bytes WAV
        
        Args:
            (mismos parámetros que get_audio_segment)
        
        Returns:
            Bytes del archivo WAV
        """
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa no está disponible")
        
        try:
            segment, sr = self.get_audio_segment(project_id, audio_filename, start_time, end_time, margin_seconds, sr)
            
            # Convertir a WAV en memoria usando soundfile
            import io
            with io.BytesIO() as buffer:
                sf.write(buffer, segment, sr, format='WAV')
                return buffer.getvalue()
        
        except Exception as e:
            raise RuntimeError(f"Error al convertir audio a WAV: {str(e)}")
    
    def get_audio_duration(self, project_id: str, audio_filename: str) -> float:
        """
        Obtiene la duración del audio en segundos
        
        Returns:
            Duración en segundos
        """
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa no está disponible")
        
        try:
            y, sr = self.load_audio(project_id, audio_filename)
            duration = len(y) / sr
            return duration
        except Exception as e:
            raise RuntimeError(f"Error al obtener duración: {str(e)}")
    
    def clear_cache(self, project_id: str = None, audio_filename: str = None):
        """
        Limpia la caché de audios
        
        Args:
            project_id: Si se especifica, limpia solo este proyecto
            audio_filename: Si se especifica, limpia solo este archivo
        """
        if project_id is None:
            self.cache.clear()
            print("Caché de audio limpiada completamente")
        else:
            cache_key = f"{project_id}:{audio_filename}" if audio_filename else None
            if cache_key and cache_key in self.cache:
                del self.cache[cache_key]
                print(f"Caché limpiada para: {cache_key}")
            elif not audio_filename:
                # Limpiar todos los archivos del proyecto
                keys_to_delete = [k for k in self.cache.keys() if k.startswith(f"{project_id}:")]
                for k in keys_to_delete:
                    del self.cache[k]
                print(f"Caché limpiada para proyecto: {project_id}")


# Instancia global del servicio
audio_service = AudioService()
