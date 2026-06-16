"""DIY Hub V1 — Stage 10: Candidate cleaning, ranking, and validation.

The live search returns raw partial candidates from 6 sources
(Wikimedia Commons, Wikidata, Wikipedia REST, PlatformIO, GitHub,
Adafruit). Those raw candidates are noisy:

  * Tutorials, demos, libraries, blog posts
  * Random GitHub repos using the chip in a project
  * Unrelated images whose title happens to mention the query
  * Datasheet URLs for wrong components
  * Search-result pages instead of product pages

This module sits between ``live_search._merge()`` and the model-picker
popup. It is pure-Python, stdlib-only, and stateless. It does NOT make
network calls.

Public surface
--------------
``clean_candidates(raw_list, query) -> list[dict]``
    Apply hard filters and reorder. Returns the final list to ship
    to the frontend, already filtered to confidence >= threshold and
    sorted by confidence DESC. Capped at ``MAX_CANDIDATES``.

``score_candidate(c, query) -> float``
    Compute a 0.0-1.0 confidence for a single raw candidate. Pure
    function of the candidate's contents (and the query).

``validate_image(c) -> (bool, str)``
    Return (ok, reason). ``ok`` is True if the image URL is present,
    is a plausible real image (extension + approved domain), and
    isn't on the placeholder blocklist.

Thresholds
----------
``QUALITY_THRESHOLD = 0.50`` — candidates below this are dropped.
``MAX_CANDIDATES = 12`` — never show more than this many.

Blacklist
---------
Any candidate whose title, description, or source_url contains any of
the ``BLACKLIST_TERMS`` is hard-rejected (confidence forced to 0.0).
This filters out tutorials, demos, libraries, blog posts, etc.

Title-token check
-----------------
At least one meaningful query token (>= 3 chars, alphanumeric) must
appear in the candidate's title or name. This prevents ``Wemos D1
Mini`` from matching ``Wemos Lolin D1 Mini Pro`` if the user is
looking for a specific board.

Image validation
----------------
Image URLs must:
  * start with http:// or https://
  * end with .jpg, .jpeg, .png, or .webp (case-insensitive)
  * be hosted on an approved domain (commons.wikimedia.org,
    cdn-shop.adafruit.com, platformio.org, raw.githubusercontent.com,
    github.com/user-attachments, upload.wikimedia.org)

Missing or invalid image -> confidence -= 0.30.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------

# Confidence cutoff. Candidates below this are hidden.
QUALITY_THRESHOLD = 0.50

# Hard cap on results shown to the operator.
MAX_CANDIDATES = 12

# Hard reject: any candidate whose title, description, or source_url
# contains any of these substrings (case-insensitive) is dropped.
BLACKLIST_TERMS: List[str] = [
    "tutorial",
    "demo",
    "library",
    "example",
    "blog",
    "guide",
    "how to",
    "how-to",
    "course",
    "lesson",
    "workshop",
    "intro to",
    "introduction to",
    "getting started",
    "first project",
    "my project",
    "weather station",     # very common Arduino project, almost never the actual sensor
    "smart home",
    "iot project",
    "arduino project",
    "raspberry pi project",
    "esp32 project",
    "esp8266 project",
    "home assistant",
    "homeassistant",
    "github.io",           # user/project pages
    "github.com/arduino-libraries",
    "github.com/esp8266",
    "github.com/espressif",# many of these are sample projects, not the chip itself
    "github.com/platformio/platformio-examples",
    "github.com/platformio/platform-atmelavr",  # platform docs, not the part
    "github.com/platformio/platform-",          # generic platform repos
    ".md",                 # markdown docs
    "wiki/How",            # how-to wiki pages
]

# Allow-list of "trusted source URL" patterns. A candidate whose
# source_url matches one of these is treated as a manufacturer/official
# page regardless of how the title heuristic would otherwise score it.
TRUSTED_SOURCE_PATTERNS: List[str] = [
    r"^https?://([^/]+\.)?adafruit\.com/products/\d+",
    r"^https?://([^/]+\.)?adafruit\.com/product/\d+",
    r"^https?://([^/]+\.)?adafruit\.com/categories/\d+",
    r"^https?://([a-z0-9-]+\.)?platformio\.org/boards/",
    r"^https?://[a-z]+\.wikipedia\.org/wiki/",
    r"^https?://www\.wikidata\.org/wiki/Q\d+",
    r"^https?://www\.wikidata\.org/entity/Q\d+",
    r"^https?://commons\.wikimedia\.org/wiki/File:",
    r"^https?://www\.espressif\.com/",
    r"^https?://docs\.espressif\.com/",
    r"^https?://www\.arduino\.cc/",
    r"^https?://docs\.arduino\.cc/",
    r"^https?://www\.raspberrypi\.com/",
    r"^https?://www\.ti\.com/",
    r"^https?://www\.analog\.com/",
    r"^https?://www\.st\.com/",
    r"^https?://www\.microchip\.com/",
    r"^https?://www\.infineon\.com/",
    r"^https?://www\.nxp\.com/",
    r"^https?://datasheets\.pdf",
    r"^https?://[^/]+\.datasheet",
    r"\.pdf$",
]

# Image URL allow-list. Only these domains are trusted to serve real
# product/component photos.
APPROVED_IMAGE_DOMAINS: List[str] = [
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "cdn-shop.adafruit.com",
    "adafruit.com",                 # Adafruit product page images (not on cdn-shop)
    "platformio.org",
    "raw.githubusercontent.com",
    "user-images.githubusercontent.com",
    "github.com",  # for user-attachments and release images
    "docs.espressif.com",
    "store.arduino.cc",
    "arduino.cc",
    "raspberrypi.com",
    "ti.com",
    "analog.com",
    "st.com",
    "microchip.com",
]

# Image file extensions we consider real.
APPROVED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _norm(s: Optional[str]) -> str:
    """Lowercase, strip, collapse whitespace. None -> empty string."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.lower().strip())


