# Reels Analyzer

`reels-analyzer` is a Python CLI for collecting short-form video data into a project workspace and optionally enriching it with heavier analysis stages.

Current MVP:

- accept a channel name and a manually prepared file with video links;
- download videos and metadata with `yt-dlp`;
- export a normalized CSV report for further analysis;
- optionally run scene detection, Whisper transcription, and Ollama-based text classification.

Full transcript text is stored in separate files under `reports/transcripts/`.
Main CSV keeps `transcript_file_path` plus compact metrics (`first_phrase`, `word_count`, `words_per_second`).
It also stores derived performance and hook-analysis fields such as
`performance_score`, `performance_bucket`, `hook_subject`, `hook_format`,
`hook_emotion`, `hook_specificity`, `hook_strength_score`, `topic_cluster`,
and `insight_tags`.
Derived logic is documented in [docs/derived-insights.md](docs/derived-insights.md).

If `--links-file` is omitted, the CLI attempts to resolve TikTok video links by channel.
This can require authentication or cookies and is not guaranteed to work for every channel.
You can always supply a manually prepared links file instead.

As a separate helper, you can also resolve
links by TikTok channel into `links.txt` via `scripts/resolve-tiktok-channel.py`.
Detailed notes: [docs/tiktok-channel-resolver.md](docs/tiktok-channel-resolver.md).

## Clone on another computer

Python 3.11+ is required. From a terminal on the other computer:

```bash
git clone https://github.com/IavnFGV/reels-analyzer.git
cd reels-analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[video,transcription,llm]'
reels-analyzer --help
```

On Windows, create the environment with `py -m venv .venv` and activate it with
`.venv\Scripts\Activate.ps1` in PowerShell. Install `ffmpeg`/`ffprobe` separately
for audio extraction, and Ollama only if text classification is needed.
Alternatively, use the VS Code devcontainer described below.

Downloaded videos, reports, transcripts, caches, and model weights are not
transferred through Git. Copy any existing `projects/` data separately if needed.
Examples use placeholder channel names; replace them with your own channel.
Keep cookies and credentials out of Git, even when using custom file names.

## Project layout

After a run, each channel gets its own project folder:

```text
projects/
  my-channel/
    inputs/links.txt
    videos/
    cache/
      audio/
    reports/
      videos.csv
      ai_reviews.csv
      transcripts/
    downloaded.txt
```

## Installation

Base install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For full pipeline (video analysis + transcription + Ollama classification):

```bash
pip install -e '.[video,transcription,llm]'
```

For Jupyter reporting/dashboard work:

```bash
pip install -e '.[reporting]'
```

Then check the CLI:

```bash
reels-analyzer --help
```

Optional feature installs:

```bash
./scripts/install-extras.sh video
./scripts/install-extras.sh transcription
./scripts/install-extras.sh llm
./scripts/install-extras.sh reporting
```

If you want all runtime extras:

```bash
./scripts/install-extras.sh all
```

System tools:

- `ffmpeg` and `ffprobe` are required for audio extraction;
- Ollama must be available separately if `--classify-text` is enabled.

## Devcontainer

If you work in VS Code, the simplest flow is through the devcontainer.

1. Open the repository folder in VS Code.
2. Make sure the `Dev Containers` extension is installed.
   Docker must be running. With the current bind mounts, create the host state
   directories before opening the container: `mkdir -p ~/.ollama ~/.codex`
   (PowerShell: `New-Item -ItemType Directory -Force ~/.ollama, ~/.codex`).
3. Run `Dev Containers: Reopen in Container` from the command palette.
4. Wait until the container is built and initialized.

The image installs the dependencies during build; container creation then runs
an editable install of the actual workspace code without reinstalling dependencies:

```bash
pip install -e . --no-deps
```

Ollama is also installed in the container image, and `ollama serve` starts automatically
on container start (`http://127.0.0.1:11434`).
Default profile is CPU-only.

### Optional GPU profile (NVIDIA)

CPU remains the default for everyone. To opt in to GPU:

```bash
./scripts/switch-devcontainer-profile.sh gpu
```

