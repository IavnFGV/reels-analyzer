from __future__ import annotations

import json
import logging
import re
from typing import Any

from reels_analyzer.dependencies import require_python_package
from reels_analyzer.models import AIReviewResult
from reels_analyzer.service_logging import logged_service_call

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = (
    "no_audio",
    "educational",
    "instruction",
    "text_led",
    "short_form",
    "vlog",
    "social",
    "generic_video",
    "other",
)
ALLOWED_HOOK_TYPES = (
    "emotional",
    "call_to_action",
    "question",
    "curiosity",
    "informational",
    "problem_solution",
    "neutral",
    "unknown",
)
ALLOWED_TONES = (
    "neutral",
    "positive",
    "negative",
    "mixed",
    "urgent",
    "calm",
    "dramatic",
    "friendly",
    "authoritative",
    "mystical",
    "energetic",
    "empathetic",
    "unknown",
)


class OllamaReviewer:
    def __init__(self, model: str, base_url: str) -> None:
        require_python_package("requests", "classify-text")

        import requests

        self._requests = requests
        self.model = model
        self.base_url = base_url

    @logged_service_call(
        "ollama.review",
        include=("duration_sec", "scene_count", "pace"),
        transforms={
            "first_phrase": lambda value: {"first_phrase": " ".join(str(value).split())[:80]},
            "transcript": lambda value: {"transcript_chars": len((value or "").strip())},
        },
        result=lambda value: {
            "content_type": value.content_type,
            "hook_type": value.hook_type,
            "tone": value.tone,
        },
    )
    def review(
        self,
        transcript: str,
        first_phrase: str,
        duration_sec: float | None,
        scene_count: int,
        pace: str,
    ) -> AIReviewResult:
        if not transcript.strip():
            return AIReviewResult(
                content_type="no_audio",
                hook_type="unknown",
                tone="unknown",
                weaknesses=["video has no audio track"],
                summary="Text classification skipped because there is no transcript.",
                skipped_reason="empty_transcript",
            )

        prompt = f"""
You are analyzing a short-form social video.

Return JSON only with this exact schema:
{{
  "content_type": "string",
  "hook_type": "string",
  "tone": "string",
  "summary": "string",
  "strengths": ["string"],
  "weaknesses": ["string"]
}}

Instructions:
- Be concise.
- Do not add markdown.
- Do not add explanation outside JSON.
- content_type must be one of: {", ".join(ALLOWED_CONTENT_TYPES)}
- hook_type must be one of: {", ".join(ALLOWED_HOOK_TYPES)}
- tone must be one of: {", ".join(ALLOWED_TONES)}
- strengths should contain 1-4 short items.
- weaknesses should contain 1-4 short items.
- summary should be in Russian and under 50 words.

Video features:
- duration_sec: {duration_sec or 0}
- scene_count: {scene_count}
- pace: {pace}
- first_phrase: {first_phrase}
- transcript: {transcript}
""".strip()

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "options": {"temperature": 0},
            "stream": False,
        }
        response = self._requests.post(self.base_url, json=payload, timeout=120)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        content = str(data["message"]["content"]).strip()
        parsed = _parse_json_response(content)

        raw_content_type = str(parsed.get("content_type", "other"))
        raw_hook_type = str(parsed.get("hook_type", "unknown"))
        raw_tone = str(parsed.get("tone", "unknown"))

        content_type = _normalize_content_type(raw_content_type)
        hook_type = _normalize_hook_type(raw_hook_type)
        tone = _normalize_tone(raw_tone)

        _warn_if_remapped("content_type", raw_content_type, content_type)
        _warn_if_remapped("hook_type", raw_hook_type, hook_type)
        _warn_if_remapped("tone", raw_tone, tone)

        summary = _normalize_summary(
            str(parsed.get("summary", "")),
            fallback_source=first_phrase or transcript,
        )
        strengths = _normalize_bullets(parsed.get("strengths"), fallback="не указано")
        weaknesses = _normalize_bullets(parsed.get("weaknesses"), fallback="не указано")

        return AIReviewResult(
            content_type=content_type,
            hook_type=hook_type,
            tone=tone,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
        )


def _normalize_label(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return cleaned or "unknown"


def _normalize_content_type(value: str) -> str:
    label = _normalize_label(value)
    if label in ALLOWED_CONTENT_TYPES:
        return label
    if label in {"video", "video_analysis"}:
        return "generic_video"
    if label in {"educational_video", "explaination", "explanation"}:
        return "educational"
    if label in {"instruction_video", "instructional", "tutorial"}:
        return "instruction"
    if label in {"text", "videotext", "video_transcript", "text_vlog"}:
        return "text_led"
    if label in {"short_video", "short_form_social_video", "videoclip"}:
        return "short_form"
    if label == "unknown":
        return "other"
    return "other"


def _normalize_hook_type(value: str) -> str:
    label = _normalize_label(value)
    if label in ALLOWED_HOOK_TYPES:
        return label
    if label in {"empathy", "empathetic", "motivational", "inspiration"}:
        return "emotional"
    if label in {"surprise", "anticipation"}:
        return "curiosity"
    if label in {"insightful", "announcement"}:
        return "informational"
    return "unknown"


def _normalize_tone(value: str) -> str:
    label = _normalize_label(value)
    if label in ALLOWED_TONES:
        return label
    if label in {"warm", "kind", "supportive"}:
        return "friendly"
    if label in {"serious", "formal"}:
        return "authoritative"
    if label in {"anxious", "tense"}:
        return "urgent"
    if label in {"excited", "dynamic"}:
        return "energetic"
    return "unknown"


def _normalize_summary(value: str, fallback_source: str = "") -> str:
    text = " ".join((value or "").split())
    if text and not re.search(r"[А-Яа-яЁё]", text):
        logger.warning("Summary is not in Russian, generating fallback summary.")
        text = ""

    if not text:
        source = " ".join((fallback_source or "").split())
        if source:
            text = f"Короткий ролик с тезисом: {source}"
        else:
            text = "Короткий ролик без краткого резюме."

    words = text.split()
    if len(words) > 50:
        words = words[:50]
    return " ".join(words)


def _parse_json_response(content: str) -> dict[str, Any]:
    candidates = [content.strip()]

    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise RuntimeError(f"Ollama did not return valid JSON: {content}")


def _normalize_bullets(value: Any, fallback: str) -> list[str]:
    if not isinstance(value, list):
        value = []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = " ".join(str(item).split()).strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
        if len(cleaned) >= 4:
            break

    while len(cleaned) < 2:
        cleaned.append(fallback)
    return cleaned


def _warn_if_remapped(field: str, raw_value: str, normalized_value: str) -> None:
    if _normalize_label(raw_value) == normalized_value:
        return
    logger.warning(
        "Normalized %s from '%s' to '%s'.",
        field,
        raw_value,
        normalized_value,
    )
