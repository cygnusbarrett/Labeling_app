"""
Servicio mínimo de base de datos para health checks y utilidades WSGI.
"""
from models.database import DatabaseManager


class DatabaseService:
    """Adaptador simple sobre DatabaseManager."""

    def __init__(self, database_url: str):
        self._db_manager = DatabaseManager(database_url=database_url)

    def get_session(self):
        return self._db_manager.get_session()