Then rebuild container in VS Code (`Dev Containers: Rebuild Container`).

To switch back to CPU profile:

```bash
./scripts/switch-devcontainer-profile.sh cpu
```

GPU profile enables:
- `ghcr.io/devcontainers/features/nvidia-cuda:1`;
- Docker run args `--gpus all`.

Host prerequisites (outside container):
- NVIDIA driver installed on host OS;
- NVIDIA Container Toolkit configured for Docker.

Ubuntu 24.04 host setup:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Quick host check before rebuild:

```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

GPU profile now runs a host preflight before container startup and fails early if:
- `nvidia-smi` is unavailable on the host;
- Docker daemon is unavailable;
- Docker does not expose the `nvidia` runtime.

Check inside devcontainer after rebuild:

```bash
ollama ps
```

After the container opens, check the CLI:

```bash
reels-analyzer --help
```

Check Ollama and pull a model once:

```bash
ollama --version
ollama pull qwen2.5:3b
```

Base run inside the container:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./projects/example-channel/inputs/links.txt
```

Optional runtime extras are installed manually:

```bash
./scripts/install-extras.sh video
./scripts/install-extras.sh transcription
./scripts/install-extras.sh llm
```

Example full run:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./projects/example-channel/inputs/links.txt \
  --analyze-video \
  --transcribe-audio \
  --classify-text
```

If your chat session disappears after reopening in the container, use the prompt template from [docs/continue-from-container.md](docs/continue-from-container.md).

## Reporting Notebook

Local reporting notebooks can compare channels and publication dynamics.
Notebooks under `projects/` are private working artifacts, ignored by Git,
and are not included in a fresh clone.

They read current normalized files:

- `projects/<channel>/reports/videos.csv`
- `projects/<channel>/reports/ai_reviews.csv`

and can provide filters by channel, time range, `content_type`, `hook_type`, `tone`, `pace_label`, plus charts for:

- posts per day;
- views over time;
- posting intensity vs rolling average views;
- daily posting volume vs average views;
- breakdown by content type / hook / tone / pace.

`videos.csv` now also includes derived analysis columns for cohort-normalized
performance and hook heuristics:

- `performance_cohort`, `performance_baseline_view_count`, `performance_score`, `performance_bucket`
- `hook_subject`, `hook_format`, `hook_emotion`, `hook_specificity`, `hook_strength_score`
- `topic_cluster`, `insight_tags`

## Usage

Prepare a text file with one video URL per line:

```text
https://www.tiktok.com/@example/video/123
https://www.tiktok.com/@example/video/456
```

Base run:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./links.txt
```

Logging controls:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./links.txt \
  --log-level DEBUG \
  --log-file ./projects/example-channel/reports/run.log
```

Run without `--links-file` (auto-resolve by channel and save to `projects/<channel>/inputs/links.txt`):

```bash
reels-analyzer run \
  --channel example \
  --resolve-limit 200
```

With cookies for channel resolving:

```bash
reels-analyzer run \
  --channel example \
  --resolve-cookies-from-browser chrome
```

Without package install:

```bash
PYTHONPATH=src ./venv/bin/python -m reels_analyzer run \
  --channel example-channel \
  --links-file ./links.txt
```

Via `Makefile`:

```bash
make run CHANNEL=example-channel LINKS=./links.txt
```

`LINKS` is optional now. If omitted, `run` auto-resolves channel links:

```bash
make run CHANNEL=example FLAGS="--resolve-limit 100"
```

Inside the devcontainer, `dev`, `video`, `transcription`, `llm`, and `reporting`
dependencies are already installed in the image. Outside it, install only the
extras you need with `pip install -e '.[...]'` or `./scripts/install-extras.sh ...`.

Metadata-only inspection without downloading media:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./links.txt \
  --no-download-media
```

In this mode, videos are not downloaded, but `yt-dlp` still writes `*.info.json`
metadata files to the project `videos/` directory.

Resume analysis from already downloaded files (skip `yt-dlp` stage):

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./projects/example-channel/inputs/links.txt \
  --use-existing-videos \
  --analyze-video \
  --transcribe-audio \
  --classify-text
