from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from reels_analyzer.config import FeatureFlags, ProjectLayout
from reels_analyzer.models import SourceVideoLink

MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mp3", ".m4a", ".wav"}


@dataclass(slots=True)
class ProjectStateIndex:
    metadata_by_id: dict[str, Path]
    media_by_id: dict[str, Path]
    transcript_by_id: dict[str, Path]
    ai_review_by_key: dict[str, bool]
    ai_review_rows_by_key: dict[str, dict[str, str]]

    @classmethod
    def scan(
        cls,
        project: ProjectLayout,
        whisper_model: str,
        ollama_model: str,
    ) -> "ProjectStateIndex":
        metadata_by_id: dict[str, Path] = {}
        media_by_id: dict[str, Path] = {}
        transcript_by_id: dict[str, Path] = {}
        ai_review_by_key: dict[str, bool] = {}
        ai_review_rows_by_key: dict[str, dict[str, str]] = {}

        if project.videos_dir.exists():
            for candidate in project.videos_dir.iterdir():
                if not candidate.is_file():
                    continue
                video_id = _extract_video_id(candidate.name)
                if not video_id:
                    continue
                if candidate.name.endswith(".info.json"):
                    metadata_by_id.setdefault(video_id, candidate)
                    continue
                if candidate.suffix.lower() in MEDIA_EXTENSIONS:
                    media_by_id.setdefault(video_id, candidate)

        transcript_suffix = f"__{_slug_for_filename(whisper_model)}.txt"
        if project.transcripts_dir.exists():
            for candidate in project.transcripts_dir.iterdir():
                if not candidate.is_file():
                    continue
                if not candidate.name.endswith(transcript_suffix):
                    continue
                video_id = candidate.name[: -len(transcript_suffix)]
                if video_id:
                    transcript_by_id[video_id] = candidate

        if project.ai_reviews_csv_path.exists():
            with project.ai_reviews_csv_path.open("r", newline="", encoding="utf-8") as csv_file:
                for row in csv.DictReader(csv_file):
                    video_id = (row.get("video_id") or "").strip()
                    model = (row.get("ollama_model") or "").strip()
                    if not video_id or not model:
                        continue
                    key = f"{video_id}|{model}"
                    ai_review_by_key[key] = True
                    ai_review_rows_by_key[key] = dict(row)

        return cls(
            metadata_by_id=metadata_by_id,
            media_by_id=media_by_id,
            transcript_by_id=transcript_by_id,
            ai_review_by_key=ai_review_by_key,
            ai_review_rows_by_key=ai_review_rows_by_key,
        )


@dataclass(slots=True)
class LinkActionPlan:
    total_links: int
    links_with_metadata: list[SourceVideoLink]
    links_missing_metadata: list[SourceVideoLink]
    links_with_media: list[SourceVideoLink]
    links_missing_media: list[SourceVideoLink]
    transcript_ready_count: int
    ai_review_ready_count: int
    transcript_missing_count: int
    ai_review_missing_count: int

    def log_lines(self, features: FeatureFlags) -> list[str]:
        lines = [
            (
                "Project state: %s links, metadata ready %s, media ready %s, "
                "transcripts ready %s, ai reviews ready %s."
            )
            % (
                self.total_links,
                len(self.links_with_metadata),
                len(self.links_with_media),
                self.transcript_ready_count,
                self.ai_review_ready_count,
            )
        ]

        actions: list[str] = []
        if features.download_media:
            actions.append(f"download media for {len(self.links_missing_media)} link(s)")
            if self.links_with_media:
                actions.append(f"reuse existing media for {len(self.links_with_media)} link(s)")
        else:
            actions.append(f"fetch metadata for {len(self.links_missing_metadata)} link(s)")
            if self.links_with_metadata:
                actions.append(
                    f"reuse existing metadata for {len(self.links_with_metadata)} link(s)"
                )

        if features.transcribe_audio:
            actions.append(
                "transcripts: restore %s, generate %s"
                % (self.transcript_ready_count, self.transcript_missing_count)
            )
        if features.classify_text:
            actions.append(
                "ai reviews: restore %s, classify %s"
                % (self.ai_review_ready_count, self.ai_review_missing_count)
            )

        lines.append("Planned actions: " + "; ".join(actions) + ".")
        return lines


def build_link_action_plan(
    links: list[SourceVideoLink],
    state: ProjectStateIndex,
    features: FeatureFlags,
    ollama_model: str,
) -> LinkActionPlan:
    links_with_metadata: list[SourceVideoLink] = []
    links_missing_metadata: list[SourceVideoLink] = []
    links_with_media: list[SourceVideoLink] = []
    links_missing_media: list[SourceVideoLink] = []
    transcript_ready_count = 0
    ai_review_ready_count = 0
    transcript_missing_count = 0
    ai_review_missing_count = 0

    for link in links:
        video_id = _extract_video_id(link.url)
        has_metadata = bool(video_id and video_id in state.metadata_by_id)
        has_media = bool(video_id and video_id in state.media_by_id)
        has_transcript = bool(video_id and video_id in state.transcript_by_id)
        has_ai_review = bool(video_id and f"{video_id}|{ollama_model}" in state.ai_review_by_key)

        if has_metadata:
            links_with_metadata.append(link)
        else:
            links_missing_metadata.append(link)

        if has_media:
            links_with_media.append(link)
        else:
            links_missing_media.append(link)

        if has_transcript:
            transcript_ready_count += 1
        elif features.transcribe_audio:
            transcript_missing_count += 1
        if has_ai_review:
            ai_review_ready_count += 1
        elif features.classify_text:
            ai_review_missing_count += 1

    return LinkActionPlan(
        total_links=len(links),
        links_with_metadata=links_with_metadata,
        links_missing_metadata=links_missing_metadata,
        links_with_media=links_with_media,
        links_missing_media=links_missing_media,
        transcript_ready_count=transcript_ready_count,
        ai_review_ready_count=ai_review_ready_count,
        transcript_missing_count=transcript_missing_count,
        ai_review_missing_count=ai_review_missing_count,
    )


def _extract_video_id(value: str) -> str:
    matches = re.findall(r"(\d{18,20})", value or "")
    if not matches:
        return ""
    return matches[0]


def _slug_for_filename(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "model"
