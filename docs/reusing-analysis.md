# Reusing Video Analysis

The existing helpers in `reels_analyzer.media` work with local files and do not
need TikTok links, a channel name, or `ChannelPipeline`.

Install the `video`, `transcription`, and `llm` extras, plus system `ffmpeg` and
`ffprobe`. Ollama is only needed for the optional text review. Whisper runs on
CPU and may download its model on first use.

```python
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from reels_analyzer.media import AudioPreprocessor, SceneDetector, WhisperTranscriber
from reels_analyzer.models import TranscriptionResult
from reels_analyzer.reviewer import OllamaReviewer

video_path = Path("input.mp4")
probe = subprocess.run(
    [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(video_path),
    ],
    capture_output=True,
    text=True,
    check=True,
)
duration = float(json.loads(probe.stdout)["format"]["duration"])

scenes = SceneDetector().analyze(video_path, duration_sec=duration)
audio = AudioPreprocessor().extract_wav(video_path, output_dir=Path("cache/audio"))
transcript = (
    WhisperTranscriber(model_size="base").transcribe(audio, duration_sec=duration)
    if audio is not None
    else TranscriptionResult(skipped_reason="no_audio_stream")
)

# Optional: requires a running Ollama server with this model available.
review = OllamaReviewer(
    model="qwen2.5:3b",
    base_url="http://localhost:11434/api/chat",
).review(
    transcript=transcript.transcript,
    first_phrase=transcript.first_phrase,
    duration_sec=duration,
    scene_count=scenes.scene_count,
    pace=scenes.pace_label,
)

result = {
    "scenes": asdict(scenes),
    "transcription": asdict(transcript),
    "review": asdict(review),
}
print(json.dumps(result, ensure_ascii=False, indent=2))
```

For multiple videos, initialize `SceneDetector`, `WhisperTranscriber`, and
`OllamaReviewer` once and reuse them. Loading Whisper for each file is expensive.
Use a separate cache directory per video when files can have the same stem:
audio caching currently uses the video file stem as the WAV filename.

`duration_sec` should be the real video duration, because it affects scene-length
and speech-rate metrics. Text review classifies the transcript; it does not
inspect images with a vision model.

A browser extension cannot import these Python classes directly. In that case,
the other project needs a Python backend or local process to call them. This
repository does not currently provide an HTTP API.
