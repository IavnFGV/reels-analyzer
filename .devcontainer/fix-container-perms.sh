#!/usr/bin/env bash
set -euo pipefail

for dir in \
  /home/vscode/.cache \
  /home/vscode/.cache/pip \
  /home/vscode/.ollama \
  /home/vscode/.codex
do
  mkdir -p "${dir}"
done

if command -v sudo >/dev/null 2>&1; then
  sudo chown -R vscode:vscode \
    /home/vscode/.cache \
    /home/vscode/.ollama \
    /home/vscode/.codex
else
  chown -R vscode:vscode \
    /home/vscode/.cache \
    /home/vscode/.ollama \
    /home/vscode/.codex
fi

chmod 700 /home/vscode/.ollama || true
