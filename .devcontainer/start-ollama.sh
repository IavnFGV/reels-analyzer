#!/usr/bin/env bash
set -euo pipefail

autostart="${OLLAMA_AUTOSTART:-1}"
case "${autostart,,}" in
  0|false|no)
    echo "Ollama autostart disabled; skipping startup."
    exit 0
    ;;
esac

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama binary not found; skipping startup."
  exit 0
fi

ensure_model() {
  model="${OLLAMA_PULL_MODEL:-qwen2.5:3b}"
  if [[ -z "${model}" ]]; then
    return 0
  fi
  if ollama show "${model}" >/dev/null 2>&1; then
    echo "Ollama model already present: ${model}"
  else
    echo "Pulling Ollama model: ${model}"
    ollama pull "${model}"
  fi
}

if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama already running."
  ensure_model
  exit 0
fi

nohup ollama serve >/tmp/ollama.log 2>&1 </dev/null &
pid="$!"
echo "Starting Ollama server on http://127.0.0.1:11434 (pid: ${pid}, log: /tmp/ollama.log)..."

ready=0
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama is ready."
    ready=1
    break
  fi
  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    echo "Ollama process exited during startup. Check /tmp/ollama.log."
    exit 1
  fi
  sleep 0.5
done

if [[ "${ready}" -ne 1 ]]; then
  echo "Ollama did not become ready in time. Check /tmp/ollama.log."
  exit 1
fi

ensure_model