def _query_tokens(query: str) -> List[str]:
    """Tokenize the query into meaningful (>2 chars, alphanumeric) tokens.

    Returns a list of tokens. Each token is also stored in normalized form
    (alphanumeric only, lowercase) for comparison.
    """
    q = (query or "").lower()
    # Split on non-alphanumeric except dot and dash (so "d1-mini" stays).
    raw = re.split(r"[^a-z0-9.-]+", q)
    return [t for t in raw if len(t) >= 3 and re.search(r"[a-z0-9]", t)]


def _has_token_overlap(candidate: Dict[str, Any], tokens: List[str]) -> bool:
    """True if at least one query token appears in the candidate's title or name."""
    if not tokens:
        return True
    title = _norm(candidate.get("title") or candidate.get("name"))
    if not title:
        return False
    for tok in tokens:
        if tok in title:
            return True
    return False


def _all_tokens_match(candidate: Dict[str, Any], tokens: List[str]) -> bool:
    """True if EVERY query token appears in the candidate's title (normalized).

    This is the strict check. "Wemos D1 Mini" needs to find "wemos", "d1",
    and "mini" (or "d1-mini" as a unit) in the title. "Wemos D1 Mini Pro"
    would also match all three, so the variant-mismatch check below
    is what catches the Pro case.
    """
    if not tokens:
        return True
    title_raw = (candidate.get("title") or candidate.get("name") or "").lower()
    title_clean = re.sub(r"[^a-z0-9]", "", title_raw)
    for tok in tokens:
        tok_clean = re.sub(r"[^a-z0-9]", "", tok)
        if len(tok_clean) < 3:
            continue
        if tok_clean not in title_clean:
            return False
    return True


def _has_strong_token_overlap(candidate: Dict[str, Any], tokens: List[str]) -> bool:
    """STRICTEST check: ALL query tokens must appear in candidate's title/name.

    Used in clean_candidates() as the primary filter. The old
    "any one token matches" check was too loose and let in projects
    (Luftdata, weather-station), photo variants (Front/Back), and
    unrelated Adafruit products.
    """
    return _all_tokens_match(candidate, tokens)


# Suffixes that indicate a photo of a component, not the component itself.
# These appear in Wikimedia Commons file titles like "Wemos D1 Mini Front"
# or "ESP32 DevKit V1 Top.jpg". They should be filtered out as model
# candidates — the user wants the COMPONENT, not photos OF it.
PHOTO_SUFFIXES: List[str] = [
    " front", " back", " top", " bottom", " left", " right", " side",
    " front.jpg", " back.jpg", " top.jpg", " bottom.jpg",
    " front.png", " back.png", " top.png", " bottom.png",
    " pinout", " schematic", " diagram", " pcb",
    " assembled", " disassembled", " bare", " blank",
    " closeup", " close-up", " detail", " macro",
]

