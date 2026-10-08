from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from reels_analyzer.config import RuntimeConfig
from reels_analyzer.downloader import YtDlpDownloader
from reels_analyzer.insights import ChannelInsightsAnalyzer
from reels_analyzer.media import AudioPreprocessor, SceneDetector, WhisperTranscriber
from reels_analyzer.models import (
    AIReviewResult,
    SceneAnalysisResult,
    TranscriptionResult,
    VideoRecord,
)
from reels_analyzer.project_state import ProjectStateIndex, build_link_action_plan
from reels_analyzer.reviewer import OllamaReviewer
from reels_analyzer.sources import ManualLinksSource
from reels_analyzer.writer import CsvReportWriter

logger = logging.getLogger(__name__)


class ChannelPipeline:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self.source = ManualLinksSource()
        self.downloader = YtDlpDownloader()
        self.writer = CsvReportWriter()
        self._audio_preprocessor: AudioPreprocessor | None = None
        self._scene_detector: SceneDetector | None = None
        self._transcriber: WhisperTranscriber | None = None
        self._reviewer: OllamaReviewer | None = None
        self._existing_index: dict[str, dict[str, str]] = {}
        self._state_index: ProjectStateIndex | None = None
        self._insights_analyzer = ChannelInsightsAnalyzer()

    def run(self) -> list[VideoRecord]:
        self.config.project.ensure_directories()
        self._existing_index = self.writer.load_index(self.config.project.results_csv_path)
        logger.info("Existing report rows: %s", len(self._existing_index))
        state = ProjectStateIndex.scan(
            project=self.config.project,
            whisper_model=self.config.whisper_model,
            ollama_model=self.config.ollama_model,
        )
        self._state_index = state
        if self.config.features.use_existing_videos:
            videos = self.downloader.load_existing(self.config.project.videos_dir)
            logger.info(
                "Using existing videos from %s (%s file(s))",
                self.config.project.videos_dir,
                len(videos),
            )
        else:
            if not _same_path(self.config.links_file, self.config.project.links_snapshot_path):
                shutil.copyfile(self.config.links_file, self.config.project.links_snapshot_path)

            links = self.source.resolve(
                channel_name=self.config.channel_name,
                links_file=self.config.links_file,
            )
            if not links:
                raise RuntimeError("No valid video links were found in the provided links file.")
            logger.info("Resolved %s link(s) from %s", len(links), self.config.links_file)
            plan = build_link_action_plan(
                links=links,
                state=state,
                features=self.config.features,
                ollama_model=self.config.ollama_model,
            )
            for line in plan.log_lines(self.config.features):
                logger.info(line)

            if self.config.features.download_media:
                logger.info("Download mode: ON")
                existing_videos = self.downloader.load_existing_for_ids(
                    output_dir=self.config.project.videos_dir,
                    video_ids={
                        _video_id_from_source_url(link.url)
                        for link in plan.links_with_media
                        if _video_id_from_source_url(link.url)
                    },
                    include_info_only=False,
                )
                downloaded_videos = self.downloader.download(
                    links=plan.links_missing_media,
                    output_dir=self.config.project.videos_dir,
                    archive_path=self.config.project.archive_path,
                )
                videos = existing_videos + downloaded_videos
            else:
                logger.info("Download mode: OFF (metadata only + info.json)")
                existing_videos = self.downloader.load_existing_for_ids(
                    output_dir=self.config.project.videos_dir,
                    video_ids={
                        _video_id_from_source_url(link.url)
                        for link in plan.links_with_metadata
                        if _video_id_from_source_url(link.url)
                    },
                    include_info_only=True,
                )
                inspected_videos = self.downloader.inspect_only(
                    links=plan.links_missing_metadata,
                    output_dir=self.config.project.videos_dir,
                )
                videos = existing_videos + inspected_videos

        if not videos:
            if self.config.features.use_existing_videos:
                raise RuntimeError(
                    f"No local videos found in project folder: {self.config.project.videos_dir}"
                )
            raise RuntimeError("No videos were resolved for processing.")

        records = [VideoRecord(video=video) for video in videos]
        total = len(records)
        for index, record in enumerate(records, start=1):
            self._enrich_record(record, index=index, total=total)
            self._persist_record(record)

        self.writer.write(records, self.config.project.results_csv_path)
        enriched_rows = self._insights_analyzer.analyze_rows(
            self.writer.load_rows(self.config.project.results_csv_path)
        )
        self.writer.write_rows(enriched_rows, self.config.project.results_csv_path)
        if self.config.features.classify_text:
            self.writer.write_ai_reviews(records, self.config.project.ai_reviews_csv_path)
        return records

    def _enrich_record(self, record: VideoRecord, index: int, total: int) -> None:
        existing = self._get_existing_entry(record)
        label = record.video.video_id or record.video.source_url or "unknown-video"
        logger.info("[%s/%s] Processing %s", index, total, label)
        record.transcription_model = (
            self.config.whisper_model if self.config.features.transcribe_audio else ""
        )
        record.classification_model = (
            self.config.ollama_model if self.config.features.classify_text else ""
        )

        if self.config.features.analyze_video:
            restored_scene = self._restore_scene_analysis(record=record, existing=existing)
            if restored_scene:
                logger.info("[%s/%s] Restored scene analysis from existing videos.csv.", index, total)
            elif record.video.file_path is None:
                record.scene_analysis = SceneAnalysisResult(skipped_reason="file_not_downloaded")
            else:
                record.scene_analysis = self._get_scene_detector().analyze(
                    file_path=record.video.file_path,
                    duration_sec=record.video.duration_sec,
                )
        else:
            record.scene_analysis = SceneAnalysisResult(skipped_reason="feature_disabled")

        if self.config.features.transcribe_audio:
            restored = self._restore_transcription(record=record, existing=existing)
            if restored:
                logger.info("[%s/%s] Restored from existing transcript file.", index, total)
            elif record.video.file_path is None:
                record.transcription = TranscriptionResult(skipped_reason="file_not_downloaded")
                logger.info("[%s/%s] Transcribe skipped: file not downloaded.", index, total)
            else:
                logger.info(
                    "[%s/%s] Extracting audio from %s",
                    index,
                    total,
                    record.video.file_path,
                )
                audio_path = self._get_audio_preprocessor().extract_wav(
                    video_file_path=record.video.file_path,
                    output_dir=self.config.project.cache_dir / "audio",
                )
                record.audio_file_path = audio_path

                if audio_path is None:
                    record.transcription = TranscriptionResult(skipped_reason="no_audio_stream")
                    logger.info("[%s/%s] Transcribe skipped: no audio stream.", index, total)
                else:
                    logger.info("[%s/%s] Running Whisper...", index, total)
                    record.transcription = self._get_transcriber().transcribe(
                        audio_file_path=audio_path,
                        duration_sec=record.video.duration_sec,
                        progress_prefix=f"[{index}/{total}]",
                    )
                    record.transcript_file_path = self._save_transcript(record)
                    logger.info(
                        "[%s/%s] Transcribe done: %s words, saved to %s",
                        index,
                        total,
                        record.transcription.word_count,
                        record.transcript_file_path,
                    )
        else:
            record.transcription = TranscriptionResult(skipped_reason="feature_disabled")

        if self.config.features.classify_text:
            restored_ai_review = self._restore_ai_review(record)
            if restored_ai_review:
                logger.info("[%s/%s] Restored AI review from existing ai_reviews.csv.", index, total)
            else:
                record.ai_review = self._get_reviewer().review(
                    transcript=record.transcription.transcript,
                    first_phrase=record.transcription.first_phrase,
                    duration_sec=record.video.duration_sec,
                    scene_count=record.scene_analysis.scene_count,
                    pace=record.scene_analysis.pace_label,
                )
        else:
            record.ai_review = AIReviewResult(skipped_reason="feature_disabled")

    def _persist_record(self, record: VideoRecord) -> None:
        self.writer.write([record], self.config.project.results_csv_path)
        self._existing_index[self._record_key(record)] = record.to_csv_row()
        if self.config.features.classify_text:
            self.writer.write_ai_reviews([record], self.config.project.ai_reviews_csv_path)

    def _restore_scene_analysis(self, record: VideoRecord, existing: ExistingEntry | None) -> bool:
        if existing is None:
            return False
        if existing.scene_skipped_reason:
            return False
        if existing.pace_label in ("", "not_run"):
            return False

        record.scene_analysis = SceneAnalysisResult(
            scene_count=existing.scene_count,
            avg_scene_length_sec=existing.avg_scene_length_sec,
            pace_label=existing.pace_label,
        )
        return True

    def _get_audio_preprocessor(self) -> AudioPreprocessor:
        if self._audio_preprocessor is None:
            self._audio_preprocessor = AudioPreprocessor()
        return self._audio_preprocessor

    def _get_scene_detector(self) -> SceneDetector:
        if self._scene_detector is None:
            self._scene_detector = SceneDetector()
        return self._scene_detector

    def _get_transcriber(self) -> WhisperTranscriber:
        if self._transcriber is None:
            self._transcriber = WhisperTranscriber(model_size=self.config.whisper_model)
        return self._transcriber

    def _get_reviewer(self) -> OllamaReviewer:
        if self._reviewer is None:
            self._reviewer = OllamaReviewer(
                model=self.config.ollama_model,
                base_url=self.config.ollama_base_url,
            )
        return self._reviewer

    def _save_transcript(self, record: VideoRecord) -> Path:
        target = self._transcript_path_for_record(record)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(record.transcription.transcript, encoding="utf-8")
        return target

    def _record_key(self, record: VideoRecord) -> str:
        if record.video.video_id:
            return f"video_id:{record.video.video_id}"
        return f"source_url:{record.video.source_url}"

    def _get_existing_entry(self, record: VideoRecord) -> ExistingEntry | None:
        row = self._existing_index.get(self._record_key(record))
        if row is None:
            return None
        return ExistingEntry.from_row(row)

    def _restore_transcription(self, record: VideoRecord, existing: ExistingEntry | None) -> bool:
        expected_path = self._transcript_path_for_record(record)
        if expected_path.exists():
            text = expected_path.read_text(encoding="utf-8")
            record.transcription = self._build_transcription_from_text(
                text=text,
                duration_sec=record.video.duration_sec,
            )
            record.transcript_file_path = expected_path
            return True

        if existing is None:
            return False
        if existing.transcription_skipped_reason:
            return False
        if not existing.transcript_text:
            return False

        record.transcription = TranscriptionResult(
            transcript=existing.transcript_text,
            first_phrase=existing.first_phrase,
            word_count=existing.word_count,
            words_per_second=existing.words_per_second,
        )
        if existing.transcript_file_path is not None:
            record.transcript_file_path = existing.transcript_file_path
        else:
            # Legacy CSV row may contain transcript text without transcript_file_path.
            record.transcript_file_path = expected_path
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            expected_path.write_text(existing.transcript_text, encoding="utf-8")
        return True

    def _restore_ai_review(self, record: VideoRecord) -> bool:
        if self._state_index is None:
            return False
        video_id = (record.video.video_id or "").strip()
        if not video_id:
            return False
        key = f"{video_id}|{self.config.ollama_model}"
        row = self._state_index.ai_review_rows_by_key.get(key)
        if row is None:
            return False

        record.ai_review = AIReviewResult(
            content_type=(row.get("content_type") or "").strip() or "not_run",
            hook_type=(row.get("hook_type") or "").strip() or "not_run",
            tone=(row.get("tone") or "").strip() or "not_run",
            summary=(row.get("summary") or "").strip(),
            strengths=_split_pipe_list(row.get("strengths", "")),
            weaknesses=_split_pipe_list(row.get("weaknesses", "")),
            skipped_reason=(row.get("classification_skipped_reason") or "").strip() or None,
        )
        return True

    def _transcript_path_for_record(self, record: VideoRecord) -> Path:
        identifier = record.video.video_id
        if not identifier:
            identifier = record.video.file_path.stem if record.video.file_path else "video"
        model_slug = _slug_for_filename(self.config.whisper_model)
        return self.config.project.transcripts_dir / f"{identifier}__{model_slug}.txt"

    def _build_transcription_from_text(
        self,
        text: str,
        duration_sec: float | None,
    ) -> TranscriptionResult:
        words = text.split()
        word_count = len(words)
        safe_duration = duration_sec or 0.0
        return TranscriptionResult(
            transcript=text,
            first_phrase=" ".join(words[:10]) if words else "",
            word_count=word_count,
            words_per_second=(word_count / safe_duration) if safe_duration > 0 else 0.0,
        )


