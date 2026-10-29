"""Pull a public Pinterest board into local pin images via the board's RSS feed (no login, no
Pinterest API). Pins land in data/boards/<user>/ and then go through the same sync_user path
as the demo boards.

    python -m visioncart.live.board quinn https://www.pinterest.com/quinnkingqk/mens-outfits/
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import re
import xml.etree.ElementTree as ET

import httpx

from visioncart import config

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
_IMG = re.compile(r'<img src="(https://i\.pinimg\.com/[^"]+)"')


def rss_url(board_url: str) -> str:
    return board_url.split("?")[0].rstrip("/") + ".rss"


def pin_image_urls(rss: str) -> list[str]:
    """Image urls in feed order, upgraded from the 236px thumbnail to the 736px rendition."""
    urls = []
    for item in ET.fromstring(rss).iter("item"):
        m = _IMG.search(html.unescape(item.findtext("description") or ""))
        if m:
            urls.append(re.sub(r"/\d+x/", "/736x/", m.group(1)))
    return urls


async def fetch_board(user_id: str, board_url: str) -> list[str]:
    """Download any new pins; return all pin paths (relative to ROOT) for the board."""
    out_dir = config.BOARDS_DIR / user_id
    out_dir.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        feed = await client.get(rss_url(board_url))
        feed.raise_for_status()
        urls = pin_image_urls(feed.text)

        async def one(url: str) -> str:
            path = out_dir / f"{hashlib.sha1(url.encode()).hexdigest()[:12]}.jpg"
            if not path.exists():
                r = await client.get(url)
                r.raise_for_status()
                path.write_bytes(r.content)
            return str(path.relative_to(config.ROOT))

        return list(await asyncio.gather(*[one(u) for u in urls]))


def board_pins(user_id: str) -> list[str]:
    """Pins already on disk, without touching the network."""
    return sorted(str(p.relative_to(config.ROOT)) for p in (config.BOARDS_DIR / user_id).glob("*.jpg"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("board_url")
    args = ap.parse_args()
    pins = asyncio.run(fetch_board(args.user, args.board_url))
    print(f"{len(pins)} pins in {config.BOARDS_DIR / args.user}")