# Variant suffixes that indicate a related but DIFFERENT product.
# If the user searched for "Wemos D1 Mini" and the result is "Wemos D1
# Mini Pro", that's a different product. We don't outright reject it
# (the user might want the Pro), but we lower its score significantly
# and demote it below the exact-match candidates.
VARIANT_SUFFIXES: List[str] = [
    "pro", "plus", "lite", "micro", "mini", "maxi", "xl",
    "v2", "v3", "v4", "v1.1", "v2.0",
    "s2", "s3", "c3", "h2",
    "esp32", "esp8266",  # when query is just "D1 Mini" but result is "ESP32 D1 Mini"
    "32u4", "168", "328", "328p",
]

# Project markers: a candidate title that contains any of these is a
# project/library/demo, not the actual component. Matched on the
# NORMALIZED title (dashes/spaces collapsed) so "weather-station" matches
# "weather station", "BME280-Weather-Station", "Wemos-D1-Mini-BME280-
# Weather-Station", etc.
PROJECT_MARKERS: List[str] = [
    "weatherstation",
    "weatherstationproject",
    "weatherstationcode",
    "smarthome",
    "homeautomation",
    "homeassistant",
    "iotproject",
    "arduinoproject",
    "esp32project",
    "esp8266project",
    "raspberrypiproject",
    "wemosproject",
    "nodemcuproject",
    "stm32project",
    "airquality",
    "airqualitymonitor",
    "airqualitysensor",
    "co2monitor",
    "luftdaten",
    "luftdata",  # a real German citizen-science project that uses Wemos
    "printermonitor",
    "alexaswitch",
    "wemoswitch",  # wemo is Belkin, not Wemos
    "fhem",
    "openhab",
    "node-red", "nodered",
    "tasmota",
    "esphome",
    "platformioexample",
    "platformiosample",
    "circuitpython",
    "micropython",
    "arduinoide",
]


def _has_photo_suffix(candidate: Dict[str, Any]) -> bool:
    """True if title ends in a photo suffix like 'Front', 'Back', 'Top'."""
    title = (candidate.get("title") or candidate.get("name") or "").lower().strip()
    if not title:
        return False
    # Check if title ENDS with any photo suffix
    for suffix in PHOTO_SUFFIXES:
        s = suffix.strip()
        if title.endswith(s):
            return True
        # Also check word-boundary suffix (e.g. "Foo Front")
        if title.endswith(" " + s):
            return True
    return False


def _has_project_marker(candidate: Dict[str, Any]) -> Optional[str]:
    """True if the candidate's title (normalized) contains a project marker.

    E.g. "Wemos-D1-Mini-BME280-Weather-Station" normalizes to
    "wemosd1minibme280weatherstation" which contains "weatherstation".

    Returns the matched marker string if found, None otherwise.
    """
    title_raw = (candidate.get("title") or candidate.get("name") or "").lower()
    # Normalize: remove all non-alphanumeric characters
    title_norm = re.sub(r"[^a-z0-9]", "", title_raw)
    for marker in PROJECT_MARKERS:
        if marker in title_norm:
            return marker
    return None


def _has_variant_mismatch(query: str, candidate: Dict[str, Any]) -> Optional[str]:
    """Detect when the title is a variant of the query (e.g. 'D1 Mini Pro' for 'D1 Mini').

    Returns the variant word that mismatches, or None if no mismatch.
    Does NOT reject — just used for scoring.
    """
    if not query:
        return None
    q_norm = re.sub(r"[^a-z0-9]", "", query.lower())
    title_raw = (candidate.get("title") or candidate.get("name") or "").lower()
    title_norm = re.sub(r"[^a-z0-9]", "", title_raw)
    # If the title is longer than the query, find what extra word(s) it has
    # that aren't in the query
    if title_norm in q_norm:
        return None  # title is a substring of query (e.g. "D1 Mini" in "Wemos D1 Mini Pro")
    # Look for variant suffixes in the title that aren't in the query
    for variant in VARIANT_SUFFIXES:
        if variant in title_norm and variant not in q_norm:
            return variant
    return None


def _has_blacklist_term(candidate: Dict[str, Any]) -> Optional[str]:
    """Return the first blacklisted term found, or None."""
    haystacks = [
        _norm(candidate.get("title")),
        _norm(candidate.get("name")),
        _norm(candidate.get("description")),
        _norm(candidate.get("source_url")),
        _norm(candidate.get("platformio_url")),
    ]
    for hay in haystacks:
        if not hay:
            continue
        for term in BLACKLIST_TERMS:
            if term in hay:
                return term
    return None


