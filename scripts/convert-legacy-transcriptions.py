#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

import typer


app = typer.Typer(
    help="Convert legacy transcription.csv into reports/transcripts/<video_id>__<model>.txt files."
)


def _extract_video_id(file_name: str) -> str:
    matches = re.findall(r"(\d{18,20})", file_name or "")
    if not matches:
        raise ValueError(f"Could not extract video_id from file name: {file_name}")
    return matches[0]


@app.command()
def main(
    source_csv: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to legacy transcription.csv file.",
    ),
    output_dir: Path = typer.Argument(
        ...,
        file_okay=False,
        dir_okay=True,
        help="Target reports/transcripts directory.",
    ),
    model_name: str = typer.Option(
        "medium",
        "--model-name",
        help="Model suffix used in output file names.",
    ),
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    overwritten = 0

    with source_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            video_id = _extract_video_id(row.get("file_name", ""))
            transcript = (row.get("transcription") or "").strip()
            target = output_dir / f"{video_id}__{model_name}.txt"

            if target.exists():
                overwritten += 1
            else:
                created += 1

            target.write_text(transcript, encoding="utf-8")

    typer.echo(f"Output dir: {output_dir}")
    typer.echo(f"Created: {created}")
    typer.echo(f"Overwritten: {overwritten}")


if __name__ == "__main__":
    app()
