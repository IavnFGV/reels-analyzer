from __future__ import annotations

import csv
from pathlib import Path
from tempfile import NamedTemporaryFile

from reels_analyzer.models import VideoRecord


class CsvReportWriter:
    FIELDNAMES = [
        "source_url",
        "video_id",
        "title",
        "uploader",
        "upload_date",
        "webpage_url",
        "file_path",
        "info_json_path",
        "duration_sec",
        "width",
        "height",
        "fps",
        "view_count",
        "like_count",
        "comment_count",
        "audio_file_path",
        "transcription_model",
        "classification_model",
        "scene_count",
        "avg_scene_length_sec",
        "pace_label",
        "scene_skipped_reason",
        "transcript_file_path",
        "first_phrase",
        "word_count",
        "words_per_second",
        "transcription_skipped_reason",
        "content_type",
        "hook_type",
        "tone",
        "summary",
        "strengths",
        "weaknesses",
        "classification_skipped_reason",
        "performance_cohort",
        "performance_baseline_view_count",
        "performance_score",
        "performance_bucket",
        "hook_subject",
        "hook_format",
        "hook_emotion",
        "hook_specificity",
        "hook_strength_score",
        "topic_cluster",
        "insight_tags",
    ]
    AI_FIELDNAMES = [
        "video_id",
        "source_url",
        "file_path",
        "transcript_file_path",
        "transcription_model",
        "ollama_model",
        "content_type",
        "hook_type",
        "tone",
        "summary",
        "strengths",
        "weaknesses",
        "classification_skipped_reason",
    ]

    def write(self, records: list[VideoRecord], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        existing_rows = self.load_rows(output_path)
        merged: dict[str, dict[str, str]] = {self._row_key(row): row for row in existing_rows}

        for record in records:
            row = record.to_csv_row()
            merged[self._row_key(row)] = row

        self._write_atomic(
            output_path=output_path,
            fieldnames=self.FIELDNAMES,
            rows=[
                {field: row.get(field, "") for field in self.FIELDNAMES}
                for row in merged.values()
            ],
        )

    def write_rows(self, rows: list[dict[str, str]], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_atomic(
            output_path=output_path,
            fieldnames=self.FIELDNAMES,
            rows=[{field: row.get(field, "") for field in self.FIELDNAMES} for row in rows],
        )

    def write_ai_reviews(self, records: list[VideoRecord], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        existing_rows = self._load_generic_rows(output_path)
        merged: dict[str, dict[str, str]] = {self._ai_row_key(row): row for row in existing_rows}

        for record in records:
            row = record.to_ai_review_row()
            if not row.get("ollama_model"):
                continue
            merged[self._ai_row_key(row)] = row

        self._write_atomic(
            output_path=output_path,
            fieldnames=self.AI_FIELDNAMES,
            rows=[
                {field: row.get(field, "") for field in self.AI_FIELDNAMES}
                for row in merged.values()
            ],
        )

    def load_rows(self, output_path: Path) -> list[dict[str, str]]:
        return self._load_generic_rows(output_path)

    def _load_generic_rows(self, output_path: Path) -> list[dict[str, str]]:
        if not output_path.exists():
            return []
        with output_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            return [dict(row) for row in reader]

    def load_index(self, output_path: Path) -> dict[str, dict[str, str]]:
        return {self._row_key(row): row for row in self.load_rows(output_path)}

    def _row_key(self, row: dict[str, str]) -> str:
        video_id = (row.get("video_id") or "").strip()
        if video_id:
            return f"video_id:{video_id}"
        source_url = (row.get("source_url") or "").strip()
        return f"source_url:{source_url}"

    def _ai_row_key(self, row: dict[str, str]) -> str:
        video_id = (row.get("video_id") or "").strip()
        model = (row.get("ollama_model") or "").strip()
        if video_id:
            return f"video_id:{video_id}|model:{model}"
        source_url = (row.get("source_url") or "").strip()
        return f"source_url:{source_url}|model:{model}"

    def _write_atomic(
        self,
        output_path: Path,
        fieldnames: list[str],
        rows: list[dict[str, str]],
    ) -> None:
        with NamedTemporaryFile(
            "w",
            newline="",
            encoding="utf-8",
            dir=output_path.parent,
            delete=False,
        ) as tmp_file:
            writer = csv.DictWriter(tmp_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            temp_path = Path(tmp_file.name)

        temp_path.replace(output_path)
