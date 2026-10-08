from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from reels_analyzer.dependencies import require_python_package
from reels_analyzer.models import DownloadedVideo, SourceVideoLink

logger = logging.getLogger(__name__)


class YtDlpDownloader:
    def download(
        self,
        links: list[SourceVideoLink],
        output_dir: Path,
        archive_path: Path,
    ) -> list[DownloadedVideo]:
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        return self._collect_records(
            links=links,
            output_dir=output_dir,
            download=True,
            archive_path=archive_path,
        )

    def inspect_only(
        self,
        links: list[SourceVideoLink],
        output_dir: Path,
    ) -> list[DownloadedVideo]:
        output_dir.mkdir(parents=True, exist_ok=True)
        return self._collect_records(
            links=links,
            output_dir=output_dir,
            download=False,
            archive_path=None,
        )

    def _collect_records(
        self,
        links: list[SourceVideoLink],
        output_dir: Path,
        download: bool,
        archive_path: Path | None,
    ) -> list[DownloadedVideo]:
        require_python_package("yt_dlp", "download-media")

        import yt_dlp
        from yt_dlp.utils import DownloadError

        records: list[DownloadedVideo] = []
        ydl_opts = self._build_ydl_options(
            output_dir=output_dir,
            download=download,
            archive_path=archive_path,
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            total = len(links)
            skipped = 0
            action = "Downloading media" if download else "Fetching metadata"
            for index, link in enumerate(links, start=1):
                logger.info("[%s/%s] %s for %s", index, total, action, _label_for_link(link.url))
                try:
                    info = ydl.extract_info(link.url, download=download)
                except DownloadError as error:
                    skipped += 1
                    logger.warning(
                        "[%s/%s] Skipped %s: %s",
                        index,
                        total,
                        _label_for_link(link.url),
                        error,
                    )
                    continue
                except Exception as error:
                    skipped += 1
                    logger.warning(
                        "[%s/%s] Unexpected downloader error for %s: %s",
                        index,
                        total,
                        _label_for_link(link.url),
                        error,
                    )
                    continue
                if not download:
                    self._save_info_json(output_dir=output_dir, info=info, ydl=ydl)
                records.append(
                    self._build_record(output_dir=output_dir, info=info, source_url=link.url)
                )
            if skipped:
                logger.warning("Downloader skipped %s link(s) out of %s.", skipped, total)

        return records

    def _build_ydl_options(
        self,
        output_dir: Path,
        download: bool,
        archive_path: Path | None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "outtmpl": str(output_dir / "%(uploader)s_%(upload_date)s_%(id)s.%(ext)s"),
            "restrictfilenames": True,
            "windowsfilenames": True,
            "writeinfojson": True,
            "noplaylist": True,
            "quiet": True,
        }
        if download:
            options["merge_output_format"] = "mp4"
            if archive_path is not None:
                options["download_archive"] = str(archive_path)
        else:
            options["skip_download"] = True
        return options

    def _save_info_json(
        self,
        output_dir: Path,
        info: dict[str, Any],
        ydl: Any,
    ) -> None:
        try:
            prepared_path = Path(ydl.prepare_filename(info))
        except Exception:
            fallback_path = _fallback_file_path(output_dir, info)
            if fallback_path is None:
                return
            prepared_path = fallback_path

        info_path = prepared_path.with_suffix(".info.json")
        info_path.parent.mkdir(parents=True, exist_ok=True)
        with info_path.open("w", encoding="utf-8") as file:
            json.dump(info, file, ensure_ascii=False)

    def load_existing(self, output_dir: Path) -> list[DownloadedVideo]:
        return self.load_existing_for_ids(output_dir=output_dir, video_ids=None, include_info_only=False)

    def load_existing_for_ids(
        self,
        output_dir: Path,
        video_ids: set[str] | None,
        include_info_only: bool,
    ) -> list[DownloadedVideo]:
        if not output_dir.exists():
            return []

        loaded = self._load_existing_records(output_dir=output_dir, include_info_only=include_info_only)
        if video_ids is None:
            return list(loaded.values())
        return [record for video_id, record in loaded.items() if video_id in video_ids]

    def _load_existing_records(
        self,
        output_dir: Path,
        include_info_only: bool,
    ) -> dict[str, DownloadedVideo]:
        loaded: dict[str, DownloadedVideo] = {}
        files = sorted(output_dir.iterdir())

        for file_path in files:
            if not file_path.is_file():
                continue
            if not _is_media_file(file_path):
                continue

            info = _read_info_json(file_path)
            record = self._build_record(
                output_dir=output_dir,
                info=info,
                source_url=_source_url(info),
            )
            if record.video_id:
                loaded[record.video_id] = record

        if not include_info_only:
            return loaded

        for file_path in files:
            if not file_path.is_file():
                continue
            if not _is_info_json_file(file_path):
                continue

            info = _read_info_file(file_path)
            video_id = str(info.get("id", "")).strip()
            if not video_id or video_id in loaded:
                continue
            record = self._build_record(
                output_dir=output_dir,
                info=info,
                source_url=_source_url(info),
            )
            loaded[video_id] = record

        return loaded

    def _build_record(
        self,
        output_dir: Path | None,
        info: dict[str, Any],
        source_url: str,
    ) -> DownloadedVideo:
        file_path = _extract_file_path(info)
        if file_path is None and output_dir is not None:
            file_path = _fallback_file_path(output_dir, info)

        info_json_path = None
        if file_path is not None:
            info_json_path = _find_info_json_path(file_path)
        if info_json_path is None and output_dir is not None:
            info_json_path = _fallback_info_json_path(output_dir, info)

        return DownloadedVideo(
            source_url=source_url,
            video_id=str(info.get("id", "")),
            title=str(info.get("title", "")),
            uploader=str(info.get("uploader", "")),
            upload_date=_normalize_optional(info.get("upload_date")),
            description=str(info.get("description", "") or ""),
            webpage_url=str(info.get("webpage_url", source_url)),
            file_path=file_path,
            info_json_path=info_json_path,
            duration_sec=_safe_float(info.get("duration")),
            width=_safe_int(info.get("width")),
            height=_safe_int(info.get("height")),
            fps=_safe_float(info.get("fps")),
            view_count=_safe_int(info.get("view_count")),
            like_count=_safe_int(info.get("like_count")),
            comment_count=_safe_int(info.get("comment_count")),
        )


def _extract_file_path(info: dict[str, Any]) -> Path | None:
    filepath = info.get("filepath") or info.get("_filename")
    if isinstance(filepath, str):
        return Path(filepath)

    requested_downloads = info.get("requested_downloads")
    if isinstance(requested_downloads, list):
        for item in requested_downloads:
            if isinstance(item, dict) and isinstance(item.get("filepath"), str):
                return Path(item["filepath"])

    return None


def _is_video_file(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def _is_media_file(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mp3", ".m4a", ".wav"}


def _is_info_json_file(path: Path) -> bool:
    return path.is_file() and path.name.endswith(".info.json")


def _read_info_json(video_path: Path) -> dict[str, Any]:
    info_path = _find_info_json_path(video_path)
    if info_path is None:
        return {"filepath": str(video_path)}

    try:
        with info_path.open("r", encoding="utf-8") as file:
            parsed = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"filepath": str(video_path)}

    if isinstance(parsed, dict):
        parsed.setdefault("filepath", str(video_path))
        return parsed
    return {"filepath": str(video_path)}


def _read_info_file(info_path: Path) -> dict[str, Any]:
    try:
        with info_path.open("r", encoding="utf-8") as file:
            parsed = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _label_for_link(url: str) -> str:
    matches = re.findall(r"(\d{18,20})", url or "")
    if matches:
        return matches[0]
    return url


def _source_url(info: dict[str, Any]) -> str:
    for key in ("original_url", "webpage_url", "url"):
        value = info.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _fallback_file_path(output_dir: Path, info: dict[str, Any]) -> Path | None:
    video_id = str(info.get("id", "")).strip()
    if not video_id:
        return None

    for candidate in output_dir.glob(f"*_{video_id}.*"):
        if candidate.suffix != ".json" and candidate.name.endswith(".info.json") is False:
            return candidate

    return None


def _fallback_info_json_path(output_dir: Path, info: dict[str, Any]) -> Path | None:
    video_id = str(info.get("id", "")).strip()
    if not video_id:
        return None

    for candidate in output_dir.glob(f"*_{video_id}.info.json"):
        if candidate.is_file():
            return candidate
    for candidate in output_dir.glob(f"*_{video_id}.*.info.json"):
        if candidate.is_file():
            return candidate
    return None


def _find_info_json_path(video_path: Path) -> Path | None:
    candidates = (
        video_path.with_suffix(f"{video_path.suffix}.info.json"),
        video_path.with_suffix(".info.json"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _normalize_optional(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
