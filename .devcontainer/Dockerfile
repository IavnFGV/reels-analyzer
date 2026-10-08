FROM mcr.microsoft.com/devcontainers/python:3-bookworm

WORKDIR /tmp/reels-analyzer-build

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg zstd \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

RUN mkdir -p src/reels_analyzer \
    && touch src/reels_analyzer/__init__.py

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install '.[dev,video,transcription,llm,reporting]'
