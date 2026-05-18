"""Generación de transcripción reconstruida por proyecto."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models.database import Segment


class ReconstructedTranscriptService:
    """Reconstruye y exporta la transcripción final de un proyecto."""

    JSON_FILENAME = "reconstructed_transcript.json"
    TXT_FILENAME = "reconstructed_transcript.txt"

    def __init__(self, config):
        self.config = config
        self.base_path = Path(config.get_transcription_projects_path())

    def get_project_dir(self, project_id: str) -> Path:
        return self.base_path / project_id

    def get_output_paths(self, project_id: str) -> dict:
        project_dir = self.get_project_dir(project_id)
        return {
            "json": project_dir / self.JSON_FILENAME,
            "txt": project_dir / self.TXT_FILENAME,
        }

    def build_payload(self, session, project_id: str) -> dict:
        segments = (
            session.query(Segment)
            .filter_by(project_id=project_id)
            .order_by(Segment.audio_filename.asc(), Segment.segment_index.asc())
            .all()
        )

        grouped_files = {}
        for segment in segments:
            final_text = (segment.text_revised or segment.text or "").strip()
            file_entry = grouped_files.setdefault(
                segment.audio_filename,
                {
                    "audio_filename": segment.audio_filename,
                    "segments": [],
                },
            )
            file_entry["segments"].append(
                {
                    "id": segment.id,
                    "segment_index": segment.segment_index,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "review_status": segment.review_status,
                    "decision_type": segment.decision_type,
                    "text_original": segment.text,
                    "text_revised": segment.text_revised,
                    "text_final": final_text,
                }
            )

        files = []
        all_text_lines = []
        for audio_filename, file_entry in grouped_files.items():
            reconstructed_text = "\n".join(
                segment["text_final"]
                for segment in file_entry["segments"]
                if segment["text_final"]
            ).strip()
            file_entry["reconstructed_text"] = reconstructed_text
            files.append(file_entry)
            if reconstructed_text:
                all_text_lines.append(f"[{audio_filename}]")
                all_text_lines.append(reconstructed_text)
                all_text_lines.append("")

        return {
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "segment_count": len(segments),
            "files": files,
            "reconstructed_text": "\n".join(all_text_lines).strip(),
        }

    def write_project_exports(self, session, project_id: str) -> dict:
        payload = self.build_payload(session, project_id)
        output_paths = self.get_output_paths(project_id)
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        output_paths["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        output_paths["txt"].write_text(
            payload["reconstructed_text"]
            + ("\n" if payload["reconstructed_text"] else ""),
            encoding="utf-8",
        )

        return {
            "json_path": str(output_paths["json"]),
            "txt_path": str(output_paths["txt"]),
            "segment_count": payload["segment_count"],
        }
