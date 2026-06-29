# [C5-REAL] Exergy-Maximized
import base64
import hashlib
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from babylon60.crypto.hash_registry import cortex_hash_raw


# Cache previously fetched SRI hashes to avoid entropy
@lru_cache(maxsize=128)
def generate_sri_hash(url: str, algo: str = "sha384") -> str:
    """Fetch external resource and generate SRI integrity hash. (Protected by SRI-HASH-OMEGA Whitelist)"""
    trusted_domains = {
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "unpkg.com",
        "fonts.googleapis.com",
        "ajax.googleapis.com",
        "code.jquery.com",
    }

    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)

        # Alert #63 (SSRF & Untrusted Inclusion): Reject non-whitelisted domains
        if parsed.hostname not in trusted_domains:
            return ""

        from babylon60.guards.url_guard import is_safe_url

        if not is_safe_url(url):
            return ""

        req = urllib.request.Request(url, headers={"User-Agent": "CORTEX-Persist/SRI-Engine"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read()

            if algo == "sha256":
                digest = cortex_hash_raw(data)
            elif algo == "sha512":
                digest = hashlib.sha512(data).digest()
            else:
                algo = "sha384"
                digest = hashlib.sha384(data).digest()

            b64_hash = base64.b64encode(digest).decode("utf-8")
            return f"{algo}-{b64_hash}"
    except (urllib.error.URLError, ValueError, TimeoutError):
        # If fetch fails, we return an empty string. The sanitizer can decide whether to block or allow
        return ""


def auto_heal_html(html_payload: str) -> str:
    """
    Scans an HTML payload for external scripts and links without integrity hashes.
    Downloads them, computes the SRI hash, and injects the integrity and crossorigin attributes.
    """
    # Find all script tags with a src attribute
    script_pattern = re.compile(
        r'(<script[^>]+src=["\'](https?://[^"\']+)["\'][^>]*>)', re.IGNORECASE
    )
    # Find all link tags with href returning stylesheets
    link_pattern = re.compile(r'(<link[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>)', re.IGNORECASE)

    healed_payload = html_payload

    def process_tag(tag_match):
        full_tag = tag_match.group(1)
        url = tag_match.group(2)

        # Check if already has integrity
        if "integrity=" in full_tag.lower():
            return full_tag

        sri = generate_sri_hash(url)
        if not sri:
            # If we couldn't fetch the remote asset, we do not inject the integrity.
            # Or perhaps we should raise an error? For now, we leave as is.
            return full_tag

        # Inject integrity + crossorigin
        new_tag = full_tag.replace(">", f' integrity="{sri}" crossorigin="anonymous">')
        return new_tag

    # Use ThreadPoolExecutor to resolve all URLs in parallel if needed,
    # but re.sub takes a callable, so we just run it linearly.
    # The lru_cache handles deduplication. For massive html we might need pre-fetching.

    # Pre-fetch URls to utilize ThreadPool
    urls_to_fetch = set()
    for match in script_pattern.finditer(html_payload):
        if "integrity=" not in match.group(1).lower():
            urls_to_fetch.add(match.group(2))
    for match in link_pattern.finditer(html_payload):
        if "integrity=" not in match.group(1).lower():
            urls_to_fetch.add(match.group(2))

    with ThreadPoolExecutor(max_workers=5) as executor:
        # Prepopulate the cache concurrently
        list(executor.map(generate_sri_hash, urls_to_fetch))

    healed_payload = script_pattern.sub(process_tag, healed_payload)
    healed_payload = link_pattern.sub(process_tag, healed_payload)

    return healed_payload