@dataclass(slots=True)
class ExistingEntry:
    transcript_file_path: Path | None
    transcript_text: str
    first_phrase: str
    word_count: int
    words_per_second: float
    transcription_skipped_reason: str | None
    scene_count: int
    avg_scene_length_sec: float
    pace_label: str
    scene_skipped_reason: str | None

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "ExistingEntry":
        path_text = (row.get("transcript_file_path") or "").strip()
        transcript_path = Path(path_text) if path_text else None
        transcript_text = ""
        if transcript_path is not None and transcript_path.exists():
            transcript_text = transcript_path.read_text(encoding="utf-8")
        elif row.get("transcript"):
            # Backward compatibility with old CSV format where full transcript was in-column.
            transcript_text = row.get("transcript", "")
            if transcript_path is not None:
                transcript_path.parent.mkdir(parents=True, exist_ok=True)
                transcript_path.write_text(transcript_text, encoding="utf-8")

        return cls(
            transcript_file_path=transcript_path,
            transcript_text=transcript_text,
            first_phrase=row.get("first_phrase", ""),
            word_count=_safe_int(row.get("word_count")),
            words_per_second=_safe_float(row.get("words_per_second")),
            transcription_skipped_reason=(row.get("transcription_skipped_reason") or "").strip()
            or None,
            scene_count=_safe_int(row.get("scene_count")),
            avg_scene_length_sec=_safe_float(row.get("avg_scene_length_sec")),
            pace_label=(row.get("pace_label") or "").strip(),
            scene_skipped_reason=(row.get("scene_skipped_reason") or "").strip() or None,
        )


def _safe_int(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _safe_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _slug_for_filename(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "model"


def _same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve() == right.expanduser().resolve()


def _video_id_from_source_url(value: str) -> str:
    matches = re.findall(r"(\d{18,20})", value or "")
    if not matches:
        return ""
    return matches[0]


def _split_pipe_list(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split("|") if item.strip()]
