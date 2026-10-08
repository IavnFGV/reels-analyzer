#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from reels_analyzer.channel_links import (
    normalize_channel_url,
    resolve_channel_links,
    save_links_file,
)
from reels_analyzer.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve TikTok channel videos into a plain links file. "
            "The CLI also resolves channel links when --links-file is omitted."
        )
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="TikTok handle (e.g. example or @example) or full channel URL.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output file path for links.txt.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of videos to resolve (0 = all available).",
    )
    parser.add_argument(
        "--cookies-from-browser",
        default="",
        help=(
            "Browser name for yt-dlp cookies import (for private/restricted pages). "
            "Example: chrome, firefox, edge, safari."
        ),
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        default=None,
        help="Path to Netscape-format cookies file. Used if --cookies-from-browser is not set.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level: DEBUG, INFO, WARNING, ERROR.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional path to write logs in addition to console output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(level=args.log_level, log_file=args.log_file)

    channel_url = normalize_channel_url(args.channel)
    links = resolve_channel_links(
        channel_url=channel_url,
        limit=args.limit,
        cookies_from_browser=args.cookies_from_browser.strip(),
        cookies_file=args.cookies_file,
    )
    save_links_file(args.output, links)
    logger.info("Resolved %s link(s) from %s", len(links), channel_url)
    logger.info("Saved links file: %s", args.output)


if __name__ == "__main__":
    main()