def _source_url(c: Dict[str, Any]) -> Optional[str]:
    """Pick the best source URL from a candidate (several possible keys).

    The live_search merge() sometimes stores the canonical URL under
    ``source`` (not ``source_url``), and sometimes under ``url``. We
    check all of them.
    """
    for key in ("source_url", "source", "platformio_url", "product_url", "url"):
        v = c.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def _is_trusted_source(c: Dict[str, Any]) -> bool:
    """True if any source URL on the candidate matches a trusted pattern."""
    urls = []
    for k in ("source_url", "source", "platformio_url", "product_url", "url", "datasheet_url"):
        v = c.get(k)
        if isinstance(v, str) and v.startswith("http"):
            urls.append(v)
    for url in urls:
        for pat in TRUSTED_SOURCE_PATTERNS:
            if re.search(pat, url, re.IGNORECASE):
                return True
    return False


def _is_adafruit_product(c: Dict[str, Any]) -> bool:
    """True if the candidate has an Adafruit product page URL."""
    src = _source_url(c)
    if not src:
        return False
    return bool(re.search(r"^https?://([^/]+\.)?adafruit\.com/(product|products|categories)", src, re.IGNORECASE))


# -----------------------------------------------------------------------
# Public surface
# -----------------------------------------------------------------------

def validate_image(c: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (ok, reason). ok=True if image looks like a real photo.

    - Image URL must be http(s) and end with an approved extension.
    - Must be hosted on an approved domain.
    """
    img = c.get("image_url")
    if not img or not isinstance(img, str):
        return False, "no image_url"
    if not img.startswith("http"):
        return False, "image_url not http(s)"
    # Strip query string for extension check
    path = urlparse(img).path.lower()
    if not any(path.endswith(ext) for ext in APPROVED_IMAGE_EXTENSIONS):
        return False, f"image extension not in {APPROVED_IMAGE_EXTENSIONS}"
    host = urlparse(img).netloc.lower()
    if not any(host == d or host.endswith("." + d) for d in APPROVED_IMAGE_DOMAINS):
        return False, f"image host {host!r} not approved"
    return True, "ok"


def score_candidate(c: Dict[str, Any], query: str) -> float:
    """Compute 0.0-1.0 confidence for a single raw candidate.

    Base: 0.30 (candidate passed hard filters).
    Additive bonuses. Penalties. Variant-mismatch penalty.

    Calibrated so that:
    - Real Adafruit product page (title matches query): ~0.65+
    - Wikidata entity with wikidata_id: ~0.50-0.60
    - PlatformIO board page (no image): ~0.40-0.50
    - Wikimedia Commons photo: ~0.40
    - GitHub-only repo: 0.0 (rejected by hard filters)
    - Variant mismatch (Pro/Plus/etc): -0.25 from base
    """
    score = 0.30
    tokens = _query_tokens(query)

    # 1. Image present + valid: +0.30
    img_ok, _ = validate_image(c)
    if img_ok:
        score += 0.30

    # 2. Wikidata structured entity: +0.25
    if c.get("wikidata_id"):
        score += 0.25

    # 3. PlatformIO board match: +0.20
    if c.get("platformio_url"):
        score += 0.20

    # 4. Adafruit product page (with matching title): +0.25
    if _is_adafruit_product(c):
        score += 0.25

    # 5. Wikipedia article: +0.10
    if c.get("wikipedia_url"):
        score += 0.10
    else:
        src_for_wiki = _source_url(c)
        if src_for_wiki and "wikipedia.org/wiki/" in src_for_wiki:
            score += 0.10

    # 6. Datasheet PDF: +0.20
    if isinstance(c.get("datasheet_url"), str) and c["datasheet_url"].lower().endswith(".pdf"):
        score += 0.20

    # 7. All query tokens appear in title: +0.10
    if tokens and _all_tokens_match(c, tokens):
        score += 0.10

    # 8. Has key_specs (non-empty): +0.05
    if isinstance(c.get("key_specs"), list) and c["key_specs"]:
        score += 0.05

    # 9. Has interfaces (non-empty): +0.05
    if isinstance(c.get("interfaces"), list) and c["interfaces"]:
        score += 0.05

    # 10. Has voltage: +0.03
    if c.get("voltage"):
        score += 0.03

    # 11. Trusted source bonus: +0.10 if any trusted source URL
    if _is_trusted_source(c):
        score += 0.10

    # Penalties
    # - GitHub-only source: -0.10
    srcs = c.get("_sources") or []
    if "github" in srcs and not any(s in srcs for s in ("commons", "wikidata", "adafruit", "platformio")):
        score -= 0.10

    # - No image AND not a trusted source: -0.30
    if not img_ok and not _is_trusted_source(c):
        score -= 0.30

    # - Weak title: less than 5 chars
    title = c.get("title") or c.get("name") or ""
    if not title or len(title.strip()) < 5:
        score -= 0.20

    # 12. Stage 11: Variant-mismatch penalty.
    # If the candidate's title contains a variant word (Pro, Plus, Lite,
    # etc.) that the query does NOT contain, demote the score. The user
    # searched for the base product; a Pro variant is a different product.
    variant = _has_variant_mismatch(query, c)
    if variant is not None:
        score -= 0.25

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, score))


def clean_candidates(raw_list: List[Dict[str, Any]], query: str) -> Tuple[List[Dict[str, Any]], int]:
    """Apply hard filters, score, sort, and cap the raw candidate list.

    Pipeline (Stage 11 — tightened after NOFI bug report):
      1. Hard blacklist reject (tutorial/demo/library/etc in title/desc)
      2. Photo-suffix reject (Front/Back/Top/etc -> just a photo of the part)
      3. Project-marker reject (weather-station, luftdata, iot-project, etc)
      4. ALL-tokens-must-match title check (no trusted-source bypass)
      5. Score each surviving candidate (with variant-mismatch penalty)
      6. Drop candidates below QUALITY_THRESHOLD
      7. Sort by confidence DESC
      8. Cap at MAX_CANDIDATES

    Returns (final_list, rejected_count).
    """
    tokens = _query_tokens(query)
    accepted: List[Tuple[float, Dict[str, Any]]] = []
    rejected_count = 0

    for c in raw_list:
        # 1. Blacklist
        bl = _has_blacklist_term(c)
        if bl is not None:
            rejected_count += 1
            c["_reject_reason"] = f"blacklist:{bl}"
            continue

        # 2. Photo suffix (e.g. "Wemos D1 Mini Front" — just a photo)
        if _has_photo_suffix(c):
            rejected_count += 1
            c["_reject_reason"] = "photo_suffix"
            continue

        # 3. Project marker (e.g. "Wemos-D1-Mini-BME280-Weather-Station")
        pm = _has_project_marker(c)
        if pm is not None:
            rejected_count += 1
            c["_reject_reason"] = f"project_marker:{pm}"
            continue

        # 4. ALL tokens must match the title (no trusted-source bypass)
        if not _all_tokens_match(c, tokens):
            rejected_count += 1
            c["_reject_reason"] = "no_all_tokens_match"
            continue

        # 5. Score (with variant-mismatch penalty applied inside)
        s = score_candidate(c, query)
        c["confidence"] = s

        # 6. Threshold
        if s < QUALITY_THRESHOLD:
            rejected_count += 1
            c["_reject_reason"] = f"below_threshold:{s:.2f}"
            continue

        accepted.append((s, c))

    # 7. Sort by confidence DESC, stable on (confidence, name) tiebreak
    accepted.sort(key=lambda t: (-t[0], _norm(t[1].get("title") or t[1].get("name"))))
    final = [c for _, c in accepted[:MAX_CANDIDATES]]
    return final, rejected_count


# -----------------------------------------------------------------------
# Convenience for live_search.search()
# -----------------------------------------------------------------------

def rank_and_filter(raw_candidates: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """One-call entry point for ``live_search.search()``.

    Returns:::
        {
            "candidates": [...],          # sorted, filtered, scored
            "rejected_count": int,        # how many were dropped
            "quality_threshold": float,   # the threshold used
            "best_confidence": float,     # max score in final set, 0.0 if empty
        }
    """
    cleaned, rejected = clean_candidates(raw_candidates, query)
    best = max((c.get("confidence", 0.0) for c in cleaned), default=0.0)
    return {
        "candidates": cleaned,
        "rejected_count": rejected,
        "quality_threshold": QUALITY_THRESHOLD,
        "best_confidence": round(best, 3),
    }
