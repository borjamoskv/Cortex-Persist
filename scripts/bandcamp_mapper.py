#!/usr/bin/env python3
"""Bandcamp artist/label mapper — async scraper with structured output.

Reads URLs from bandcamp_urls.txt, extracts band metadata via Bandcamp's
internal API, and outputs a JSON mapping with contact info, location,
discography counts, and label detection.

Usage:
    python scripts/bandcamp_mapper.py [--concurrency N] [--output FILE]
"""

from __future__ import annotations

import argparse
import asyncio
import html as html_module
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# ─── Constants ────────────────────────────────────────────────────────

URLS_FILE = Path(__file__).parent / "bandcamp_urls.txt"
DEFAULT_OUTPUT = Path(__file__).parent / "bandcamp_map.json"
API_ENDPOINT = "https://bandcamp.com/api/mobile/24/band_details"
DEFAULT_CONCURRENCY = 5
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds, exponential backoff
REQUEST_TIMEOUT = 15.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

EMAIL_BLACKLIST = frozenset(
    {
        "sentry",
        "example.com",
        "bandcamp.com",
        "schema.org",
        "w3.org",
        "googleapis",
        "ingest.us",
        "noreply",
        "github.com",
        "wixpress",
        "cloudflare",
        "webpack",
    }
)

LABEL_KEYWORDS = frozenset({"records", "recordings", "label", "musik", "audio"})

log = logging.getLogger("bandcamp_mapper")


# ─── URL Loading ──────────────────────────────────────────────────────


def load_urls(path: Path = URLS_FILE) -> list[str]:
    """Load and deduplicate URLs from external file."""
    if not path.exists():
        log.error("URL file not found: %s", path)
        sys.exit(1)

    seen: set[str] = set()
    unique: list[str] = []
    for line in path.read_text().splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        normalized = url.lower().rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            unique.append(url)

    log.info("Loaded %d unique URLs from %s", len(unique), path.name)
    return unique


# ─── HTTP Helpers ─────────────────────────────────────────────────────


