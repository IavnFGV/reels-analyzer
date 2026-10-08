#!/usr/bin/env python3
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECTS_DIR = REPO_ROOT / "projects"


def ask_text(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_yes_no(prompt: str, default: bool) -> bool:
    marker = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{marker}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Type y or n.")


def ask_choice(prompt: str, options: list[tuple[str, str]], default_key: str) -> str:
    print(prompt)
    for key, label in options:
        default_marker = " (default)" if key == default_key else ""
        print(f"  {key}: {label}{default_marker}")
    valid = {key for key, _ in options}
    while True:
        value = input("> ").strip().lower() or default_key
        if value in valid:
            return value
        print(f"Choose one of: {', '.join(sorted(valid))}")


def build_command() -> list[str]:
    channel = ask_text("Channel name", "example-channel")
    projects_dir = Path(ask_text("Projects dir", str(DEFAULT_PROJECTS_DIR))).expanduser()
    project_dir = projects_dir / channel

    source_mode = ask_choice(
        "What should the run use as the main source?",
        [
            ("1", "Existing local videos/audio from project/videos"),
            ("2", "Links file, metadata only from TikTok"),
            ("3", "Links file, download media from TikTok"),
        ],
        default_key="2",
    )

    links_file_default = str(project_dir / "inputs" / "links.txt")
    links_file = ""
    if source_mode in {"2", "3"}:
        links_file = ask_text("Links file path", links_file_default)

    analyze_video = ask_yes_no("Run scene analysis", default=False)
    transcribe_audio = ask_yes_no("Run Whisper transcription", default=True)
    classify_text = False
    if transcribe_audio:
        classify_text = ask_yes_no("Run Ollama text classification", default=False)

    whisper_model = "base"
    if transcribe_audio:
        whisper_model = ask_text("Whisper model", "medium")

    ollama_model = "qwen2.5:3b"
    if classify_text:
        ollama_model = ask_text("Ollama model", "qwen2.5:3b")

    log_level = ask_text("Log level", "INFO")

    command = [
        "reels-analyzer",
        "run",
        "--channel",
        channel,
        "--projects-dir",
        str(projects_dir),
        "--log-level",
        log_level,
    ]

    if source_mode == "1":
        command.append("--use-existing-videos")
    else:
        command.extend(["--links-file", links_file])
        if source_mode == "2":
            command.append("--no-download-media")

    if analyze_video:
        command.append("--analyze-video")
    if transcribe_audio:
        command.extend(["--transcribe-audio", "--whisper-model", whisper_model])
    if classify_text:
        command.extend(["--classify-text", "--ollama-model", ollama_model])

    return command


def main() -> None:
    print("Reels Analyzer Run Wizard")
    print("This helper asks simple questions and builds a run command.")
    command = build_command()
    pretty = " ".join(shlex.quote(part) for part in command)

    print("\nCommand:")
    print(pretty)

    if ask_yes_no("Run this command now", default=True):
        subprocess.run(command, check=True, cwd=REPO_ROOT)


if __name__ == "__main__":
    main()
