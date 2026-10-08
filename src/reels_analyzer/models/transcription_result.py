from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptionResult:
    transcript: str = ""
    first_phrase: str = ""
    word_count: int = 0
    words_per_second: float = 0.0
    skipped_reason: str | None = None
