#!/usr/bin/env python3
"""
Script para importar transcripciones de archivos JSON a la base de datos
como Segmentos + Palabras, estructura preparada para validación colaborativa.

Uso:
    python import_segments.py <project_id>
    python import_segments.py memoria_1970_1990  # Importa el proyecto específico
    python import_segments.py  # Importa todos los proyectos disponibles en la fuente JSON
"""

import json
import os
import re
import sys
from pathlib import Path

from sqlalchemy import func

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config
from models.database import DatabaseManager, Segment, TranscriptionProject, Word

SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".m4a")


def locate_project_source_dir(base_dir: Path, project_id: str) -> Path:
    """Return project-specific source dir when it exists, else the base dir itself."""
    candidate = base_dir / project_id
    if candidate.exists() and candidate.is_dir():
        return candidate
    return base_dir


def build_audio_index(audio_source_dir: Path) -> dict[str, Path]:
    """Index supported audio files by stem for fast lookup."""
    audio_index: dict[str, Path] = {}
    for audio_file in sorted(audio_source_dir.rglob("*")):
        if (
            not audio_file.is_file()
            or audio_file.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS
        ):
            continue
        audio_index.setdefault(audio_file.stem, audio_file)
    return audio_index


def candidate_audio_stems(json_stem: str) -> list[str]:
    """Generate likely audio stems for a transcript JSON stem."""
    candidates: list[str] = []

    def add(value: str):
        if value and value not in candidates:
            candidates.append(value)

    add(json_stem)

    if json_stem.endswith("_full"):
        add(json_stem[:-5])

    match = re.match(r"^\d+_(.+)$", json_stem)
    if match:
        stripped = match.group(1)
        add(stripped)
        if stripped.endswith("_full"):
            add(stripped[:-5])

    return candidates


def resolve_audio_filename(
    audio_source_dir: Path, audio_index: dict[str, Path], json_file: Path
) -> str:
    """Return the actual audio filename that belongs to a transcript JSON."""
    tried: list[str] = []
    for candidate_stem in candidate_audio_stems(json_file.stem):
        tried.extend(candidate_stem + ext for ext in SUPPORTED_AUDIO_EXTENSIONS)
        audio_path = audio_index.get(candidate_stem)
        if audio_path is not None:
            return str(audio_path.relative_to(audio_source_dir))

    raise FileNotFoundError(
        f"No se encontró audio para {json_file.name}. "
        f'Se probaron nombres base: {", ".join(candidate_audio_stems(json_file.stem))}. '
        f'Archivos esperados: {", ".join(tried)}'
    )


