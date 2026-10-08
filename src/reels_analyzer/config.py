from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FeatureFlags:
    download_media: bool = True
    use_existing_videos: bool = False
    analyze_video: bool = False
    transcribe_audio: bool = False
    classify_text: bool = False


@dataclass(slots=True)
class ProjectLayout:
    root: Path
    videos_dir: Path
    reports_dir: Path
    cache_dir: Path
    transcripts_dir: Path
    archive_path: Path
    links_snapshot_path: Path
    results_csv_path: Path
    ai_reviews_csv_path: Path

    @classmethod
    def from_channel(cls, base_dir: Path, channel_name: str) -> "ProjectLayout":
        slug = _slugify(channel_name)
        root = base_dir / slug
        return cls(
            root=root,
            videos_dir=root / "videos",
            reports_dir=root / "reports",
            cache_dir=root / "cache",
            transcripts_dir=root / "reports" / "transcripts",
            archive_path=root / "downloaded.txt",
            links_snapshot_path=root / "inputs" / "links.txt",
            results_csv_path=root / "reports" / "videos.csv",
            ai_reviews_csv_path=root / "reports" / "ai_reviews.csv",
        )

    def ensure_directories(self) -> None:
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.links_snapshot_path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class RuntimeConfig:
    channel_name: str
    links_file: Path
    project: ProjectLayout
    features: FeatureFlags
    whisper_model: str = "base"
    ollama_model: str = "qwen2.5:3b"
    ollama_base_url: str = "http://localhost:11434/api/chat"


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "channel"
