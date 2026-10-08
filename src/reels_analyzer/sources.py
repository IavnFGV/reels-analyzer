from __future__ import annotations

from pathlib import Path

from reels_analyzer.models import SourceVideoLink


class ManualLinksSource:
    """Current MVP source resolver.

    Automatic TikTok channel crawling is intentionally left outside the MVP because
    it often requires authentication, cookies, or channel-specific anti-bot handling.
    """

    def resolve(self, channel_name: str, links_file: Path) -> list[SourceVideoLink]:
        if not links_file.exists():
            raise FileNotFoundError(f"Links file does not exist: {links_file}")

        seen: set[str] = set()
        links: list[SourceVideoLink] = []

        with links_file.open("r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith(("http://", "https://")):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                links.append(SourceVideoLink(url=line, channel_name=channel_name))

        return links
