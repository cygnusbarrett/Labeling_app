"""Helpers to rebuild corrected transcription files from reviewed segments."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from models.database import Segment
from config import Config


def _segment_sort_key(segment: Segment):
    return (
        segment.audio_filename or '',
        segment.segment_index if segment.segment_index is not None else 0,
        segment.start_time if segment.start_time is not None else 0,
        segment.id if segment.id is not None else 0,
    )


def _final_text(segment: Segment) -> str:
    return (segment.text_revised or segment.text or '').strip()


def build_project_transcript_payload(session, project_id: str) -> dict:
    segments = (
        session.query(Segment)
        .filter(Segment.project_id == project_id)
        .order_by(
            Segment.audio_filename.asc(),
            Segment.segment_index.asc(),
            Segment.start_time.asc(),
            Segment.id.asc(),
        )
        .all()
    )

    grouped_segments = defaultdict(list)
    for segment in segments:
        final_text = _final_text(segment)
        segment_payload = {
            'segment_id': segment.id,
            'segment_index': segment.segment_index,
            'audio_filename': segment.audio_filename,
            'start_time': segment.start_time,
            'end_time': segment.end_time,
            'review_status': segment.review_status,
            'decision_type': segment.decision_type,
            'annotator_id': segment.annotator_id,
            'original_text': segment.text,
            'final_text': final_text,
            'completed_at': segment.completed_at.isoformat() if segment.completed_at else None,
        }
        grouped_segments[segment.audio_filename].append(segment_payload)

    audio_outputs = {}
    combined_sections = []

    for audio_filename in sorted(grouped_segments):
        ordered_segments = sorted(
            grouped_segments[audio_filename],
            key=lambda item: (
                item['segment_index'] if item['segment_index'] is not None else 0,
                item['start_time'] if item['start_time'] is not None else 0,
                item['segment_id'] if item['segment_id'] is not None else 0,
            ),
        )
        accepted_texts = [
            item['final_text']
            for item in ordered_segments
            if item['review_status'] in ('approved', 'corrected') and item['final_text']
        ]
        audio_transcription = ' '.join(accepted_texts).strip()
        audio_outputs[audio_filename] = {
            'transcription': audio_transcription,
            'segments': ordered_segments,
        }
        if audio_transcription:
            combined_sections.append(f'## {audio_filename}\n{audio_transcription}')

    return {
        'project_id': project_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'audio_files': audio_outputs,
        'full_transcription': '\n\n'.join(combined_sections).strip(),
    }


def export_project_transcript(session, project_id: str, config: Config | None = None) -> dict:
    config = config or Config.from_env()
    project_dir = Path(config.get_transcription_projects_path()) / project_id
    export_dir = project_dir / 'exports'
    export_dir.mkdir(parents=True, exist_ok=True)

    payload = build_project_transcript_payload(session, project_id)
    json_path = export_dir / 'corrected_transcription.json'
    txt_path = export_dir / 'corrected_transcription.txt'

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    txt_sections = [
        f'Proyecto: {project_id}',
        f'Generado: {payload["generated_at"]}',
        '',
        payload['full_transcription'] or 'No hay segmentos aprobados o corregidos para reconstruir la transcripcion.',
        '',
    ]
    txt_path.write_text('\n'.join(txt_sections), encoding='utf-8')

    return {
        'json_path': str(json_path),
        'txt_path': str(txt_path),
    }
