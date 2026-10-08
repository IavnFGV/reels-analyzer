from dataclasses import dataclass, field


@dataclass(slots=True)
class SceneAnalysisResult:
    scene_count: int = 0
    avg_scene_length_sec: float = 0.0
    pace_label: str = "not_run"
    scenes: list[tuple[float, float]] = field(default_factory=list)
    skipped_reason: str | None = None