async def fetch_html(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[int, str]:
    """GET a URL and return (status_code, body). Retries on transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            return resp.status_code, resp.text
        except httpx.TimeoutException:
            log.warning("Timeout fetching %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
        except httpx.HTTPError as exc:
            log.warning(
                "HTTP error fetching %s: %s (attempt %d/%d)",
                url,
                exc,
                attempt,
                MAX_RETRIES,
            )

        if attempt < MAX_RETRIES:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

    return 0, ""


async def fetch_band_details(
    client: httpx.AsyncClient,
    band_id: int,
) -> dict[str, Any] | None:
    """POST to Bandcamp API for band details. Retries on transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.post(
                API_ENDPOINT,
                json={"band_id": band_id},
                headers={"User-Agent": HEADERS["User-Agent"]},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            log.warning(
                "API returned %d for band_id=%d (attempt %d/%d)",
                resp.status_code,
                band_id,
                attempt,
                MAX_RETRIES,
            )
        except httpx.TimeoutException:
            log.warning(
                "API timeout for band_id=%d (attempt %d/%d)",
                band_id,
                attempt,
                MAX_RETRIES,
            )
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            log.warning(
                "API error for band_id=%d: %s (attempt %d/%d)",
                band_id,
                exc,
                attempt,
                MAX_RETRIES,
            )

        if attempt < MAX_RETRIES:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

    return None


# ─── Parsing ──────────────────────────────────────────────────────────


def extract_band_id(body: str) -> int | None:
    """Extract band_id from Bandcamp page HTML using multiple strategies."""
    # Strategy 1: data-band JSON attribute
    m = re.search(r'data-band="([^"]+)"', body)
    if m:
        decoded = html_module.unescape(m.group(1))
        try:
            data = json.loads(decoded)
            band_id = data.get("id")
            if isinstance(band_id, int):
                return band_id
        except json.JSONDecodeError:
            pass
        # Fallback: regex inside decoded attribute
        m2 = re.search(r'"id"\s*:\s*(\d+)', decoded)
        if m2:
            return int(m2.group(1))

    # Strategy 2: HTML-encoded JSON
    m = re.search(r"&quot;id&quot;:(\d+)", body)
    if m:
        return int(m.group(1))

    # Strategy 3: band_id in raw JSON
    m = re.search(r'"band_id"\s*:\s*(\d+)', body)
    if m:
        return int(m.group(1))

    return None


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def extract_emails(text: str) -> list[str]:
    """Extract emails from text, filtering known noise domains."""
    emails = _EMAIL_RE.findall(text)
    return list({e for e in emails if not any(bl in e.lower() for bl in EMAIL_BLACKLIST)})


def detect_label(name: str | None, has_artists: bool) -> bool:
    """Heuristic: is this Bandcamp page a label rather than an artist?"""
    if has_artists:
        return True
    if name:
        name_lower = name.lower()
        return any(kw in name_lower for kw in LABEL_KEYWORDS)
    return False


# ─── Core Processing ─────────────────────────────────────────────────


async def process_url(
    client: httpx.AsyncClient,
    url: str,
    idx: int,
    total: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """Scrape a single Bandcamp URL and return structured metadata."""
    slug = url.replace("https://", "").replace(".bandcamp.com", "").rstrip("/")
    result: dict[str, Any] = {
        "url": url,
        "slug": slug,
        "name": None,
        "band_id": None,
        "location": None,
        "bio": None,
        "sites": [],
        "emails": [],
        "status": "unknown",
        "is_label": False,
        "discography_count": 0,
    }

    async with semaphore:
        status_code, body = await fetch_html(client, url)

    if status_code == 404 or "doesn't exist" in body:
        result["status"] = "not_found"
        log.info("[%d/%d] ❌ %s — not found", idx, total, slug)
        return result

    if status_code != 200:
        result["status"] = f"http_{status_code}"
        log.warning("[%d/%d] ⚠️  %s — HTTP %d", idx, total, slug, status_code)
        return result

    band_id = extract_band_id(body)
    if not band_id:
        result["status"] = "no_band_id"
        log.info("[%d/%d] 🔍 %s — no band_id found", idx, total, slug)
        return result

    result["band_id"] = band_id
    result["emails"] = extract_emails(body)

    # Rate-limit API calls
    async with semaphore:
        details = await fetch_band_details(client, band_id)

    if not details:
        result["status"] = "api_error"
        log.warning("[%d/%d] 🔌 %s — API error", idx, total, slug)
        return result

    result["status"] = "ok"
    result["name"] = details.get("name")
    result["location"] = details.get("location")
    bio = details.get("bio") or ""
    result["bio"] = bio[:500] if bio else None
    result["sites"] = [
        {"url": s.get("url", ""), "title": s.get("title", "")} for s in details.get("sites", [])
    ]
    result["discography_count"] = len(details.get("discography", []))
    result["is_label"] = detect_label(
        result["name"],
        bool(details.get("artists")),
    )

    log.info(
        "[%d/%d] ✅ %s — %s (%s, %d releases)",
        idx,
        total,
        slug,
        result["name"],
        result["location"] or "??",
        result["discography_count"],
    )
    return result


# ─── Orchestrator ─────────────────────────────────────────────────────


async def run(concurrency: int, output_path: Path) -> None:
    """Main async orchestrator — process all URLs with bounded concurrency."""
    urls = load_urls()
    total = len(urls)
    semaphore = asyncio.Semaphore(concurrency)

    log.info("Starting Bandcamp mapper: %d URLs, concurrency=%d", total, concurrency)
    t0 = time.monotonic()

    async with httpx.AsyncClient(
        follow_redirects=True,
        http2=True,
    ) as client:
        tasks = [
            process_url(client, url, idx + 1, total, semaphore) for idx, url in enumerate(urls)
        ]
        results = await asyncio.gather(*tasks)

    elapsed = time.monotonic() - t0

    # ── Summary stats ──
    stats: dict[str, int] = {}
    for r in results:
        status = r["status"]
        stats[status] = stats.get(status, 0) + 1

    output_path.write_text(json.dumps(list(results), indent=2, ensure_ascii=False))

    log.info("━" * 60)
    log.info("Completed in %.1fs — %d URLs processed", elapsed, total)
    for status, count in sorted(stats.items(), key=lambda x: -x[1]):
        log.info("  %-15s %d", status, count)
    log.info("Output: %s", output_path)


# ─── Entry Point ──────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Bandcamp artist/label mapper — async scraper",
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent requests (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON file (default: {DEFAULT_OUTPUT.name})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    asyncio.run(run(args.concurrency, args.output))


if __name__ == "__main__":
    main()
