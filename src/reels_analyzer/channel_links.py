from __future__ import annotations

from pathlib import Path

from reels_analyzer.dependencies import require_python_package


def normalize_channel_url(value: str) -> str:
    raw = value.strip()
    if raw.startswith(("http://", "https://")):
        return raw
    handle = raw if raw.startswith("@") else f"@{raw}"
    return f"https://www.tiktok.com/{handle}"


def resolve_channel_links(
    channel_url: str,
    limit: int = 0,
    cookies_from_browser: str = "",
    cookies_file: Path | None = None,
) -> list[str]:
    require_python_package("yt_dlp", "download-media")

    import yt_dlp

    ydl_opts: dict[str, object] = {
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": limit if limit > 0 else None,
        "noplaylist": False,
        "quiet": False,
    }

    cookies_from_browser = cookies_from_browser.strip()
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    elif cookies_file is not None:
        ydl_opts["cookiefile"] = str(cookies_file)

    links: list[str] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(channel_url, download=False)
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return links

        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            candidate = entry.get("webpage_url") or entry.get("url") or entry.get("original_url")
            if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                if candidate not in seen:
                    seen.add(candidate)
                    links.append(candidate)
    return links


def save_links_file(output: Path, links: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(links)
    if links:
        payload += "\n"
    output.write_text(payload, encoding="utf-8")
