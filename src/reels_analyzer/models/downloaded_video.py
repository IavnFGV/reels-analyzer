from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DownloadedVideo:
    source_url: str
    video_id: str
    title: str
    uploader: str
    upload_date: str | None
    description: str
    webpage_url: str
    file_path: Path | None
    info_json_path: Path | None
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
