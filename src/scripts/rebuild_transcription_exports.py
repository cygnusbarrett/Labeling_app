"""Reconstruye los archivos TXT/JSON de transcripción corregida por proyecto."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from models.database import DatabaseManager, TranscriptionProject
from services.reconstructed_transcript_service import ReconstructedTranscriptService


def main():
    parser = argparse.ArgumentParser(
        description="Regenera exports reconstruidos por proyecto."
    )
    parser.add_argument("--project-id", help="Proyecto específico a reconstruir")
    args = parser.parse_args()

    config = Config.from_env()
    db_manager = DatabaseManager(config.DATABASE_URL)
    reconstructor = ReconstructedTranscriptService(config)
    session = db_manager.get_session()

    try:
        if args.project_id:
            project_ids = [args.project_id]
        else:
            project_ids = [
                project.id for project in session.query(TranscriptionProject.id).all()
            ]

        if not project_ids:
            print("No hay proyectos para reconstruir.")
            return 0

        for project_id in project_ids:
            result = reconstructor.write_project_exports(session, project_id)
            print(
                f"{project_id}: {result['segment_count']} segmentos -> {result['json_path']} | {result['txt_path']}"
            )

        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
