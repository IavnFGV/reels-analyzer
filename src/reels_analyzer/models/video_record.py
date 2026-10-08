from dataclasses import dataclass, field
from pathlib import Path

from reels_analyzer.models.ai_review_result import AIReviewResult
from reels_analyzer.models.derived_insights_result import DerivedInsightsResult
from reels_analyzer.models.downloaded_video import DownloadedVideo
from reels_analyzer.models.scene_analysis_result import SceneAnalysisResult
from reels_analyzer.models.transcription_result import TranscriptionResult


@dataclass(slots=True)
class VideoRecord:
    video: DownloadedVideo
    audio_file_path: Path | None = None
    transcript_file_path: Path | None = None
    transcription_model: str = ""
    classification_model: str = ""
    transcription: TranscriptionResult = field(default_factory=TranscriptionResult)
    scene_analysis: SceneAnalysisResult = field(default_factory=SceneAnalysisResult)
    ai_review: AIReviewResult = field(default_factory=AIReviewResult)
    derived_insights: DerivedInsightsResult = field(default_factory=DerivedInsightsResult)

    def to_csv_row(self) -> dict[str, str]:
        return {
            "source_url": self.video.source_url,
            "video_id": self.video.video_id,
            "title": self.video.title,
            "uploader": self.video.uploader,
            "upload_date": self.video.upload_date or "",
            "webpage_url": self.video.webpage_url,
            "file_path": str(self.video.file_path) if self.video.file_path else "",
            "info_json_path": str(self.video.info_json_path) if self.video.info_json_path else "",
            "duration_sec": _format_float(self.video.duration_sec),
            "width": _format_int(self.video.width),
            "height": _format_int(self.video.height),
            "fps": _format_float(self.video.fps),
            "view_count": _format_int(self.video.view_count),
            "like_count": _format_int(self.video.like_count),
            "comment_count": _format_int(self.video.comment_count),
            "audio_file_path": str(self.audio_file_path) if self.audio_file_path else "",
            "transcription_model": self.transcription_model,
            "classification_model": self.classification_model,
            "scene_count": _format_int(self.scene_analysis.scene_count),
            "avg_scene_length_sec": _format_float(self.scene_analysis.avg_scene_length_sec),
            "pace_label": self.scene_analysis.pace_label,
            "scene_skipped_reason": self.scene_analysis.skipped_reason or "",
            "transcript_file_path": (
                str(self.transcript_file_path) if self.transcript_file_path else ""
            ),
            "first_phrase": self.transcription.first_phrase,
            "word_count": _format_int(self.transcription.word_count),
            "words_per_second": _format_float(self.transcription.words_per_second),
            "transcription_skipped_reason": self.transcription.skipped_reason or "",
            "content_type": self.ai_review.content_type,
            "hook_type": self.ai_review.hook_type,
            "tone": self.ai_review.tone,
            "summary": self.ai_review.summary,
            "strengths": " | ".join(self.ai_review.strengths),
            "weaknesses": " | ".join(self.ai_review.weaknesses),
            "classification_skipped_reason": self.ai_review.skipped_reason or "",
            "performance_cohort": self.derived_insights.performance_cohort,
            "performance_baseline_view_count": _format_float(
                self.derived_insights.performance_baseline_view_count
            ),
            "performance_score": _format_float(self.derived_insights.performance_score),
            "performance_bucket": self.derived_insights.performance_bucket,
            "hook_subject": self.derived_insights.hook_subject,
            "hook_format": self.derived_insights.hook_format,
            "hook_emotion": self.derived_insights.hook_emotion,
            "hook_specificity": self.derived_insights.hook_specificity,
            "hook_strength_score": _format_int(self.derived_insights.hook_strength_score),
            "topic_cluster": self.derived_insights.topic_cluster,
            "insight_tags": " | ".join(self.derived_insights.normalized_tags()),
        }

    def to_ai_review_row(self) -> dict[str, str]:
        return {
            "video_id": self.video.video_id,
            "source_url": self.video.source_url,
            "file_path": str(self.video.file_path) if self.video.file_path else "",
            "transcript_file_path": (
                str(self.transcript_file_path) if self.transcript_file_path else ""
            ),
            "transcription_model": self.transcription_model,
            "ollama_model": self.classification_model,
            "content_type": self.ai_review.content_type,
            "hook_type": self.ai_review.hook_type,
            "tone": self.ai_review.tone,
            "summary": self.ai_review.summary,
            "strengths": " | ".join(self.ai_review.strengths),
            "weaknesses": " | ".join(self.ai_review.weaknesses),
            "classification_skipped_reason": self.ai_review.skipped_reason or "",
        }


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def _format_int(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)
