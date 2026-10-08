from __future__ import annotations

import math
import re
from collections import defaultdict

from reels_analyzer.models.derived_insights_result import DerivedInsightsResult


class ChannelInsightsAnalyzer:
    def analyze_rows(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        if not rows:
            return rows

        baselines = self._build_monthly_baselines(rows)
        enriched: list[dict[str, str]] = []
        for row in rows:
            result = self._analyze_row(row=row, baselines=baselines)
            enriched.append(self._merge_result(row=row, result=result))
        return enriched

    def _analyze_row(
        self,
        row: dict[str, str],
        baselines: dict[str, float],
    ) -> DerivedInsightsResult:
        text = self._source_text(row)
        tokens = _tokenize(text)
        cohort = self._cohort_key(row)
        views = _safe_float(row.get("view_count"))
        baseline = baselines.get(cohort, baselines.get("all", 0.0))

        subject = self._detect_subject(text, tokens)
        hook_format = self._detect_format(text, tokens)
        emotion = self._detect_emotion(text, tokens)
        specificity, specificity_score = self._detect_specificity(text, tokens)
        strength_score = min(5, max(1 if text else 0, specificity_score + self._strength_bonus(text)))
        topic_cluster = self._detect_topic_cluster(subject=subject, emotion=emotion, text=text)
        tags = self._build_tags(
            row=row,
            subject=subject,
            hook_format=hook_format,
            emotion=emotion,
            specificity=specificity,
            strength_score=strength_score,
        )

        performance_score, performance_bucket = self._performance_metrics(
            views=views,
            baseline=baseline,
        )

        return DerivedInsightsResult(
            performance_cohort=cohort,
            performance_baseline_view_count=baseline,
            performance_score=performance_score,
            performance_bucket=performance_bucket,
            hook_subject=subject,
            hook_format=hook_format,
            hook_emotion=emotion,
            hook_specificity=specificity,
            hook_strength_score=strength_score,
            topic_cluster=topic_cluster,
            insight_tags=tags,
        )

    def _build_monthly_baselines(self, rows: list[dict[str, str]]) -> dict[str, float]:
        views_by_cohort: dict[str, list[float]] = defaultdict(list)
        all_views: list[float] = []
        for row in rows:
            views = _safe_float(row.get("view_count"))
            if views <= 0:
                continue
            cohort = self._cohort_key(row)
            views_by_cohort[cohort].append(views)
            all_views.append(views)

        baselines: dict[str, float] = {}
        for cohort, values in views_by_cohort.items():
            baselines[cohort] = _median(values)
        baselines["all"] = _median(all_views) if all_views else 0.0
        return baselines

    def _merge_result(
        self,
        row: dict[str, str],
        result: DerivedInsightsResult,
    ) -> dict[str, str]:
        merged = dict(row)
        merged.update(
            {
                "performance_cohort": result.performance_cohort,
                "performance_baseline_view_count": _format_float(
                    result.performance_baseline_view_count
                ),
                "performance_score": _format_float(result.performance_score),
                "performance_bucket": result.performance_bucket,
                "hook_subject": result.hook_subject,
                "hook_format": result.hook_format,
                "hook_emotion": result.hook_emotion,
                "hook_specificity": result.hook_specificity,
                "hook_strength_score": str(result.hook_strength_score),
                "topic_cluster": result.topic_cluster,
                "insight_tags": " | ".join(result.normalized_tags()),
            }
        )
        return merged

    def _source_text(self, row: dict[str, str]) -> str:
        candidates = [
            row.get("first_phrase", ""),
            row.get("title", ""),
            row.get("summary", ""),
        ]
        combined = " ".join(part.strip() for part in candidates if part and part.strip())
        return " ".join(combined.split())

    def _cohort_key(self, row: dict[str, str]) -> str:
        upload_date = (row.get("upload_date") or "").strip()
        if len(upload_date) >= 6 and upload_date[:6].isdigit():
            return f"{upload_date[:4]}-{upload_date[4:6]}"
        return "unknown"

    def _detect_subject(self, text: str, tokens: set[str]) -> str:
        if _contains_any(text, ("деньг", "финанс", "доход", "работ", "бизнес")):
            return "money"
        if _contains_any(text, ("энерг", "сил", "ресурс")):
            return "energy"
        if _contains_any(text, ("соперниц", "любовниц", "другая", "конкурент")):
            return "rival"
        if _contains_any(text, ("отношен", "любит", "мужчин", "он ", "она ", "бывш", "партнер")):
            return "relationship"
        if _contains_any(text, ("что будет", "что произойдет", "дальше", "скоро", "ближайш")):
            return "future"
        if "кто" in tokens:
            return "identity"
        return "general"

    def _detect_format(self, text: str, tokens: set[str]) -> str:
        if _contains_any(text, ("в ближайшие", "48 часов", "сегодня", "завтра", "скоро")):
            return "timeline"
        if _contains_any(text, ("тайно", "скрывает", "секрет", "правда")):
            return "reveal"
        if _contains_any(text, ("опас", "вредит", "враг", "осторож", "нельзя")):
            return "warning"
        if _contains_any(text, ("произойдет", "ждет", "случится", "получите", "будет")):
            return "promise"
        if "?" in text or _contains_any(text, ("что", "кто", "как", "почему")):
            return "question"
        if _contains_any(text, ("сделай", "нанесите", "посмотрите", "загадайте")):
            return "instruction"
        return "statement"

    def _detect_emotion(self, text: str, tokens: set[str]) -> str:
        if _contains_any(text, ("соперниц", "любовниц", "другая")):
            return "jealousy"
        if _contains_any(text, ("вредит", "враг", "опас", "утекает", "теряете")):
            return "fear"
        if _contains_any(text, ("любит", "ждет", "счаст", "скоро", "хорош")):
            return "hope"
        if _contains_any(text, ("думает", "в его глазах", "кто вас любит", "кто вас тайно")):
            return "validation"
        if "что" in tokens or "кто" in tokens:
            return "curiosity"
        return "neutral"

    def _detect_specificity(self, text: str, tokens: set[str]) -> tuple[str, int]:
        score = 0
        if _contains_any(text, ("48 часов", "сегодня", "завтра", "недел", "месяц", "скоро")):
            score += 2
        if _contains_any(text, ("он", "она", "мужчин", "бывш", "конкретного")):
            score += 1
        if _contains_any(text, ("что будет", "что произойдет", "между вами", "в его глазах")):
            score += 1
        if _contains_any(text, ("деньги", "энергия", "отношения")):
            score += 1

        if score >= 4:
            return "high", 4
        if score >= 2:
            return "medium", 3
        if text or tokens:
            return "low", 1
        return "unknown", 0

    def _strength_bonus(self, text: str) -> int:
        bonus = 0
        if _contains_any(text, ("внезапно", "тайно", "не ждете", "очень скоро")):
            bonus += 1
        if "?" in text:
            bonus += 1
        return bonus

    def _detect_topic_cluster(self, subject: str, emotion: str, text: str) -> str:
        if subject == "relationship" and emotion in {"hope", "validation", "jealousy"}:
            return "relationship_tension"
        if subject == "future":
            return "future_prediction"
        if subject == "money":
            return "money_signal"
        if subject == "energy":
            return "energy_state"
        if _contains_any(text, ("руна", "таро", "карта")):
            return "esoteric_tool"
        return subject

    def _performance_metrics(self, views: float, baseline: float) -> tuple[float, str]:
        if views <= 0 or baseline <= 0:
            return 0.0, "unknown"

        ratio = views / baseline
        score = math.log1p(views) - math.log1p(baseline)
        if ratio >= 3.0:
            bucket = "breakout"
        elif ratio >= 1.5:
            bucket = "winner"
        elif ratio >= 0.67:
            bucket = "baseline"
        else:
            bucket = "underperformer"
        return score, bucket

    def _build_tags(
        self,
        row: dict[str, str],
        subject: str,
        hook_format: str,
        emotion: str,
        specificity: str,
        strength_score: int,
    ) -> list[str]:
        tags = [f"subject:{subject}", f"format:{hook_format}", f"emotion:{emotion}"]
        if specificity != "unknown":
            tags.append(f"specificity:{specificity}")
        if strength_score >= 4:
            tags.append("strong_hook")

        duration = _safe_float(row.get("duration_sec"))
        if duration >= 120:
            tags.append("long_duration")
        elif duration > 0 and duration <= 30:
            tags.append("short_duration")

        wps = _safe_float(row.get("words_per_second"))
        if wps >= 2.5:
            tags.append("dense_speech")

        scene_count = _safe_float(row.get("scene_count"))
        if scene_count >= 8:
            tags.append("high_scene_count")

        if (row.get("transcription_skipped_reason") or "").strip():
            tags.append("no_transcript")

        return tags


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    haystack = f" {text.lower()} "
    return any(pattern in haystack for pattern in patterns)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", text.lower()) if token}


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _safe_float(value: str | float | int | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _format_float(value: float) -> str:
    return f"{value:.2f}"