def import_project_segments(
    db_manager, project_id, project_dir, transcript_source_dir, audio_source_dir
):
    """
    Importa todos los segmentos de un proyecto desde JSONs

    Args:
        db_manager: DatabaseManager instance
        project_id: ID del proyecto (ej: 'memoria_1970_1990')
        project_dir: Ruta al directorio del proyecto
    """
    session = db_manager.get_session()

    try:
        project_dir.mkdir(parents=True, exist_ok=True)

        # Verificar/crear el proyecto
        project = session.query(TranscriptionProject).filter_by(id=project_id).first()
        if not project:
            metadata_candidates = [
                Path(project_dir) / "metadata.json",
                Path(transcript_source_dir) / "metadata.json",
            ]
            metadata_path = next(
                (path for path in metadata_candidates if path.exists()), None
            )
            if metadata_path is not None:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    project = TranscriptionProject(
                        id=project_id,
                        name=metadata.get("name", project_id),
                        description=metadata.get("description", ""),
                        status="active",
                    )
            else:
                project = TranscriptionProject(
                    id=project_id,
                    name=project_id.replace("_", " ").title(),
                    status="active",
                )
            session.add(project)
            print(f"✅ Proyecto creado: {project.name}")

        # Procesar archivos JSON desde la fuente configurada
        json_files = list(Path(transcript_source_dir).glob("*.json"))
        json_files = [f for f in json_files if f.name != "metadata.json"]
        audio_index = build_audio_index(Path(audio_source_dir))

        print(f"📁 Encontrados {len(json_files)} archivo(s) JSON")

        total_segments = 0
        total_words = 0
        segments_with_issues = 0

        for json_file in json_files:
            print(f"\n📖 Procesando: {json_file.name}...")

            audio_filename = resolve_audio_filename(
                Path(audio_source_dir), audio_index, json_file
            )
            print(f"   └─ Audio asociado: {audio_filename}")

            with open(json_file) as f:
                data = json.load(f)

            segments_data = data.get("segments", [])
            print(f"   └─ {len(segments_data)} segmentos")

            for segment_idx, segment_data in enumerate(segments_data):
                segment = (
                    session.query(Segment)
                    .filter_by(
                        project_id=project_id,
                        audio_filename=audio_filename,
                        segment_index=segment_idx,
                    )
                    .first()
                )

                if segment is None:
                    segment = Segment(
                        project_id=project_id,
                        audio_filename=audio_filename,
                        segment_index=segment_idx,
                        start_time=segment_data["start"],
                        end_time=segment_data["end"],
                        text=segment_data["text"],
                        speaker=segment_data.get("speaker", "UNKNOWN"),
                        review_status="pending",
                    )
                    session.add(segment)
                    session.flush()  # Para obtener el ID del segment
                else:
                    total_segments += 1
                    continue

                # Procesar palabras y detectar probabilidades bajas
                low_prob_count = 0
                words_data = segment_data.get("words", [])

                for word_idx, word_data in enumerate(words_data):
                    word = Word(
                        segment_id=segment.id,
                        project_id=project_id,
                        audio_filename=audio_filename,
                        word_index=word_idx,
                        word=word_data["word"],
                        speaker=word_data.get("speaker", "UNKNOWN"),
                        probability=word_data["probability"],
                        start_time=word_data["start"],
                        end_time=word_data["end"],
                        alignment_score=word_data.get("alignment_score"),
                    )
                    session.add(word)

                    # Contar palabras con baja probabilidad
                    if word_data["probability"] < 0.95:
                        low_prob_count += 1

                # Si hay palabras con baja probabilidad, marcar segmento
                segment.low_prob_word_count = low_prob_count
                if low_prob_count > 0:
                    segment.review_status = "pending"
                    segments_with_issues += 1
                else:
                    segment.review_status = "approved"  # Sin problemas, ya validado

                total_segments += 1
                total_words += len(words_data)

            session.commit()

        # Actualizar estadísticas del proyecto usando el estado real de la BD.
        project.total_words = (
            session.query(func.count(Word.id)).filter_by(project_id=project_id).scalar()
            or 0
        )
        project.words_to_review = (
            session.query(func.count(Segment.id))
            .filter(
                Segment.project_id == project_id,
                Segment.low_prob_word_count > 0,
            )
            .scalar()
            or 0
        )
        project.words_completed = 0
        session.commit()

        print("\n✅ IMPORTACIÓN COMPLETADA")
        print(f"   └─ Total segmentos procesados: {total_segments}")
        print(f"   └─ Total palabras nuevas: {total_words}")
        print(f"   └─ Segmentos para revisar: {project.words_to_review}")

        return total_segments, total_words, project.words_to_review

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


def main():
    """Función principal"""
    # Cargar configuración
    config = Config.from_env()

    # Rutas configuradas
    project_storage_root = Path(config.get_transcription_projects_path())
    transcript_source_root = Path(config.get_transcript_source_path())
    audio_source_root = Path(config.get_audio_files_path())

    # Determinar qué proyecto(s) importar
    if len(sys.argv) > 1:
        project_ids = [sys.argv[1]]
    else:
        # Importar todos los proyectos disponibles
        project_ids = [d.name for d in transcript_source_root.iterdir() if d.is_dir()]
        if not project_ids:
            raise SystemExit(
                "Debes indicar <project_id> cuando TRANSCRIPT_SOURCE_PATH no contiene subdirectorios por proyecto."
            )

    # Conectar a BD
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_manager.create_tables()

    print("=" * 80)
    print("📥 IMPORTADOR DE SEGMENTOS DE TRANSCRIPCIÓN")
    print("=" * 80)

    grand_total_segments = 0
    grand_total_words = 0

    for project_id in project_ids:
        transcript_source_dir = locate_project_source_dir(
            transcript_source_root, project_id
        )
        audio_source_dir = locate_project_source_dir(audio_source_root, project_id)
        project_dir = project_storage_root / project_id

        if not transcript_source_dir.exists():
            print(
                f"❌ Fuente JSON no encontrada para proyecto {project_id}: {transcript_source_dir}"
            )
            continue

        if not audio_source_dir.exists():
            print(
                f"❌ Fuente audio no encontrada para proyecto {project_id}: {audio_source_dir}"
            )
            continue

        print(f"\n{'=' * 80}")
        print(f"Importando proyecto: {project_id}")
        print(f"{'=' * 80}")

        total_segs, total_words, segs_issue = import_project_segments(
            db_manager,
            project_id,
            project_dir,
            transcript_source_dir,
            audio_source_dir,
        )

        grand_total_segments += total_segs
        grand_total_words += total_words

    print(f"\n{'=' * 80}")
    print("✅ RESUMEN FINAL")
    print(f"{'=' * 80}")
    print(f"Total segmentos importados: {grand_total_segments}")
    print(f"Total palabras importadas: {grand_total_words}")
    print("\nVerificación: python check_db.py")


if __name__ == "__main__":
    main()
