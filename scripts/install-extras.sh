#!/usr/bin/env bash

set -euo pipefail

if [[ $# -eq 0 ]]; then
  cat <<'EOF'
Usage:
  ./scripts/install-extras.sh video
  ./scripts/install-extras.sh transcription
  ./scripts/install-extras.sh llm
  ./scripts/install-extras.sh reporting
  ./scripts/install-extras.sh all

Available extras:
  video           Install scene detection dependencies
  transcription   Install Whisper transcription dependencies
  llm             Install Ollama client dependencies
  reporting       Install Jupyter/reporting dependencies
  all             Install all optional dependencies
EOF
  exit 1
fi


  PIP="pip"

case "${1}" in
  video)
    "${PIP}" install -e ".[video]"
    ;;
  transcription)
    "${PIP}" install -e ".[transcription]"
    ;;
  llm)
    "${PIP}" install -e ".[llm]"
    ;;
  reporting)
    "${PIP}" install -e ".[reporting]"
    ;;
  all)
    "${PIP}" install -e ".[video,transcription,llm,reporting]"
    ;;
  *)
    echo "Unknown extra: ${1}" >&2
    exit 1
    ;;
esac
