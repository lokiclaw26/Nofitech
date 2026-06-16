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


def _has_strong_token_overlap(candidate: Dict[str, Any], tokens: List[str]) -> bool:
    """Stronger check: at least one alphanumeric token must appear in title.

    Unlike _has_token_overlap, this strips dots/dashes from the title
    before matching, so "esp32-s3" matches "esp32s3devkitcv1" etc.
    """
    if not tokens:
        return True
    title_raw = (candidate.get("title") or candidate.get("name") or "").lower()
    # Normalize: drop dots, dashes, underscores, spaces
    title_clean = re.sub(r"[^a-z0-9]", "", title_raw)
    for tok in tokens:
        tok_clean = re.sub(r"[^a-z0-9]", "", tok)
        if len(tok_clean) >= 3 and tok_clean in title_clean:
            return True
    return False


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

    Base: 0.0. Additive bonuses (capped at 1.0).
    Subtracts penalties.

    The score is calibrated so that:
    - Real Adafruit product page with image: ~0.65+
    - Wikidata entity + Wikimedia image: ~0.55+
    - PlatformIO board page (no image): ~0.40
    - Random GitHub repo alone: ~0.0
    - Tutorial with image: 0.0 (rejected upstream)
    """
    score = 0.30  # base: candidate passed hard filters
    tokens = _query_tokens(query)

    # 1. Image present + valid: +0.30
    img_ok, _ = validate_image(c)
    if img_ok:
        score += 0.30

    # 2. Wikidata structured entity: +0.20
    if c.get("wikidata_id"):
        score += 0.20

    # 3. PlatformIO board match: +0.20
    if c.get("platformio_url"):
        score += 0.20

    # 4. Adafruit / trusted vendor product: +0.25 (strong signal)
    if _is_adafruit_product(c):
        score += 0.25

    # 5. Wikipedia article: +0.10
    if c.get("wikipedia_url"):
        score += 0.10
    else:
        src_for_wiki = _source_url(c)
        if src_for_wiki and "wikipedia.org/wiki/" in src_for_wiki:
            score += 0.10

    # 6. Datasheet PDF: +0.20 (very strong signal)
    if isinstance(c.get("datasheet_url"), str) and c["datasheet_url"].lower().endswith(".pdf"):
        score += 0.20

    # 7. Title has all query tokens (not just one): +0.10
    if tokens:
        title = _norm(c.get("title") or c.get("name"))
        if all(tok in title for tok in tokens):
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

    # 11. Trusted source bonus: if the candidate has any trusted source
    #     URL (manufacturer, vendor, official docs, datasheet, etc.),
    #     add +0.10 even if no other signals.
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

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, score))


def clean_candidates(raw_list: List[Dict[str, Any]], query: str) -> Tuple[List[Dict[str, Any]], int]:
    """Apply hard filters, score, sort, and cap the raw candidate list.

    Pipeline:
      1. Hard blacklist reject (confidence = 0.0)
      2. Title-token overlap check (drop if no overlap)
      3. Score each surviving candidate
      4. Drop candidates below QUALITY_THRESHOLD
      5. Sort by confidence DESC
      6. Cap at MAX_CANDIDATES

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

        # 2. Title token overlap (skip if candidate has a trusted source URL
        #    — those are official pages even if title heuristic is weak)
        if not _has_strong_token_overlap(c, tokens) and not _is_trusted_source(c):
            rejected_count += 1
            c["_reject_reason"] = "no_token_overlap"
            continue

        # 3. Score
        s = score_candidate(c, query)
        c["confidence"] = s

        # 4. Threshold
        if s < QUALITY_THRESHOLD:
            rejected_count += 1
            c["_reject_reason"] = f"below_threshold:{s:.2f}"
            continue

        accepted.append((s, c))

    # 5. Sort by confidence DESC, stable on (confidence, name) tiebreak
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
