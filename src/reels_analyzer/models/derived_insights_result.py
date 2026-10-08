from dataclasses import dataclass


@dataclass(slots=True)
class DerivedInsightsResult:
    performance_cohort: str = ""
    performance_baseline_view_count: float = 0.0
    performance_score: float = 0.0
    performance_bucket: str = "unknown"
    hook_subject: str = "unknown"
    hook_format: str = "unknown"
    hook_emotion: str = "unknown"
    hook_specificity: str = "unknown"
    hook_strength_score: int = 0
    topic_cluster: str = "unknown"
    insight_tags: list[str] | None = None

    def normalized_tags(self) -> list[str]:
        return self.insight_tags or []
