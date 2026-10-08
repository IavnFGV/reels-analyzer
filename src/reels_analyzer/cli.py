from __future__ import annotations

import logging
from pathlib import Path

import typer

from reels_analyzer.channel_links import (
    normalize_channel_url,
    resolve_channel_links,
    save_links_file,
)
from reels_analyzer.config import FeatureFlags, ProjectLayout, RuntimeConfig
from reels_analyzer.insights import ChannelInsightsAnalyzer
from reels_analyzer.logging_utils import configure_logging
from reels_analyzer.pipeline import ChannelPipeline
from reels_analyzer.writer import CsvReportWriter

app = typer.Typer(
    help="TikTok/Reels download and analysis pipeline.",
    no_args_is_help=True,
)
logger = logging.getLogger(__name__)


@app.callback()
def callback() -> None:
    """CLI entrypoint."""


@app.command()
def run(
    channel: str = typer.Option(..., help="Channel label used for project folder naming."),
    links_file: Path | None = typer.Option(
        None,
        file_okay=True,
        dir_okay=False,
        help="Path to a manually prepared file with one video URL per line. Optional.",
    ),
    projects_dir: Path = typer.Option(
        Path("projects"),
        file_okay=False,
        dir_okay=True,
        help="Base directory where channel project folders will be created.",
    ),
    download_media: bool = typer.Option(
        True,
        "--download-media/--no-download-media",
        help="Download videos with yt-dlp. Disable for metadata-only inspection.",
    ),
    use_existing_videos: bool = typer.Option(
        False,
        "--use-existing-videos/--no-use-existing-videos",
        help="Load already downloaded files from project videos/ and skip yt-dlp.",
    ),
    analyze_video: bool = typer.Option(
        False,
        "--analyze-video/--no-analyze-video",
        help="Run optional scene analysis on downloaded videos.",
    ),
    transcribe_audio: bool = typer.Option(
        False,
        "--transcribe-audio/--no-transcribe-audio",
        help="Run optional Whisper transcription on downloaded videos.",
    ),
    classify_text: bool = typer.Option(
        False,
        "--classify-text/--no-classify-text",
        help="Run optional Ollama classification on the transcript.",
    ),
    whisper_model: str = typer.Option("base", help="Whisper model size for transcription."),
    ollama_model: str = typer.Option("qwen2.5:3b", help="Ollama model name."),
    ollama_base_url: str = typer.Option(
        "http://localhost:11434/api/chat",
        help="Ollama chat endpoint.",
    ),
    resolve_limit: int = typer.Option(
        0,
        min=0,
        help="Max videos to resolve from channel when --links-file is omitted (0 means no limit).",
    ),
    resolve_cookies_from_browser: str = typer.Option(
        "",
        help="Browser name for cookies import when resolving channel links (e.g. chrome, firefox).",
    ),
    resolve_cookies_file: Path | None = typer.Option(
        None,
        file_okay=True,
        dir_okay=False,
        help="Path to cookies file for channel link resolving.",
    ),
    log_level: str = typer.Option(
        "INFO",
        help="Logging level: DEBUG, INFO, WARNING, ERROR.",
    ),
    log_file: Path | None = typer.Option(
        None,
        file_okay=True,
        dir_okay=False,
        help="Optional path to write logs in addition to console output.",
    ),
) -> None:
    configure_logging(level=log_level, log_file=log_file)

    if classify_text and not transcribe_audio:
        raise typer.BadParameter("--classify-text requires --transcribe-audio.")

    project = ProjectLayout.from_channel(base_dir=projects_dir, channel_name=channel)
    if use_existing_videos and links_file is None:
        effective_links_file = project.links_snapshot_path
    else:
        effective_links_file = _resolve_links_file(
            links_file=links_file,
            channel=channel,
            output_path=project.links_snapshot_path,
            resolve_limit=resolve_limit,
            resolve_cookies_from_browser=resolve_cookies_from_browser,
            resolve_cookies_file=resolve_cookies_file,
        )

    config = RuntimeConfig(
        channel_name=channel,
        links_file=effective_links_file,
        project=project,
        features=FeatureFlags(
            download_media=download_media,
            use_existing_videos=use_existing_videos,
            analyze_video=analyze_video,
            transcribe_audio=transcribe_audio,
            classify_text=classify_text,
        ),
        whisper_model=whisper_model,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url,
    )

    records = ChannelPipeline(config).run()
    logger.info("Processed %s video(s).", len(records))
    logger.info("Results CSV: %s", config.project.results_csv_path)
    if classify_text:
        logger.info("AI Reviews CSV: %s", config.project.ai_reviews_csv_path)
    logger.info("Project folder: %s", config.project.root)
    typer.echo(f"Processed {len(records)} video(s).")
    typer.echo(f"Results CSV: {config.project.results_csv_path}")
    if classify_text:
        typer.echo(f"AI Reviews CSV: {config.project.ai_reviews_csv_path}")
    typer.echo(f"Project folder: {config.project.root}")


@app.command("analyze-report")
def analyze_report(
    channel: str = typer.Option(..., help="Channel label used for project folder naming."),
    projects_dir: Path = typer.Option(
        Path("projects"),
        file_okay=False,
        dir_okay=True,
        help="Base directory where channel project folders are stored.",
    ),
    log_level: str = typer.Option(
        "INFO",
        help="Logging level: DEBUG, INFO, WARNING, ERROR.",
    ),
    log_file: Path | None = typer.Option(
        None,
        file_okay=True,
        dir_okay=False,
        help="Optional path to write logs in addition to console output.",
    ),
) -> None:
    configure_logging(level=log_level, log_file=log_file)

    project = ProjectLayout.from_channel(base_dir=projects_dir, channel_name=channel)
    writer = CsvReportWriter()
    rows = writer.load_rows(project.results_csv_path)
    if not rows:
        raise typer.BadParameter(f"No rows found in report: {project.results_csv_path}")

    analyzer = ChannelInsightsAnalyzer()
    enriched_rows = analyzer.analyze_rows(rows)
    writer.write_rows(enriched_rows, project.results_csv_path)

    logger.info("Enriched report rows: %s", len(enriched_rows))
    typer.echo(f"Enriched {len(enriched_rows)} row(s): {project.results_csv_path}")


def _resolve_links_file(
    links_file: Path | None,
    channel: str,
    output_path: Path,
    resolve_limit: int,
    resolve_cookies_from_browser: str,
    resolve_cookies_file: Path | None,
) -> Path:
    if links_file is not None:
        if not links_file.exists():
            raise typer.BadParameter(f"Links file does not exist: {links_file}")
        if not links_file.is_file():
            raise typer.BadParameter(f"Links file must be a file: {links_file}")
        return links_file

    channel_url = normalize_channel_url(channel)
    logger.info("--links-file is not provided, resolving links from %s", channel_url)
    try:
        links = resolve_channel_links(
            channel_url=channel_url,
            limit=resolve_limit,
            cookies_from_browser=resolve_cookies_from_browser,
            cookies_file=resolve_cookies_file,
        )
    except Exception as exc:
        raise typer.BadParameter(
            "Failed to resolve channel links. "
            "Try --links-file manually or pass cookies options."
        ) from exc
    if not links:
        raise typer.BadParameter(
            "Could not resolve any video links for this channel. "
            "Pass --links-file manually or provide cookies options."
        )
    save_links_file(output_path, links)
    logger.info("Resolved links file: %s (%s URL(s))", output_path, len(links))
    return output_path


def main() -> None:
    app()


if __name__ == "__main__":
    main()