```

If `reports/videos.csv` already exists, new run updates matching rows (by `video_id`)
and keeps unrelated existing rows in the report.
After each `run`, the pipeline also recalculates derived report-level insights
for the full `videos.csv`.

Recalculate derived insights for an existing report without re-running download,
scene detection, transcription, or Ollama classification:

```bash
reels-analyzer analyze-report \
  --channel example-channel
```

This is useful when:

- you changed hook/performance heuristics in code;
- only part of the channel has full base analysis, but you still want refreshed report-level insights;
- you want to backfill new derived columns into an older `reports/videos.csv`.

Derived field semantics, matching rules, and thresholds are documented in
[docs/derived-insights.md](docs/derived-insights.md).

Current limitation:

- TikTok `comment_count` is collected from metadata, but a separate PoC with `yt-dlp`
  did not yield comment bodies for TikTok videos, even with valid cookies. For now,
  the project should treat TikTok comments as count-only metadata unless a different
  collection method is added later.

Enable scene analysis:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./links.txt \
  --analyze-video
```

Enable transcription:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./links.txt \
  --transcribe-audio
```

Whisper model options (`--whisper-model`):

```text
tiny, tiny.en
base, base.en
small, small.en
medium, medium.en
large-v1, large-v2, large-v3
distil-large-v3
```

Notes:
- For Russian and mixed-language content, prefer multilingual models (without `.en`).
- Good speed/quality tradeoff in CPU-only environments is usually `small` or `medium`.

Enable full text pipeline:

```bash
reels-analyzer run \
  --channel example-channel \
  --links-file ./links.txt \
  --transcribe-audio \
  --classify-text
```

Classification taxonomy (normalized values):

```text
content_type:
  no_audio, educational, instruction, text_led, short_form, vlog, social, generic_video, other

hook_type:
  emotional, call_to_action, question, curiosity, informational, problem_solution, neutral, unknown

tone:
  neutral, positive, negative, mixed, urgent, calm, dramatic, friendly, authoritative, mystical,
  energetic, empathetic, unknown
```

If Ollama returns out-of-taxonomy labels, the pipeline normalizes them to the nearest known category
or falls back (`other`/`unknown`) and writes a warning in logs.

When `--classify-text` is enabled, AI results are also written to a dedicated file:
`reports/ai_reviews.csv` (keyed by `video_id` + `ollama_model`).

Resolve links by channel (standalone step):

```bash
python scripts/resolve-tiktok-channel.py \
  --channel @example \
  --output projects/example/inputs/links.txt
```

With browser cookies (if channel content needs authentication):

```bash
python scripts/resolve-tiktok-channel.py \
  --channel @example \
  --output projects/example/inputs/links.txt \
  --cookies-from-browser chrome
```

Then run existing pipeline as usual:

```bash
reels-analyzer run --channel example --links-file projects/example/inputs/links.txt
```

## Reuse analysis in another Python project

The analysis helpers can be imported without downloading videos or running the
channel pipeline. Install from a local clone (editable) or from GitHub:

```bash
pip install -e '/path/to/reels-analyzer[video,transcription,llm]'
# Or install the published version:
pip install 'reels-analyzer[video,transcription,llm] @ git+https://github.com/IavnFGV/reels-analyzer.git@main'
```

For reproducible builds, replace `main` with a specific commit or tag.
See [docs/reusing-analysis.md](docs/reusing-analysis.md) for a local-file example.
These are Python helpers, not a hosted API or a browser-extension interface.

## Architecture

The code is separated by responsibility:

- `reels_analyzer.sources`: input link resolvers;
- `reels_analyzer.downloader`: `yt-dlp` integration;
- `reels_analyzer.media`: scene detection and transcription helpers;
- `reels_analyzer.reviewer`: Ollama classification;
- `reels_analyzer.pipeline`: orchestration;
- `reels_analyzer.writer`: CSV export.

This separates link collection from analysis and leaves room for richer report
formats or asynchronous processing.
