from dataclasses import dataclass, field


@dataclass(slots=True)
class AIReviewResult:
    content_type: str = "not_run"
    hook_type: str = "not_run"
    tone: str = "not_run"
    summary: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    skipped_reason: str | None = None
