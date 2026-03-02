#!/usr/bin/env python3
"""
EU B2B Email Scraper v5.0 — MOSKV-1 Sovereign
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estrategia que funciona GARANTIZADO:

  MODO 1 (Recomendado): --domains domains.txt
    → Lee una lista de dominios EU → crawl directo → emails
    → Sin search engines, sin CAPTCHA, resultados perfectos

  MODO 2 (Con API key): --serpapi KEY --query "..."
    → SerpAPI (gratis: 100 searches/mes - https://serpapi.com)
    → Google results sin CAPTCHA

  MODO 3 (LinkedIn, Hunter): --hunter KEY --company "..."
    → Hunter.io API (50 búsquedas/mes gratis)
    → Email addresses directos por empresa

  MODO 4 (directorios EU hardcodeados):
    → Kompass, InfoBel con URLs directas
    → No necesita search engine

GDPR: Solo emails PÚBLICOS de contacto empresarial.

Usage:
  # Con lista de dominios (MODO MÁS EFECTIVO):
  python eu_email_scraper.py --domains companies_eu.txt

  # Con SerpAPI (100 gratis/mes):
  python eu_email_scraper.py --query "software Spain" --serpapi YOUR_KEY

  # Con Hunter.io (50 gratis/mes):
  python eu_email_scraper.py --company "nombre empresa" --domain empresa.es --hunter YOUR_KEY

  # Crawl directo de URLs:
  python eu_email_scraper.py --urls urls.txt
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("eu_scraper")

# ── Constants ─────────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}\b",
    re.IGNORECASE,
)

PUBLIC_PREFIXES = {
    "info", "contact", "contacto", "hello", "hola", "bonjour", "ciao",
    "kontakt", "sales", "ventas", "comercial", "trade", "export",
    "press", "media", "marketing", "support", "office", "admin",
    "general", "mail", "enquiries", "business", "partner",
    "hallo", "aloha", "olá", "witaj",
}

PRIORITY_PREFIXES = {"info", "contact", "contacto", "sales", "ventas", "hello", "hola"}

BLACKLIST_DOMAINS = {
    "example.com", "test.com", "sentry.io", "wixpress.com",
    "wordpress.com", "shopify.com", "gmail.com", "hotmail.com",
    "yahoo.com", "outlook.com", "protonmail.com", "icloud.com",
    "amazonaws.com", "cloudflare.com", "google.com", "facebook.com",
    "instagram.com", "twitter.com", "linkedin.com", "tiktok.com",
    "w3.org", "schema.org", "apple.com", "microsoft.com",
    "gravatar.com", "vimeo.com", "youtube.com",
}

BLACKLIST_PREFIXES = {
    "noreply", "no-reply", "donotreply", "bounce", "mailer",
    "daemon", "postmaster", "webmaster", "privacy", "gdpr",
}

EU_TLDS = {
    ".de", ".es", ".fr", ".it", ".nl", ".pl", ".se", ".be",
    ".at", ".pt", ".dk", ".fi", ".no", ".ie", ".cz", ".ro",
    ".hu", ".sk", ".hr", ".bg", ".gr", ".lt", ".lv", ".ee",
    ".si", ".lu", ".mt", ".cy", ".eu",
}

TLD_COUNTRY = {
    ".de": "Germany", ".es": "Spain", ".fr": "France", ".it": "Italy",
    ".nl": "Netherlands", ".pl": "Poland", ".se": "Sweden", ".be": "Belgium",
    ".at": "Austria", ".pt": "Portugal", ".dk": "Denmark", ".fi": "Finland",
    ".no": "Norway", ".ie": "Ireland", ".cz": "Czech Republic", ".ro": "Romania",
    ".hu": "Hungary", ".sk": "Slovakia", ".hr": "Croatia", ".bg": "Bulgaria",
    ".gr": "Greece", ".eu": "European Union",
}

# ── EU Legal Goldmine Configuration ──────────────────────────────────────────
IMPRESSUM_SLUG = "/impressum"
AVISO_LEGAL_SLUG = "/aviso-legal"
MENTIONS_LEGALES_SLUG = "/mentions-legales"
NOTE_LEGALI_SLUG = "/note-legali"

TLD_PRIORITY_SLUGS = {
    ".de": [IMPRESSUM_SLUG],
    ".at": [IMPRESSUM_SLUG],
    ".ch": [IMPRESSUM_SLUG],
    ".es": [AVISO_LEGAL_SLUG, "/privacidad", "/contacto"],
    ".fr": [MENTIONS_LEGALES_SLUG],
    ".it": [NOTE_LEGALI_SLUG],
    ".be": ["/legal-notice", "/mentions-legales"],
    ".nl": ["/disclaimer", "/colofon"],
}

# Contact slugs — EU-optimized
# German .de: impressum is LEGALLY REQUIRED → always has contact email
CONTACT_SLUGS = [
    "", "/contact", "/contact-us", "/contacto", "/kontakt",
    "/nous-contacter", "/contattaci", "/contatti",
    "/about", "/about-us", "/quienes-somos",
    IMPRESSUM_SLUG,
    AVISO_LEGAL_SLUG,
    "/legal-notice",
    MENTIONS_LEGALES_SLUG,
    NOTE_LEGALI_SLUG,
    "/get-in-touch", "/team", "/company",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8,de;q=0.7,fr;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


# ── Data Model ────────────────────────────────────────────────────────────────
@dataclass
class CompanyLead:
    email: str
    domain: str
    company_name: str = ""
    legal_officers: str = ""
    phone: str = ""
    vat_id: str = ""
    registration: str = ""
    source: str = ""
    country: str = ""
    website: str = ""
    page_found: str = ""
    is_public_contact: bool = False
    is_legal_source: bool = False
    has_legal_id: bool = False  # True if GmbH, S.L., SAS, etc. found
    priority_score: float = 0.0
    scraped_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))

    def generate_outreach_snippet(self) -> str:
        """Autonomously generates a high-authority outreach snippet citing legal data."""
        if not self.is_legal_source:
            return "Generic outreach (no legal hooks found)."
        
        legal_anchor = self.vat_id or self.registration or "Empresa Registrada"
        name = self.company_name or self.domain
        
        lines = [
            f"Subject: [Legal Insight] Referente a {name}",
            "Hola,",
            (f"He estado revisando la estructura legal de {name} "
             f"y vuestra presencia en {self.page_found}."),
            (f"Como experto en Trust Infrastructure (MOSKV-1), me ha llamado la "
             f"atención vuestro registro {legal_anchor}...")
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Email Extraction ──────────────────────────────────────────────────────────
def extract_emails(html: str) -> list[str]:
    """Multi-pass email extraction."""
    soup = BeautifulSoup(html, "html.parser")
    found: set[str] = set()

    # Pass 1: visible text
    text = soup.get_text(separator=" ")
    found.update(EMAIL_RE.findall(text))

    # Pass 2: mailto links
    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("mailto:"):
            email = a["href"][7:].split("?")[0].strip()
            if "@" in email:
                found.add(email)

    # Pass 3: Cloudflare obfuscation decode
    for el in soup.find_all(attrs={"data-cfemail": True}):
        decoded = _cf_decode(el.get("data-cfemail", ""))
        if decoded:
            found.add(decoded)

    # Pass 4: data-* attributes
    for tag in soup.find_all(True):
        for val in tag.attrs.values():
            if isinstance(val, str) and "@" in val and 5 < len(val) < 150:
                found.update(EMAIL_RE.findall(val))

    # Pass 5: inline scripts
    for script in soup.find_all("script"):
        if script.string and "@" in (script.string or ""):
            found.update(EMAIL_RE.findall(script.string or ""))

    # Pass 6: ROT13 obfuscation (some EU sites use this)
    rot13_emails = re.findall(
        r'\bROT13\(["\'"]([^"\']+)["\']\)',
        html, re.IGNORECASE
    )
    for enc in rot13_emails:
        decoded = enc.translate(str.maketrans(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
        ))
        if "@" in decoded:
            found.add(decoded)

    # Pass 7: Physical obfuscation [at], (at), {at}
    obs_text = html.replace("[at]", "@").replace("(at)", "@").replace("{at}", "@")
    obs_text = obs_text.replace("[dot]", ".").replace("(dot)", ".").replace("{dot}", ".")
    found.update(EMAIL_RE.findall(obs_text))

    return [e.lower().strip(".,;:'\"<>()[]{}") for e in found if _is_valid(e)]


def _cf_decode(encoded: str) -> str | None:
    try:
        r = int(encoded[:2], 16)
        return "".join(chr(int(encoded[i:i+2], 16) ^ r) for i in range(2, len(encoded), 2))
    except Exception:
        return None


def _is_valid(email: str) -> bool:
    email = email.lower()
    if not EMAIL_RE.match(email) or email.count("@") != 1:
        return False
    prefix, domain = email.split("@")
    if domain in BLACKLIST_DOMAINS:
        return False
    if any(bp in prefix for bp in BLACKLIST_PREFIXES):
        return False
    if re.search(r"\d+\.\d+", domain):  # version strings
        return False
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    return 2 <= len(tld) <= 6


def is_public_contact(email: str) -> bool:
    prefix = email.split("@")[0].lower()
    return any(prefix == p or prefix.startswith(f"{p}.") or prefix.startswith(f"{p}@") for p in PUBLIC_PREFIXES)


def is_priority(email: str) -> bool:
    prefix = email.split("@")[0].lower()
    return any(prefix == p or prefix.startswith(p) for p in PRIORITY_PREFIXES)


def is_legal_page(url: str) -> bool:
    """Checks if a URL refers to a legal/impressum page."""
    legal_slugs = [IMPRESSUM_SLUG, AVISO_LEGAL_SLUG, MENTIONS_LEGALES_SLUG, NOTE_LEGALI_SLUG, "/legal", "/privacy"]
    return any(slug.lower() in url.lower() for slug in legal_slugs)


def infer_country(domain: str) -> str:
    for tld, country in TLD_COUNTRY.items():
        if domain.endswith(tld):
            return country
    return ""


def is_eu_domain(domain: str) -> bool:
    return any(domain.endswith(tld) for tld in EU_TLDS)


def score_lead(lead: CompanyLead) -> float:
    """Sovereign Scoring Algorithm v6.0."""
    s = 0.0
    # PRIMARY SIGNAL: Verified Legal Entity (GmbH, S.L., SAS, etc.)
    if lead.has_legal_id:
        s += 100
    elif not is_priority(lead.email):
        s -= 40  # Shell penalty

    if lead.is_legal_source:
        s += 80

    if is_priority(lead.email):
        s += 50
    elif lead.is_public_contact:
        s += 30

    if is_eu_domain(lead.domain):
        s += 20
    if lead.company_name:
        s += 15
    if lead.vat_id or lead.registration:
        s += 35  # Authority booster

    if lead.legal_officers:
        s += 25
    return s


# ── HTTP Client ───────────────────────────────────────────────────────────────
class HTTPClient:
    """Resilient async HTTP client."""

    def __init__(self, delay: float = 1.0, max_retries: int = 3):
        self._delay = delay
        self._max_retries = max_retries
        self._last: float = 0.0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HTTPClient:
        self._client = httpx.AsyncClient(
            headers=HEADERS,
            follow_redirects=True,
            timeout=httpx.Timeout(connect=8.0, read=20.0, write=5.0, pool=5.0),
            verify=False,  # Note: verify=False for broader compatibility with legacy EU sites
            http2=True,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    async def get(self, url: str) -> str | None:
        elapsed = time.monotonic() - self._last
        if elapsed < self._delay:
            await asyncio.sleep(self._delay - elapsed)

        for attempt in range(self._max_retries):
            try:
                assert self._client
                resp = await self._client.get(url)
                self._last = time.monotonic()
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code in (429, 503):
                    await asyncio.sleep(2 ** attempt * 3)
                elif resp.status_code in (301, 302, 403, 404, 410):
                    return None
            except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
                log.debug(f"[{attempt+1}/{self._max_retries}] {url}: {exc}")
                await asyncio.sleep(2 ** attempt)
            except Exception as exc:
                log.debug(f"Unexpected: {exc}")
                break

        return None


# ── Company Crawler ───────────────────────────────────────────────────────────
class CompanyCrawler:
    """
    Direct company website crawler.
    Hits homepage + multilingual contact/legal page slugs.
    """

    def __init__(self, http: HTTPClient, max_pages: int = 8):
        self._http = http
        self._max_pages = max_pages

    def _generate_pages(self, domain: str) -> list[str]:
        """Calculates prioritized page list to crawl based on TLD."""
        current_slugs = [s for s in CONTACT_SLUGS if s]

        # Priority slugs for this specific TLD
        tld = next((t for t in TLD_PRIORITY_SLUGS if domain.endswith(t)), None)
        if tld:
            priorities = TLD_PRIORITY_SLUGS[tld]
            # Move priorities to the front
            for ps in reversed(priorities):
                if ps in current_slugs:
                    current_slugs.remove(ps)
                current_slugs.insert(0, ps)

        # Root is always first
        current_slugs.insert(0, "")

        pages: list[str] = []
        for scheme in ["https"]:
            for b in [f"{scheme}://{domain}", f"{scheme}://www.{domain}"]:
                for slug in current_slugs[:self._max_pages]:
                    pages.append(b + slug)

        # Unique ordered pages
        seen = set()
        return [p for p in pages if not (p in seen or seen.add(p))]

    def _extract_legal_data(self, html: str) -> dict:
        """Extracts official name, directors, phone and VAT from legal pages."""
        data = {"name": "", "officers": "", "phone": "", "vat": "", "reg": "", "has_legal_id": False}
        text = BeautifulSoup(html, "html.parser").get_text(separator=" ")

        # 1. Official Name (GmbH, S.L., Sp. z o.o., etc.)
        suffixes = r"GmbH|AG|KG|OHG|e\.V\.|GbR|S\.L\.|S\.A\.|S\.R\.L\.|SAS|Ltd|PLC|B\.V\.|N\.V\.|Sp\.\sz\so\.o\.|A/S|Oyj"
        name_match = re.search(rf"([A-Z][a-zA-Z0-9\-\.\s]{{1,50}}\b(?:{suffixes}))", text)
        if name_match:
            data["name"] = name_match.group(1).strip()
            data["has_legal_id"] = True
        else:
            data["has_legal_id"] = False

        # 2. Directors / Officers
        off_keywords = r"Geschäftsführer|Director|Represented by|Vertreten durch|Administrador|Gérant|Directeur"
        off_regex = rf"(?:{off_keywords})[:\s]+([A-Z][a-z]+\s[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
        off_match = re.search(off_regex, text)
        if off_match:
            data["officers"] = off_match.group(1).strip()

        # 3. Phone (common EU patterns)
        phone_match = re.search(r"(?:Tel|Phone|Tfn|Tél)[:\s]+([\+\d\s\-\/\(\)]{8,20})", text)
        if phone_match:
            data["phone"] = phone_match.group(1).strip()

        # 4. VAT / Tax ID (USt-IdNr, P.IVA, TVA, etc.)
        vat_keywords = r"VAT|USt\-IdNr|NIF|CIF|P\.IVA|TVA|BTW|IVA|UID"
        vat_regex = rf"(?:{vat_keywords})[:\s]+([A-Z]{{2}}[\s\d]{{5,15}}|\d{{8,12}})"
        vat_match = re.search(vat_regex, text)
        if vat_match:
            data["vat"] = vat_match.group(1).strip()

        # 5. Registration (Amtsgericht, Registry, KRS, etc.)
        reg_keywords = r"Amtsgericht|Registry|Registro Mercantil|KRS|Greffe|Handelsregister"
        reg_regex = rf"(?:{reg_keywords})[:\s]+([a-zA-Z\s\.\,\-]+[\d]{{3,10}})"
        reg_match = re.search(reg_regex, text)
        if reg_match:
            data["reg"] = reg_match.group(1).strip()

        return data

    async def crawl(self, url: str) -> list[tuple[str, str, dict, bool]]:
        """Returns (email, page_url, legal_data, is_legal_source) quadruples."""
        domain = urlparse(url).netloc.replace("www.", "")
        if not domain:
            return []

        # email -> (page_url, legal_data, is_legal)
        found: dict[str, tuple[str, dict, bool]] = {}
        pages_to_check = self._generate_pages(domain)
        best_legal_data = {"name": "", "officers": "", "phone": "", "vat": "", "reg": ""}

        for page_url in pages_to_check:
            html = await self._http.get(page_url)
            if not html:
                continue

            is_legal = is_legal_page(page_url)
            legal_data = {"name": "", "officers": "", "phone": "", "vat": "", "reg": "", "has_legal_id": False}
            
            if is_legal:
                legal_data = self._extract_legal_data(html)
                for key in ["name", "officers", "phone", "vat", "reg", "has_legal_id"]:
                    if legal_data.get(key) and not best_legal_data.get(key):
                        best_legal_data[key] = legal_data[key]

            for email in extract_emails(html):
                # If we find it in a legal page, override previous findings (3x conversion ROI)
                if email not in found or (is_legal and not found[email][2]):
                    found[email] = (page_url, best_legal_data.copy(), is_legal)
                    log.debug(f"    [+] {email} ({'LEGAL' if is_legal else 'GENERIC'}) ← {page_url}")

            # Optimization: If we have a quality lead from a legal source WITH legal ID, we might stop early
            if len(found) >= 4 and any(is_priority(e) for e in found) and best_legal_data["has_legal_id"]:
                break

        return [(e, p, d, is_legal) for e, (p, d, is_legal) in found.items()]


# ── SerpAPI Integration ───────────────────────────────────────────────────────
async def serpapi_search(
    query: str, api_key: str, pages: int = 3, http: HTTPClient | None = None
) -> list[dict]:
    """Use SerpAPI for Google results (100 free searches/month)."""
    results: list[dict] = []
    client = http

    for page_num in range(pages):
        start = page_num * 10
        url = (
            f"https://serpapi.com/search.json"
            f"?q={quote_plus(query)}"
            f"&start={start}"
            f"&num=10"
            f"&api_key={api_key}"
            f"&engine=google"
        )
        log.info(f"🔑 SerpAPI page {page_num+1}: {query}")

        assert client
        html = await client.get(url)
        if not html:
            continue

        try:
            data = json.loads(html)
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                title = result.get("title", "")
                if link:
                    results.append({"url": link, "name": title})
        except json.JSONDecodeError:
            log.warning("SerpAPI: Invalid JSON response")

    log.info(f"  → SerpAPI: {len(results)} URLs")
    return results


# ── Hunter.io Integration ─────────────────────────────────────────────────────
async def hunter_domain_search(
    domain: str, api_key: str, http: HTTPClient
) -> list[CompanyLead]:
    """Use Hunter.io API to find emails for a domain (50 free/month)."""
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
    html = await http.get(url)
    if not html:
        return []

    try:
        data = json.loads(html)
        emails_data = data.get("data", {}).get("emails", [])
        company_name = data.get("data", {}).get("organization", "")
        leads = []
        for e in emails_data:
            email = e.get("value", "")
            if email and _is_valid(email):
                lead = CompanyLead(
                    email=email,
                    domain=domain,
                    company_name=company_name,
                    source="hunter_io",
                    country=infer_country(domain),
                    website=f"https://{domain}",
                    is_public_contact=is_public_contact(email),
                )
                lead.priority_score = score_lead(lead)
                leads.append(lead)
        return leads
    except (json.JSONDecodeError, KeyError):
        return []


# ── MX Verification ──────────────────────────────────────────────────────────
async def verify_mx(domain: str) -> bool:
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 3.0
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: resolver.resolve(domain, "MX"))
        return True
    except Exception:
        return False


# ── Pipeline Components ───────────────────────────────────────────────────────
async def _process_serpapi_mode(args, http) -> list[dict]:
    if not (args.query and args.serpapi):
        return []
    query = args.query
    if args.sector:
        query += f" {args.sector}"
    if args.country:
        query += f" {args.country}"
    query += " email contact"
    return await serpapi_search(query, args.serpapi, args.pages, http)


async def _process_hunter_mode(args, http) -> list[CompanyLead]:
    if not (args.hunter and args.domain):
        return []
    log.info(f"🎯 Hunter.io: {args.domain}")
    return await hunter_domain_search(args.domain, args.hunter, http)

async def _process_domain_mining(args, crawler, domains) -> list[CompanyLead]:
    if not domains:
        return []

    # SORTING: Prioritize high-ROI EU domains (.de, .es, .fr, etc.)
    domains.sort(key=lambda d: not any(d.endswith(t) for t in TLD_PRIORITY_SLUGS))
    log.info(f"⛏️  Mining {len(domains)} domains (Prioritizing EU Legal Pages)...")

    results_leads = []
    sem = asyncio.Semaphore(5)

    async def safe_process(domain: str):
        async with sem:
            url = f"https://{domain}"
            pairs = await crawler.crawl(url)
            if not pairs:
                if await verify_mx(domain):
                    return [CompanyLead(email=f"{p}@{domain}", domain=domain, source="mx_pattern",
                                       country=infer_country(domain), website=url, is_public_contact=True)
                            for p in ["info", "contact", "sales"]]
                return []
            return [CompanyLead(
                email=email, domain=domain, page_found=page_found,
                company_name=legal.get("name") or "",
                legal_officers=legal.get("officers") or "",
                phone=legal.get("phone") or "",
                vat_id=legal.get("vat") or "",
                registration=legal.get("reg") or "",
                source="domain_crawl", country=infer_country(domain),
                website=url, is_public_contact=is_public_contact(email),
                is_legal_source=is_legal_source,
                has_legal_id=legal.get("has_legal_id", False)
            ) for email, page_found, legal, is_legal_source in pairs]

            for r in results:
                if isinstance(r, list):
                    for lead in r:
                        lead.priority_score = score_lead(lead)
                        results_leads.append(lead)
            return results_leads

async def _process_url_crawling(args, crawler, company_urls) -> list[CompanyLead]:
    if not company_urls:
        return []
    
    SKIP = {"linkedin.com", "facebook.com", "indeed.com", "glassdoor.com", "wikipedia.org", "amazon.com"}
    filtered = [r for r in company_urls if not any(skip in r.get("url", "") for skip in SKIP)]
    log.info(f"🌐 Crawling {len(filtered)} curated company sites...")

    leads = []
    for company in filtered:
        url = company["url"]
        name = company.get("name", "")
        domain = urlparse(url).netloc.replace("www.", "")
        if not domain:
            continue

        try:
            pairs = await crawler.crawl(url)
            country = args.country or infer_country(domain)
            for email, page, legal, is_legal_source in pairs:
                lead = CompanyLead(
                    email=email, domain=domain, company_name=legal.get("name") or name,
                    legal_officers=legal.get("officers") or "", phone=legal.get("phone") or "",
                    vat_id=legal.get("vat") or "", registration=legal.get("reg") or "",
                    source="url_crawl", country=country, website=url, page_found=page,
                    is_public_contact=is_public_contact(email),
                    is_legal_source=is_legal_source,
                    has_legal_id=legal.get("has_legal_id", False)
                )
                lead.priority_score = score_lead(lead)
                leads.append(lead)
        except Exception as exc:
            log.debug(f"Crawl error {url}: {exc}")
    return leads

# ── Main Pipeline ─────────────────────────────────────────────────────────────
async def run_pipeline(args: argparse.Namespace) -> list[CompanyLead]:
    all_leads: list[CompanyLead] = []

    async with HTTPClient(delay=args.delay) as http:
        crawler = CompanyCrawler(http, max_pages=args.max_pages)
        
        # 1. Inputs: SERPAPI & Hunter
        found_urls = await _process_serpapi_mode(args, http)
        all_leads.extend(await _process_hunter_mode(args, http))

        # 2. Add URLs from file
        if args.urls:
            urls_reader = Path(args.urls).read_text().splitlines()
            lines = [ln.strip() for ln in urls_reader if ln.strip() and not ln.startswith("#")]
            found_urls.extend([{"url": u, "name": ""} for u in lines])

        # 3. Domain Mining (Mode 4)
        domains_to_mine = []
        if args.domains:
            for line_raw in Path(args.domains).read_text().splitlines():
                ln = line_raw.strip()
                if not ln or ln.startswith("#"):
                    continue
                if ln.startswith("http"):
                    found_urls.append({"url": ln, "name": ""})
                else:
                    domains_to_mine.append(ln)
        
        all_leads.extend(await _process_domain_mining(args, crawler, domains_to_mine))
        all_leads.extend(await _process_url_crawling(args, crawler, found_urls))

    # Deduplicate & Filter
    if args.public_only:
        all_leads = [lead for lead in all_leads if lead.is_public_contact]
        
    if args.strict_legal:
        all_leads = [lead for lead in all_leads if lead.has_legal_id]

    seen: dict[str, CompanyLead] = {}
    for lead in all_leads:
        key = lead.email.lower()
        if key not in seen or lead.priority_score > seen[key].priority_score:
            seen[key] = lead

    return sorted(seen.values(), key=lambda lead: lead.priority_score, reverse=True)


# ── Output ────────────────────────────────────────────────────────────────────
def save_csv(leads: list[CompanyLead], path: Path) -> None:
    if not leads:
        log.warning("No leads found.")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(leads[0].to_dict().keys()))
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_dict())
    log.info(f"💾 CSV → {path} ({len(leads)} rows)")


def print_table(leads: list[CompanyLead], max_rows: int = 50) -> None:
    W = 158
    pub_count = sum(1 for lead in leads if lead.is_public_contact)
    eu_count = sum(1 for lead in leads if is_eu_domain(lead.domain))
    legal_count = sum(1 for lead in leads if lead.is_legal_source)

    fmt_header = (
        f"  {'SCR':>4}  {'EMAIL':<30} {'OFFICER':<22} {'COMPANY':<22} "
        f"{'STATUS':<12} {'PHONE/VAT/REG':<32} {'PUB':>4}"
    )
    print("\n" + "═" * W)
    print(fmt_header)
    print("─" * W)

    for lead in leads[:max_rows]:
        pub = "✓" if lead.is_public_contact else "·"
        status = "REAL BIZ" if lead.has_legal_id else "SHELL?"
        if lead.is_legal_source:
            status = f"LEG:{status}"

        vat_reg = (f"{lead.phone} | {lead.vat_id or lead.registration}"
                   if lead.vat_id or lead.registration else lead.phone)
        line = (
            f"  {lead.priority_score:>4.0f}  "
            f"{lead.email:<30} "
            f"{lead.legal_officers[:21]:<22} "
            f"{lead.company_name[:21]:<22} "
            f"{status:<12} "
            f"{vat_reg[:31]:<32} "
            f"{pub:>4}"
        )
        print(line)

    if len(leads) > max_rows:
        print(f"  ... +{len(leads) - max_rows} more rows")

    print("═" * W)
    ver = sum(1 for l in leads if l.has_legal_id)
    print((f"\n  📧 {len(leads)} emails | ⚖️ {legal_count} Legal (3x ROI) | "
           f"🏢 {ver} Verified | ✓ {pub_count} public | 🇪🇺 {eu_count} EU\n"))


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eu_email_scraper",
        description="🇪🇺 EU B2B Email Scraper — MOSKV-1 Sovereign v5.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRATEGIAS (en orden de efectividad):

1. DOMAIN LIST (mejor) — sin CAPTCHA, 100% resultados:
   echo "empresa.es\\nagencia.de\\ncompany.fr" > companies.txt
   python eu_email_scraper.py --domains companies.txt

2. URL LIST — tengo las URLs pero no los emails:
   python eu_email_scraper.py --urls company_urls.txt

3. SERPAPI (Google sin CAPTCHA - 100 free/mes):
   python eu_email_scraper.py --query "software Spain" --serpapi YOUR_KEY

4. HUNTER.IO (50 búsquedas free/mes):
   python eu_email_scraper.py --domain empresa.es --hunter YOUR_KEY

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO BUILD A DOMAIN LIST:
  • LinkedIn Sales Navigator → export companies
  • Kompass.com → search industry + country → copy domains
  • Europages.com → search → export/manually collect domains
  • Crunchbase → filter EU startups → export
  • Apollo.io / ZoomInfo → export domains (free tiers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
    )

    # Input sources
    g = p.add_argument_group("📥 Input sources (pick one or combine)")
    g.add_argument("--query", "-q", type=str, help="Search query (requires --serpapi)")
    g.add_argument("--domains", "-d", type=str, help="domains.txt file (one domain per line)")
    g.add_argument("--urls", type=str, help="urls.txt file (one URL per line)")
    g.add_argument("--domain", type=str, help="Single domain for Hunter.io lookup")

    # APIs
    a = p.add_argument_group("🔑 API Keys (optional)")
    a.add_argument("--serpapi", type=str, metavar="KEY", help="SerpAPI key (serpapi.com - 100 free/mo)")
    a.add_argument("--hunter", type=str, metavar="KEY", help="Hunter.io API key (50 free/mo)")

    # Filters
    f = p.add_argument_group("🔍 Filters")
    f.add_argument("--country", "-c", type=str, default="", help="Country hint (e.g. Spain)")
    f.add_argument("--sector", "-s", type=str, default="", help="Industry sector")
    f.add_argument("--public-only", action="store_true", help="Only info@/contact@ emails")
    f.add_argument("--outreach", action="store_true", help="Generate authority snippets")
    f.add_argument("--strict-legal", action="store_true", help="Exclude domains without verified Razón Social (GmbH, S.L., etc.)")

    # Output
    o = p.add_argument_group("📤 Output")
    o.add_argument("--output", type=str, default="eu_leads.csv", help="Output CSV path")
    o.add_argument("--json", action="store_true", help="Also export JSON")

    # Performance
    perf = p.add_argument_group("⚡ Performance")
    perf.add_argument("--pages", "-p", type=int, default=3, help="Pages for SerpAPI (default: 3)")
    perf.add_argument("--delay", type=float, default=1.0, help="Request delay seconds (default: 1.0)")
    perf.add_argument("--max-pages", type=int, default=8, help="Pages to crawl per site (default: 8)")

    return p


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate inputs
    has_input = any([args.query, args.domains, args.urls, args.domain])
    if not has_input:
        parser.error("Provide at least one input: --query, --domains, --urls, or --domain")
    if args.query and not args.serpapi:
        log.warning("⚠️  --query requires --serpapi KEY (search engines block bots)")
        log.warning("    Get free key at https://serpapi.com (100 searches/month)")
        log.warning("    Alternative: use --domains with a list of company domains")

    lines = [
        "",
        "═" * 70,
        "  🇪🇺  EU B2B EMAIL SCRAPER — MOSKV-1 SOVEREIGN v5.0",
        "═" * 70,
    ]
    if args.query:
        lines.append(f"  Query    : {args.query}")
    if args.domains:
        lines.append(f"  Domains  : {args.domains}")
    if args.urls:
        lines.append(f"  URLs     : {args.urls}")
    if args.country:
        lines.append(f"  Country  : {args.country}")
    lines += [
        f"  Output   : {args.output}",
        "═" * 70,
        "",
    ]
    print("\n".join(lines))

    t0 = time.monotonic()
    try:
        leads = await run_pipeline(args)
    except KeyboardInterrupt:
        print("\n⚡ Interrupted.")
        return

    elapsed = time.monotonic() - t0
    print_table(leads)
    
    if args.outreach:
        print("\n" + "═" * 120)
        print("  🚀 SOVEREIGN OUTREACH SNIPPETS (Top 3)")
        print("─" * 120)
        for lead in leads[:3]:
            if lead.is_legal_source:
                print(f"\n📧 Email: {lead.email}")
                print(lead.generate_outreach_snippet())
                print("─" * 40)
        print("═" * 120)

    save_csv(leads, Path(args.output))

    if args.json and leads:
        jp = Path(args.output).with_suffix(".json")
        jp.write_text(
            json.dumps([lead.to_dict() for lead in leads], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info(f"💾 JSON → {jp}")

    print(f"  ⏱️  {elapsed:.1f}s | 📧 {len(leads)} unique emails\n")


if __name__ == "__main__":
    asyncio.run(main())
