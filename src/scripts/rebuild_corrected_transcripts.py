#!/usr/bin/env python3
"""Rebuild corrected transcription export files for one or more projects."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from models.database import DatabaseManager, TranscriptionProject
from services.transcript_export_service import export_project_transcript


def main() -> int:
    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    session = db_manager.get_session()

    try:
        if len(sys.argv) > 1:
            project_ids = sys.argv[1:]
        else:
            project_ids = [project.id for project in session.query(TranscriptionProject).order_by(TranscriptionProject.id.asc()).all()]

        if not project_ids:
            print('No hay proyectos para exportar')
            return 0

        for project_id in project_ids:
            paths = export_project_transcript(session, project_id, config=config)
            print(f'{project_id}:')
            print(f'  JSON: {paths["json_path"]}')
            print(f'  TXT:  {paths["txt_path"]}')
        return 0
    finally:
        session.close()


if __name__ == '__main__':
    raise SystemExit(main())
