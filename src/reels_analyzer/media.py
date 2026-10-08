from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from reels_analyzer.dependencies import require_command, require_python_package
from reels_analyzer.models import SceneAnalysisResult, TranscriptionResult
from reels_analyzer.service_logging import logged_service_call

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    @logged_service_call(
        "audio.extract_wav",
        include=("video_file_path", "output_dir"),
        result=lambda value: {"audio_file_path": value or "none"},
    )
    def extract_wav(self, video_file_path: Path, output_dir: Path) -> Path | None:
        require_command("ffprobe", "transcribe-audio")
        require_command("ffmpeg", "transcribe-audio")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_file_path = output_dir / f"{video_file_path.stem}.wav"
        if output_file_path.exists() and output_file_path.stat().st_size > 0:
            logger.info("Using cached WAV: %s", output_file_path)
            return output_file_path

        if not self._has_audio_stream(video_file_path):
            return None

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_file_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg audio extraction error: {result.stderr.strip()}")
        return output_file_path

    def _has_audio_stream(self, video_file_path: Path) -> bool:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            str(video_file_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe error: {result.stderr.strip()}")
        data = json.loads(result.stdout)
        return any(stream.get("codec_type") == "audio" for stream in data.get("streams", []))


class WhisperTranscriber:
    def __init__(self, model_size: str) -> None:
        require_python_package("faster_whisper", "transcribe-audio")

        from faster_whisper import WhisperModel

        logger.info(
            "Initializing Whisper model '%s' on CPU (first run may download model files)...",
            model_size,
        )
        self.model = WhisperModel(model_size, compute_type="int8", device="cpu")
        logger.info("Whisper model '%s' is ready.", model_size)

    @logged_service_call(
        "whisper.transcribe",
        include=("audio_file_path", "duration_sec", "progress_prefix"),
        result=lambda value: {
            "word_count": value.word_count,
            "words_per_second": round(value.words_per_second, 2),
        },
    )
    def transcribe(
        self,
        audio_file_path: Path,
        duration_sec: float | None,
        progress_prefix: str = "[transcribe]",
    ) -> TranscriptionResult:
        segments, _ = self.model.transcribe(str(audio_file_path))
        text_parts: list[str] = []
        safe_duration = duration_sec or 0.0
        next_progress_mark = 10
        progress_line = _ConsoleProgressLine(prefix=progress_prefix)

        for segment in segments:
            cleaned_text = segment.text.strip()
            if cleaned_text:
                text_parts.append(cleaned_text)

            if safe_duration > 0:
                segment_end = getattr(segment, "end", None)
                if isinstance(segment_end, (int, float)):
                    current_percent = int(min(100, (float(segment_end) / safe_duration) * 100))
                    while current_percent >= next_progress_mark and next_progress_mark <= 100:
                        progress_line.update(next_progress_mark)
                        next_progress_mark += 10

        transcript = " ".join(text_parts).strip()
        words = transcript.split()
        word_count = len(words)

        if safe_duration > 0 and next_progress_mark <= 100 and word_count > 0:
            progress_line.update(100)
        progress_line.finish()

        return TranscriptionResult(
            transcript=transcript,
            first_phrase=" ".join(words[:10]) if words else "",
            word_count=word_count,
            words_per_second=(word_count / safe_duration) if safe_duration > 0 else 0.0,
        )


class SceneDetector:
    def __init__(self, threshold: float = 27.0) -> None:
        require_python_package("scenedetect", "analyze-video")
        self.threshold = threshold

    @logged_service_call(
        "scene_detect.analyze",
        include=("file_path", "duration_sec"),
        result=lambda value: {
            "scene_count": value.scene_count,
            "avg_scene_length_sec": round(value.avg_scene_length_sec, 2),
            "pace_label": value.pace_label,
        },
    )
    def analyze(self, file_path: Path, duration_sec: float | None) -> SceneAnalysisResult:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector

        video = open_video(str(file_path))
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=self.threshold))
        scene_manager.detect_scenes(video)

        scenes: list[tuple[float, float]] = []
        for start, end in scene_manager.get_scene_list():
            scenes.append((start.get_seconds(), end.get_seconds()))

        safe_duration = duration_sec or 0.0
        scene_count = len(scenes)
        if scene_count == 0 and safe_duration > 0:
            scene_count = 1
            scenes = [(0.0, safe_duration)]

        avg_scene_length_sec = (safe_duration / scene_count) if scene_count else 0.0
        if avg_scene_length_sec >= 4.0:
            pace_label = "slow"
        elif avg_scene_length_sec >= 2.0:
            pace_label = "medium"
        elif scene_count > 0:
            pace_label = "fast"
        else:
            pace_label = "not_run"

        return SceneAnalysisResult(
            scene_count=scene_count,
            avg_scene_length_sec=avg_scene_length_sec,
            pace_label=pace_label,
            scenes=scenes,
        )


class _ConsoleProgressLine:
    """Single-line progress renderer for interactive terminals only."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self._enabled = sys.stdout.isatty()
        self._dirty = False

    def update(self, percent: int) -> None:
        if not self._enabled:
            return
        sys.stdout.write(f"\r{self.prefix} Progress: ~{percent}%")
        sys.stdout.flush()
        self._dirty = True

    def finish(self) -> None:
        if not self._enabled or not self._dirty:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()
