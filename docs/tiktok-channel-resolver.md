# TikTok Channel Resolver (Standalone)

This helper resolves TikTok video links by channel and writes them to `links.txt`.
The same resolver is used by `reels-analyzer run` when `--links-file` is omitted.

## Basic usage

```bash
python scripts/resolve-tiktok-channel.py \
  --channel @example \
  --output projects/example/inputs/links.txt
```

You can also pass just the handle without `@`:

```bash
python scripts/resolve-tiktok-channel.py \
  --channel example \
  --output projects/example/inputs/links.txt
```

## Authenticated/private access

For channels/videos that require login, pass cookies from your browser:

```bash
python scripts/resolve-tiktok-channel.py \
  --channel @example \
  --output projects/example/inputs/links.txt \
  --cookies-from-browser chrome
```

Or use an exported cookies file:

```bash
python scripts/resolve-tiktok-channel.py \
  --channel @example \
  --output projects/example/inputs/links.txt \
  --cookies-file /path/to/cookies.txt
```

## Limit for quick checks

```bash
python scripts/resolve-tiktok-channel.py \
  --channel @example \
  --output /tmp/links_test.txt \
  --limit 10
```
