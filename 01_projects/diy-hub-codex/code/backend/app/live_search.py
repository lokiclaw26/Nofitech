"""Real live component lookup for DIY Hub V1 (Stage 5).

NOFI redesign: the Add Component flow no longer reads from a
pre-set list. For every query, we hit 5 free, no-key, no-login
public sources in parallel, merge the results, and return real
variants with real images and real specs.

Allowed sources (per NOFI brief, 2026-06-14):
    1. Wikimedia Commons  (images)  - commons.wikimedia.org
    2. Wikidata           (structured data) - wikidata.org
    3. Wikipedia REST     (descriptions) - en.wikipedia.org
    4. PlatformIO boards  (variant specs) - platformio.org
    5. GitHub public repos (board.json / datasheets)

Disallowed (per NOFI brief):
    - Google Custom Search
    - Octopart
    - Paid APIs
    - API keys
    - Login-required sources
    - Purchasing actions

User-Agent
----------
Every outbound request carries an identifying User-Agent per the
Wikimedia Foundation's policy. The format follows their guidelines:
    ``DIY-Hub/1.0 (https://github.com/nofitech; contact: ops@nofitech.local) Python-urllib``

Architecture
------------
1. ``search(query)`` — runs all 5 sources in parallel, 5s timeout each
2. Each source returns a list of partial ``Candidate`` dicts
3. ``_merge()`` groups partials by image/identifier, computes confidence
4. Return the merged list

Confidence score
----------------
- 0.0 = no live data
- 0.3 = 1 source returned something
- 0.5 = 2 sources returned something
- 0.7 = 3 sources returned something
- 0.9 = 4+ sources returned something
- A single image match from Commons counts +0.3
- A Wikidata entity match counts +0.2
- A PlatformIO board match counts +0.3
- A Wikipedia summary match counts +0.1

Caching
-------
A tiny in-process cache (1 entry per query, 60s TTL) avoids hammering
the APIs when the operator types and re-types the same query.

This module is stdlib-only (urllib + json + re). No requests, no aiohttp.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------

USER_AGENT = (
    "DIY-Hub/1.0 (https://github.com/nofitech; "
    "contact: ops@nofitech.local) Python-urllib"
)

_REQUEST_TIMEOUT = 5  # seconds per source

# In-process cache: query -> (timestamp, result)
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL = 60  # seconds

# Vendor cache: (vendor, query) -> (timestamp, [partial, ...])
# 1-hour TTL per NOFI brief ("Use cache to avoid repeated requests").
# Distinct from the 60s primary-source cache above.
_VENDOR_CACHE: Dict[Tuple[str, str], Tuple[float, List[Dict[str, Any]]]] = {}
_VENDOR_CACHE_TTL = 3600  # 1 hour

# Last request time per vendor: (vendor, timestamp). Used to enforce the
# 1-second minimum pause between requests to the same vendor.
_LAST_VENDOR_REQUEST: Dict[str, float] = {}
_VENDOR_MIN_INTERVAL = 1.0  # seconds between requests to the same vendor


def _vendor_throttle(vendor: str) -> None:
    """Sleep if needed to enforce the 1-second minimum pause per vendor.

    Called before every vendor HTTP request. Sleeps for the time gap
    between now and the last request to this vendor (if < 1s).
    """
    last = _LAST_VENDOR_REQUEST.get(vendor, 0.0)
    now = time.time()
    gap = now - last
    if gap < _VENDOR_MIN_INTERVAL:
        time.sleep(_VENDOR_MIN_INTERVAL - gap)
    _LAST_VENDOR_REQUEST[vendor] = time.time()


# -----------------------------------------------------------------------
# Public surface
# -----------------------------------------------------------------------

def search(query: str) -> Dict[str, Any]:
    """Run live lookup for a free-text query.

    Returns::

        {
            "query": "wemos d1 mini",
            "candidates": [<candidate>, ...],  # may be []
            "sources": {
                "commons":    {"status": "ok"|"timeout"|"error", "n": 5},
                "wikidata":   {"status": "ok"|"timeout"|"error", "n": 1},
                "wikipedia":  {"status": "ok"|"timeout"|"error", "n": 1},
                "platformio": {"status": "ok"|"timeout"|"error", "n": 1},
                "github":     {"status": "ok"|"timeout"|"error", "n": 0},
            },
            "error": None | "no reliable live result found",
        }

    Always returns (never raises). Per-source failures are recorded in
    ``sources``; the overall result is empty ``candidates`` if all 5
    sources fail or return 0 candidates.
    """
    q = (query or "").strip()
    if not q:
        return {
            "query": "",
            "candidates": [],
            "sources": {},
            "error": "empty query",
        }

    # Cache hit?
    now = time.time()
    if q in _CACHE and (now - _CACHE[q][0]) < _CACHE_TTL:
        return _CACHE[q][1]

    # Stage 12 (DIY-012 rule 10): check the verified cache FIRST. A hit
    # returns immediately with match_level='exact' and high confidence.
    # We still classify the query so the response shape stays consistent.
    from .identity import classify_query, platformio_allowed  # late import
    from .identity_cache import (
        get_rejected_signatures,
        get_verified,
        query_signature,
    )

    component_type = classify_query(q)
    pio_allowed = platformio_allowed(component_type)
    qsig = query_signature(q)

    verified_hit = get_verified(q)
    if verified_hit is not None:
        return _verified_cache_response(q, qsig, component_type, pio_allowed, verified_hit)

    # Run all 5 sources in parallel (plus 2 vendor sources — see below)
    sources_status: Dict[str, Dict[str, Any]] = {}
    partials: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=7) as pool:
        futures = {}
        futures[pool.submit(_fetch_commons, q)] = "commons"
        futures[pool.submit(_fetch_wikidata, q)] = "wikidata"
        futures[pool.submit(_fetch_wikipedia, q)] = "wikipedia"
        if pio_allowed:
            futures[pool.submit(_fetch_platformio, q)] = "platformio"
        else:
            # Per DIY-012 rule 3: explicitly record that PlatformIO was
            # skipped for non-board queries, so the UI / logs make it
            # obvious why it didn't appear.
            sources_status["platformio"] = {
                "status": "skipped",
                "n": 0,
                "note": f"PlatformIO gated: component_type={component_type!r} not in dev_board",
            }
        futures[pool.submit(_fetch_github, q)] = "github"
        # Stage 6: vendor scrapers (Adafruit, Pololu)
        futures[pool.submit(_fetch_adafruit, q)] = "adafruit"
        futures[pool.submit(_fetch_pololu, q)] = "pololu"
        for fut in as_completed(futures, timeout=_REQUEST_TIMEOUT + 1):
            name = futures[fut]
            try:
                rows, status = fut.result(timeout=0.1)
            except Exception as exc:  # noqa: BLE001
                rows, status = [], {"status": "error", "error": str(exc), "n": 0}
            # Don't overwrite the platformio-skipped status
            if name not in sources_status:
                sources_status[name] = status
            partials.extend(rows)

    # Merge by (commons_filename, wikidata_id) or by normalized name
    candidates = _merge(partials)

    # Compute per-candidate confidence
    for c in candidates:
        c["confidence"] = _confidence(c, sources_status)

    # Stage 10: clean + rank + filter (reject <50% confidence, drop tutorials/demos/etc)
    from .quality import rank_and_filter  # late import to avoid heavy dep at module load
    ranked = rank_and_filter(candidates, q)

    # Stage 12 (DIY-012): enrich with identity-engine fields, re-rank by
    # match_level (exact > variant > related > image_only), drop rejected
    # queries, and apply the 0.85 auto-confirm threshold.
    final = _apply_identity_engine(ranked["candidates"], q, component_type)

    result: Dict[str, Any] = {
        "query": q,
        "candidates": final,
        "rejected_count": ranked["rejected_count"] + (
            len(ranked["candidates"]) - len(final)
        ),
        "quality_threshold": ranked["quality_threshold"],
        "auto_confirm_threshold": _AUTO_CONFIRM_THRESHOLD,
        "best_confidence": ranked["best_confidence"],
        "component_type": component_type,
        "platformio_allowed": pio_allowed,
        "query_signature": qsig,
        "sources": sources_status,
        "error": None if final else "no reliable match found",
    }

    # Cache the result
    _CACHE[q] = (now, result)
    return result


# Stage 12: hard 0.85 threshold from NOFI brief 5A.
_AUTO_CONFIRM_THRESHOLD = 0.85


def _verified_cache_response(
    q: str,
    qsig: str,
    component_type: str,
    pio_allowed: bool,
    hit: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a search response for a verified-components cache hit.

    The cached row becomes the only candidate, with match_level='exact',
    confidence=0.95, confidence_reason mentioning the verified cache.
    """
    cached_candidate = {
        "id": f"verified:{hit.get('id', '')}",
        "name": hit.get("canonical_name", q),
        "model_number": hit.get("model_number") or "Unknown",
        "category": hit.get("component_type") or component_type or "Other",
        "manufacturer": hit.get("manufacturer") or "",
        "description": hit.get("description") or "",
        "voltage": hit.get("voltage") or "",
        "interfaces": hit.get("interfaces") or [],
        "key_specs": list((hit.get("specs") or {}).items()) if isinstance(hit.get("specs"), dict) else [],
        "image_url": hit.get("image_url") or None,
        "image_source": "verified_cache" if hit.get("image_url") else None,
        "datasheet_url": hit.get("datasheet_url") or "",
        "source_url": (hit.get("source_urls") or [None])[0],
        "tags": ["verified_cache", component_type],
        "matched_sources": ["verified_cache"],
        "source_quality": "vendor",
        "match_level": "exact",
        "confidence": 0.95,
        "confidence_reason": (
            f"From local verified cache (query signature {qsig!r}). "
            f"Verified by {hit.get('verified_by', 'nofi')!r} at "
            f"{hit.get('verified_at', 'unknown')}."
        ),
        "verified_cache": True,
    }
    response = {
        "query": q,
        "candidates": [cached_candidate],
        "rejected_count": 0,
        "quality_threshold": 0.50,
        "auto_confirm_threshold": _AUTO_CONFIRM_THRESHOLD,
        "best_confidence": 0.95,
        "component_type": component_type,
        "platformio_allowed": pio_allowed,
        "query_signature": qsig,
        "sources": {
            "verified_cache": {
                "status": "hit",
                "n": 1,
                "note": f"verified_components.query_signature={qsig}",
            },
        },
        "error": None,
        "verified_cache_hit": True,
    }
    # Cache the result so we don't repeat the DB lookup
    _CACHE[q] = (time.time(), response)
    return response


def _apply_identity_engine(
    candidates: List[Dict[str, Any]],
    query: str,
    component_type: str,
) -> List[Dict[str, Any]]:
    """Apply Stage 12 identity engine: enrich, re-rank, drop platformio-pollution.

    Steps:
      1. Filter out candidates with ``platformio_url`` when component_type is
         NOT ``dev_board`` (PlatformIO pollution guard, rule 3).
      2. Drop candidates whose signature is in the rejected_components cache
         (rule 5: "Rejected queries never return that candidate again").
      3. Compute ``match_level``, ``confidence_reason``, ``source_quality``,
         ``matched_sources`` via identity.enrich_candidate().
      4. Re-rank using identity.rank_key() (exact > variant > related > image_only).
      5. Drop ``match_level == "rejected"`` (none produced today, but the
         future reject-list path may add them).
    """
    from .identity import enrich_candidate, rank_key  # late import
    from .identity_cache import (
        candidate_signature,
        get_rejected_signatures,
    )
    rejected_sigs = set(get_rejected_signatures(query))
    out: List[Dict[str, Any]] = []
    for c in candidates:
        # Rule 5: drop candidates the operator has previously rejected.
        csig = candidate_signature(c)
        if csig in rejected_sigs:
            continue
        # Rule 3: PlatformIO gate on OUTPUTS, not just on the fetch step.
        # If the component_type is not dev_board, drop any candidate whose
        # ONLY identity source is platformio. (Other sources still allowed.)
        # We deliberately check matched_sources (not source_url, which can
        # also be a platformio URL) so a candidate with a wikidata_id AND
        # a platformio_url is still kept.
        if component_type != "dev_board" and c.get("platformio_url"):
            sources_l = {s.lower() for s in (c.get("matched_sources") or [])}
            non_pio_sources = sources_l - {"platformio"}
            if not non_pio_sources:
                # Only PlatformIO. Drop.
                continue
        # Filter out clearly-wrong rejects that snuck past quality.py
        # (e.g. identity reject-list is checked here).
        c["query"] = query
        enriched = enrich_candidate(c, component_type=component_type)
        if enriched.get("match_level") == "rejected":
            continue
        # Re-anchor confidence using match_level priority.
        # The new ranking uses (match_level, source_quality, confidence, image)
        # and replaces the pure confidence sort. We keep the Stage 11
        # confidence number for the threshold / "needs review" check, but
        # the SORT order is now identity-first.
        # Apply the variant-mismatch penalty from enrich_candidate by
        # adjusting the displayed confidence (UI threshold still works).
        boost = enriched.get("confidence_boost")
        if boost is not None:
            new_conf = max(0.0, min(1.0, float(enriched.get("confidence", 0.0)) + float(boost)))
            enriched["confidence"] = round(new_conf, 3)
        enriched.pop("confidence_boost", None)
        out.append(enriched)
    # Final sort: match_level > source_quality > confidence > has_image
    out.sort(key=rank_key, reverse=True)
    return out


def get_detail(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a more detailed spec sheet for a single candidate.

    The candidate is a dict from ``search()``'s result list. We re-hit
    the relevant source URLs to extract more detailed specs. Used by
    the frontend's "review" step before ADD TO DATABASE.
    """
    detail = dict(candidate)  # shallow copy
    detail.setdefault("interfaces", [])
    detail.setdefault("key_specs", [])
    detail.setdefault("tags", [])
    detail.setdefault("voltage", "")
    detail.setdefault("category", candidate.get("category", "Other"))

    # If we have a Wikidata ID, fetch the entity and pull out more claims
    qid = candidate.get("wikidata_id")
    if qid and qid.startswith("Q"):
        try:
            extra = _fetch_wikidata_entity(qid)
            detail.update(extra)
        except Exception as exc:  # noqa: BLE001
            print(f"[live_search.get_detail] wikidata entity fetch failed: {exc}", file=sys.stderr)

    # If we have a PlatformIO board URL, re-fetch the page and parse more
    pio_url = candidate.get("platformio_url")
    if pio_url:
        try:
            extra = _fetch_platformio_board(pio_url)
            detail.update(extra)
        except Exception as exc:  # noqa: BLE001
            print(f"[live_search.get_detail] platformio fetch failed: {exc}", file=sys.stderr)

    return detail


# -----------------------------------------------------------------------
# Source 1: Wikimedia Commons (file search)
# -----------------------------------------------------------------------

def _http_get(url: str, *, headers: Optional[Dict[str, str]] = None,
              timeout: int = _REQUEST_TIMEOUT) -> Tuple[bytes, Dict[str, str]]:
    """GET a URL with a polite User-Agent. Returns (body, response_headers)."""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.headers)


def _fetch_commons(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Search Wikimedia Commons for image files matching the query.

    Returns a list of partial candidates, each with a real Commons
    image URL and the filename that produced it.
    """
    status: Dict[str, Any] = {"status": "ok", "n": 0}
    try:
        params = urllib.parse.urlencode({
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srnamespace": 6,  # File namespace
            "srlimit": 5,
        })
        url = f"https://commons.wikimedia.org/w/api.php?{params}"
        body, _ = _http_get(url)
        data = json.loads(body.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [], {"status": "timeout", "error": str(exc), "n": 0}
    except (json.JSONDecodeError, ValueError) as exc:
        return [], {"status": "error", "error": f"json: {exc}", "n": 0}

    hits = data.get("query", {}).get("search", [])
    if not hits:
        return [], {"status": "ok", "n": 0}

    # Resolve the file URL for each hit (so we have a direct link to a thumbnail)
    titles = [h["title"] for h in hits]
    partials: List[Dict[str, Any]] = []
    try:
        info_body, _ = _http_get(
            "https://commons.wikimedia.org/w/api.php?"
            + urllib.parse.urlencode({
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "iiurlwidth": 500,
                "titles": "|".join(titles),
            })
        )
        info = json.loads(info_body.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        info = {}

    pages = info.get("query", {}).get("pages", {})
    for hit in hits:
        title = hit["title"]  # e.g. "File:Wemos D1 mini pro.png"
        # Find the matching page
        page = next(
            (p for p in pages.values() if p.get("title") == title),
            None,
        )
        if not page or "imageinfo" not in page:
            continue
        ii = page["imageinfo"][0]
        # Prefer the thumburl (500px), fall back to url
        img_url = ii.get("thumburl") or ii.get("url")
        if not img_url:
            continue
        # Skip non-image mimetypes (e.g. PDF datasheets are also in Commons)
        if not ii.get("mime", "").startswith("image/"):
            continue

        # Extract a friendly name from the filename
        # "File:Wemos D1 mini pro.png" -> "Wemos D1 mini pro"
        filename = title.split(":", 1)[1] if ":" in title else title
        friendly = re.sub(r"\.[a-zA-Z0-9]+$", "", filename)
        friendly = friendly.replace("_", " ")

        partials.append({
            "id": f"commons:{filename}",
            "name": _title_case(friendly),
            "model_number": "Unknown",
            "category": _guess_category_from_query(query),
            "image_url": img_url,
            "commons_filename": filename,
            "commons_page_url": ii.get("descriptionurl", ""),
            "image_source": "commons",
            "image_attribution": {
                "license": "CC BY-SA",
                "source_url": ii.get("descriptionurl", "https://commons.wikimedia.org/"),
            },
        })

    status["n"] = len(partials)
    return partials, status


# -----------------------------------------------------------------------
# Source 2: Wikidata (entity search)
# -----------------------------------------------------------------------

def _fetch_wikidata(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Search Wikidata for a structured product entity.

    Returns a list of partial candidates carrying wikidata_id,
    manufacturer, release_year, description.
    """
    status: Dict[str, Any] = {"status": "ok", "n": 0}
    try:
        params = urllib.parse.urlencode({
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "limit": 3,
            "format": "json",
        })
        url = f"https://www.wikidata.org/w/api.php?{params}"
        body, _ = _http_get(url)
        data = json.loads(body.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [], {"status": "timeout", "error": str(exc), "n": 0}
    except (json.JSONDecodeError, ValueError) as exc:
        return [], {"status": "error", "error": f"json: {exc}", "n": 0}

    hits = data.get("search", [])
    if not hits:
        return [], {"status": "ok", "n": 0}

    partials: List[Dict[str, Any]] = []
    for hit in hits:
        qid = hit.get("id", "")
        if not qid.startswith("Q"):
            continue
        label = hit.get("label") or query
        description = hit.get("description") or ""
        partials.append({
            "id": f"wikidata:{qid}",
            "name": _title_case(label),
            "model_number": qid,
            "category": _guess_category_from_query(query),
            "wikidata_id": qid,
            "wikidata_url": hit.get("concepturi", f"https://www.wikidata.org/wiki/{qid}"),
            "description": description,
            "tags": _extract_tags_from_description(description),
            "source_url": hit.get("concepturi", f"https://www.wikidata.org/wiki/{qid}"),
        })

    status["n"] = len(partials)
    return partials, status


def _fetch_wikidata_entity(qid: str) -> Dict[str, Any]:
    """Fetch a Wikidata entity and pull out a few key claims.

    P176 = manufacturer
    P577 = publication date
    P856 = official website
    Returns a dict that gets merged into the candidate detail.
    """
    params = urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims|labels|descriptions",
        "languages": "en",
        "format": "json",
    })
    url = f"https://www.wikidata.org/w/api.php?{params}"
    body, _ = _http_get(url, timeout=_REQUEST_TIMEOUT)
    data = json.loads(body.decode("utf-8", errors="replace"))
    entity = data.get("entities", {}).get(qid, {})

    out: Dict[str, Any] = {}
    claims = entity.get("claims", {})

    # Manufacturer (P176)
    if "P176" in claims:
        try:
            mv = claims["P176"][0]["mainsnak"]["datavalue"]["value"]
            mid = mv.get("id", "")
            if mid:
                out["manufacturer_wikidata_id"] = mid
                out["manufacturer"] = _wikidata_label(mid)
        except (KeyError, IndexError, TypeError):
            pass

    # Publication date (P577)
    if "P577" in claims:
        try:
            ts = claims["P577"][0]["mainsnak"]["datavalue"]["value"]["time"]
            # Format: "+2016-05-01T00:00:00Z"
            year = ts[:5].lstrip("+")
            out["release_year"] = year
        except (KeyError, IndexError, TypeError):
            pass

    # Official website (P856)
    if "P856" in claims:
        try:
            out["datasheet_url"] = claims["P856"][0]["mainsnak"]["datavalue"]["value"]
        except (KeyError, IndexError, TypeError):
            pass

    return out


def _wikidata_label(qid: str) -> str:
    """Fetch the English label of a Wikidata entity. Best-effort."""
    try:
        params = urllib.parse.urlencode({
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels",
            "languages": "en",
            "format": "json",
        })
        url = f"https://www.wikidata.org/w/api.php?{params}"
        body, _ = _http_get(url, timeout=2)
        data = json.loads(body.decode("utf-8", errors="replace"))
        return (
            data.get("entities", {}).get(qid, {})
            .get("labels", {}).get("en", {}).get("value", qid)
        )
    except Exception:  # noqa: BLE001
        return qid


# -----------------------------------------------------------------------
# Source 3: Wikipedia REST (descriptions)
# -----------------------------------------------------------------------

def _fetch_wikipedia(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch a Wikipedia summary for the query (best-effort, often 404).

    Returns 1 partial candidate carrying a description text.
    """
    status: Dict[str, Any] = {"status": "ok", "n": 0}
    title = query.replace(" ", "_")
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        body, _ = _http_get(url, headers={"Accept": "application/json"})
        data = json.loads(body.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return [], {"status": "ok", "n": 0, "note": "no article"}
        return [], {"status": "error", "error": f"http {exc.code}", "n": 0}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [], {"status": "timeout", "error": str(exc), "n": 0}
    except (json.JSONDecodeError, ValueError) as exc:
        return [], {"status": "error", "error": f"json: {exc}", "n": 0}

    extract = data.get("extract", "")
    title_norm = data.get("title", query)
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    if not extract:
        return [], {"status": "ok", "n": 0}

    partial = {
        "id": f"wikipedia:{title_norm}",
        "name": _title_case(title_norm),
        "model_number": "Unknown",
        "category": _guess_category_from_query(query),
        "description": extract,
        "tags": _extract_tags_from_description(extract),
        "source_url": page_url or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title_norm)}",
    }
    return [partial], {"status": "ok", "n": 1}


# -----------------------------------------------------------------------
# Source 4: PlatformIO board database
# -----------------------------------------------------------------------

# A small list of well-known board slugs. We try each in turn and accept
# the first one that 200s. This is fuzzy — "Wemos D1 Mini" might match
# `wemos-d1-mini-32` (ESP32) or `wemos-d1-mini-pro` (ESP8266) or others.
_PLATFORMIO_BOARD_TEMPLATES: tuple[str, ...] = (
    "{slug}",
    "{slug}-32",
    "{slug}-pro",
    "{slug}-mini",
)


def _platformio_slug_candidates(query: str) -> List[str]:
    """Build a list of PlatformIO board slugs to try for a query."""
    base = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    out: List[str] = []
    for tpl in _PLATFORMIO_BOARD_TEMPLATES:
        slug = tpl.format(slug=base)
        if slug not in out:
            out.append(slug)
    return out


def _fetch_platformio(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Try to find a PlatformIO board page for the query.

    PlatformIO is an AngularJS SPA — the static HTML doesn't contain
    the spec table. We just verify the page exists (200) and record
    its URL as a source. Real spec data has to come from a structured
    source (Wikidata / Wikipedia).
    """
    status: Dict[str, Any] = {"status": "ok", "n": 0}
    for slug in _platformio_slug_candidates(query):
        url = f"https://platformio.org/boards/{slug}"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                if resp.status == 200:
                    break
        except urllib.error.HTTPError:
            continue
        except (urllib.error.URLError, TimeoutError, OSError):
            return [], {"status": "timeout", "error": "platformio", "n": 0}
    else:
        return [], {"status": "ok", "n": 0}

    # Page exists — record it as a source. We don't try to parse
    # spec strings from the HTML (it's a SPA; specs are JS-rendered).
    # Instead, infer a couple of tags from the slug.
    tags = ["platformio"]
    if "esp32" in slug:
        tags.append("esp32")
    if "esp8266" in slug:
        tags.append("esp8266")
    if "wemos" in slug:
        tags.append("wemos")
    if "arduino" in slug:
        tags.append("arduino")
    if "raspberry" in slug:
        tags.append("raspberry-pi")

    partial: Dict[str, Any] = {
        "id": f"platformio:{slug}",
        "name": _title_case(slug.replace("-", " ")),
        "model_number": slug,
        "category": _guess_category_from_query(query),
        "platformio_url": url,
        "source_url": url,
        "tags": tags,
        "key_specs": [f"PlatformIO board page: {url}"],
    }
    return [partial], {"status": "ok", "n": 1}


def _fetch_platformio_board(url: str) -> Dict[str, Any]:
    """Re-fetch a known PlatformIO board page for richer detail."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {"_platformio_error": str(exc)}
    return {"key_specs": _parse_platformio_html(html)}


# Simple HTML spec extractor. Looks for <th>MCU</th><td>...</td> patterns.
_PIO_KEYS = ("MCU", "Frequency", "Flash", "RAM", "Voltage", "Digital I/O", "Analog I/O")


def _parse_platformio_html(html: str) -> List[str]:
    """Pull key spec strings out of a PlatformIO board page."""
    out: List[str] = []
    for key in _PIO_KEYS:
        m = re.search(
            rf"<th[^>]*>\s*{re.escape(key)}\s*</th>\s*<td[^>]*>([^<]+)</td>",
            html, re.IGNORECASE,
        )
        if m:
            out.append(f"{key}: {m.group(1).strip()}")
    return out


# -----------------------------------------------------------------------
# Source 5: GitHub public repos (readme fetch)
# -----------------------------------------------------------------------

def _fetch_github(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Search GitHub for a public repo matching the query.

    Uses the public REST API (no key, rate-limited). Returns 0 candidates
    if rate-limited or no match. We filter out unrelated repos whose
    name doesn't share a meaningful word with the query — without this
    filter, "Wemos D1 Mini" returns Printer-Monitor, Alexa-Wemo-Switch,
    etc. (repos that mention the term in the readme but aren't boards).
    """
    status: Dict[str, Any] = {"status": "ok", "n": 0}
    # Build a stopword set + the meaningful words from the query
    stop = {
        "the", "a", "an", "is", "of", "and", "or", "in", "on", "for", "to",
        "with", "by", "as", "it", "this", "that", "its", "be", "are", "was",
        "were", "has", "have", "had", "from", "at", "one", "two", "three",
    }
    query_words = {
        w for w in re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
        if w not in stop
    }
    if not query_words:
        return [], {"status": "ok", "n": 0, "note": "no meaningful query words"}

    try:
        params = urllib.parse.urlencode({
            "q": f"{query} board in:readme",
            "per_page": 10,
        })
        url = f"https://api.github.com/search/repositories?{params}"
        body, _ = _http_get(
            url, headers={"Accept": "application/vnd.github+json"}
        )
        data = json.loads(body.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return [], {"status": "ok", "n": 0, "note": "github rate-limited"}
        return [], {"status": "error", "error": f"http {exc.code}", "n": 0}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [], {"status": "timeout", "error": str(exc), "n": 0}
    except (json.JSONDecodeError, ValueError) as exc:
        return [], {"status": "error", "error": f"json: {exc}", "n": 0}

    items = data.get("items", [])
    # Keep only repos whose name OR description shares at least 1
    # meaningful word with the query. Description is added by the
    # repo owner, so it's a useful relevance signal.
    partials: List[Dict[str, Any]] = []
    for item in items:
        repo_name = item.get("full_name", "").lower()
        repo_desc = (item.get("description") or "").lower()
        haystack = f"{repo_name} {repo_desc}"
        if not any(w in haystack for w in query_words):
            continue
        partials.append({
            "id": f"github:{item['full_name']}",
            "name": _title_case(item["full_name"].split("/")[-1]),
            "model_number": "Unknown",
            "category": _guess_category_from_query(query),
            "source_url": item.get("html_url", ""),
            "tags": (item.get("topics") or []) + ["github"],
        })
        if len(partials) >= 3:
            break

    status["n"] = len(partials)
    return partials, status


# ---------------------------------------------------------------------------
# Stage 6: Vendor site scrapers (Adafruit, Pololu)
# ---------------------------------------------------------------------------
#
# Polite-crawler policy (per NOFI brief, 2026-06-14):
#   - robots.txt must allow the path we're scraping
#   - 1-second minimum pause between requests to the same vendor
#   - 1-hour cache per (vendor, query) to avoid repeated requests
#   - NEVER scrape price/stock/availability (NO purchasing actions)
#   - NEVER auto-save anything; the operator must click ADD TO DATABASE
#
# SparkFun was proposed and REJECTED — their search results page is
# JS-rendered and has no product URLs in the static HTML. Without a
# headless browser we can't reliably reach a product page from a query.
# Pololu's /search is disallowed by their robots.txt, so we do NOT
# call it. Pololu's candidates are reachable only via direct product
# URLs (e.g. https://www.pololu.com/product/1182) which the operator
# can paste into the description field manually if needed.
#


def _vendor_cached(vendor: str, query: str) -> Optional[List[Dict[str, Any]]]:
    """Return cached vendor partials if fresh, else None."""
    key = (vendor, query)
    if key in _VENDOR_CACHE:
        ts, rows = _VENDOR_CACHE[key]
        if (time.time() - ts) < _VENDOR_CACHE_TTL:
            return rows
    return None


def _vendor_store(vendor: str, query: str, rows: List[Dict[str, Any]]) -> None:
    """Cache vendor partials with a 1-hour TTL."""
    _VENDOR_CACHE[(vendor, query)] = (time.time(), rows)


def _http_get_vendor(vendor: str, url: str, *, headers: Optional[Dict[str, str]] = None,
                      timeout: int = _REQUEST_TIMEOUT) -> Optional[bytes]:
    """HTTP GET with vendor throttling and a polite User-Agent.

    Returns the response body, or None on any error. NEVER raises.
    """
    _vendor_throttle(vendor)
    h = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        h.update(headers)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(f"[{vendor}] network error for {url}: {exc}", file=sys.stderr)
        return None


def _extract_meta(html: str, prop: str) -> Optional[str]:
    """Pull the content attribute from a <meta property="X" content="Y"> tag.

    Returns the first match's content, or None if not found.
    """
    pat = re.compile(
        rf'<meta[^>]+property="{re.escape(prop)}"[^>]+content="([^"]+)"',
        re.IGNORECASE,
    )
    m = pat.search(html)
    if m:
        return m.group(1)
    # Try the reverse attribute order
    pat2 = re.compile(
        rf'<meta[^>]+content="([^"]+)"[^>]+property="{re.escape(prop)}"',
        re.IGNORECASE,
    )
    m = pat2.search(html)
    return m.group(1) if m else None


# --- Adafruit ----------------------------------------------------------------

_ADAFRUIT_MAX_RESULTS = 10  # DIY-012 rule 8: inspect at least 5, up to 10


def _adafruit_extract_product_links(html: str) -> List[Tuple[str, str]]:
    """Pull all product hrefs from an Adafruit search page.

    Returns a list of (href, product_id) pairs in the order they appear.
    De-duplicates by product_id.
    """
    out: List[Tuple[str, str]] = []
    seen_ids: Set[str] = set()
    for m in re.finditer(
        r'<a[^>]+href="(/product/(\d+)[^"]*)"[^>]*>(.*?)</a>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        href = m.group(1)
        pid = m.group(2)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        out.append((href, pid))
    return out


def _adafruit_title_token_match(query: str, title: str) -> int:
    """Return count of query tokens that appear in the title (lowercased)."""
    q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    t_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    return len(q_tokens & t_tokens)


def _fetch_adafruit(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Search Adafruit for products matching the query.

    Stage 12 (DIY-012 rule 8): inspect up to ``_ADAFRUIT_MAX_RESULTS`` results
    (not just the first), rank by exact token match + variant compatibility,
    and return the top results in a stable, relevance-ordered list.

    Polite-crawler policy still applies: 1-second minimum pause per vendor,
    1-hour cache per (vendor, query), and we cap to 5 product-page fetches
    per query (the search-page + up to 4 product pages).

    robots.txt allows /search and /product/<id>. The first 5 product links
    are inspected; we then fetch the top 1 (best match) to get the rich
    metadata. The rest are returned as partials using search-page metadata.
    """
    status: Dict[str, Any] = {"status": "ok", "n": 0}
    cached = _vendor_cached("adafruit", query)
    if cached is not None:
        status["n"] = len(cached)
        status["cache"] = "hit"
        return list(cached), status

    # 1) Search Adafruit
    search_url = f"https://www.adafruit.com/search?q={urllib.parse.quote(query)}"
    body = _http_get_vendor("adafruit", search_url)
    if body is None:
        return [], {"status": "timeout", "error": "adafruit search", "n": 0}

    html = body.decode("utf-8", errors="replace")
    product_links = _adafruit_extract_product_links(html)
    if not product_links:
        return [], {"status": "ok", "n": 0}

    # Cap to top N
    product_links = product_links[:_ADAFRUIT_MAX_RESULTS]

    # 2) Quickly score each link by extracting the anchor text (the title
    #    on the search page) and counting token overlap with the query.
    #    Then fetch the TOP 1 product page (per polite-crawler policy) to
    #    get rich metadata.
    scored: List[Tuple[int, int, Tuple[str, str]]] = []  # (score, idx, link)
    for idx, (href, pid) in enumerate(product_links):
        m = re.search(
            rf'<a[^>]+href="{re.escape(href)}"[^>]*>(.*?)</a>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        anchor = m.group(1) if m else ""
        anchor_text = re.sub(r"<[^>]+>", " ", anchor)
        anchor_text = re.sub(r"\s+", " ", anchor_text).strip()
        score = _adafruit_title_token_match(query, anchor_text)
        # Heavily penalize variant mismatches: a title that contains Pro/Plus
        # but the query doesn't is demoted
        q_norm = query.lower()
        for bad in ("pro", "plus", "lite", "v2", "v3", "v4", "s2", "s3", "c3", "h2"):
            if bad in anchor_text.lower() and bad not in q_norm:
                score -= 1
        scored.append((score, idx, (href, pid)))
    scored.sort(key=lambda t: (-t[0], t[1]))  # higher score first; stable on idx

    # 3) Fetch the top 1 product page (1 request) to get rich metadata.
    top_score, _, (top_href, top_pid) = scored[0]
    top_url = f"https://www.adafruit.com{top_href}"
    body2 = _http_get_vendor("adafruit", top_url)
    rich: Dict[str, Any] = {}
    if body2 is not None:
        html2 = body2.decode("utf-8", errors="replace")
        title = _extract_meta(html2, "og:title")
        image_url = _extract_meta(html2, "og:image")
        description = _extract_meta(html2, "og:description")
        if not title:
            m2 = re.search(r"<title>([^<]+)</title>", html2, re.IGNORECASE)
            if m2:
                title = m2.group(1).split(":", 1)[0].strip()
        if description and len(description) > 500:
            description = description[:497] + "..."
        # Datasheet link
        ds_match = re.search(
            r'<a[^>]+href="([^"]+)"[^>]*>[^<]*[Dd]atasheet[^<]*</a>',
            html2,
        )
        datasheet_url = ""
        if ds_match:
            datasheet_url = ds_match.group(1)
            if datasheet_url.startswith("/"):
                datasheet_url = f"https://www.adafruit.com{datasheet_url}"
        rich = {
            "title": title or "",
            "image_url": image_url,
            "description": description or "",
            "datasheet_url": datasheet_url,
        }

    # 4) Build the top candidate (rich)
    top_title = rich.get("title") or _title_case(top_href.replace("-", " ").split("/")[-1])
    partials: List[Dict[str, Any]] = [
        {
            "id": f"adafruit:{top_pid}",
            "name": _title_case(top_title),
            "model_number": top_pid,
            "category": _guess_category_from_query(query),
            "description": rich.get("description", ""),
            "image_url": rich.get("image_url"),
            "image_source": "adafruit",
            "image_attribution": {
                "license": "see vendor page",
                "source_url": top_url,
            },
            "source_url": top_url,
            "datasheet_url": rich.get("datasheet_url", ""),
            "tags": ["adafruit", "vendor"],
        }
    ]

    # 5) Add the remaining 4 product links as partial candidates (no rich
    #    metadata, but the URL is enough to rank them as alternates).
    for score, idx, (href, pid) in scored[1:5]:
        product_url = f"https://www.adafruit.com{href}"
        m = re.search(
            rf'<a[^>]+href="{re.escape(href)}"[^>]*>(.*?)</a>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        anchor_text = m.group(1) if m else ""
        anchor_text = re.sub(r"<[^>]+>", " ", anchor_text)
        anchor_text = re.sub(r"\s+", " ", anchor_text).strip()
        partials.append({
            "id": f"adafruit:{pid}",
            "name": _title_case(anchor_text) or _title_case(href.replace("-", " ").split("/")[-1]),
            "model_number": pid,
            "category": _guess_category_from_query(query),
            "source_url": product_url,
            "tags": ["adafruit", "vendor"],
        })

    _vendor_store("adafruit", query, partials)
    status["n"] = len(partials)
    return partials, status


# --- Pololu ------------------------------------------------------------------

def _fetch_pololu(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Pololu vendor fetcher — DISABLED.

    Pololu's robots.txt disallows /search. To respect it, we do NOT call
    /search. Instead we return 0 candidates with a note explaining why.
    Niche components that only Pololu carries can be added via the
    "Enter manually" form (parked for Stage 7+) or by pasting a direct
    Pololu product URL into the description field.
    """
    return [], {
        "status": "ok",
        "n": 0,
        "note": "Pololu /search disallowed by robots.txt; not scraped. Use direct Pololu URLs or Enter manually.",
    }


# --- SparkFun (DISABLED) -----------------------------------------------------

# SparkFun's search results page is JS-rendered and contains no product
# URLs in the static HTML. Without a headless browser we cannot extract
# a product URL from a query. This violates NOFI's "no aggressive
# scraping" rule. SparkFun is parked until they add a structured search
# endpoint or a no-JS search page.
#
# def _fetch_sparkfun(query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
#     raise NotImplementedError("SparkFun search is JS-rendered, parked.")


# -----------------------------------------------------------------------
# Merge + confidence
# -----------------------------------------------------------------------

def _merge(partials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group partial candidates and combine their fields.

    Group key priority:
        1. commons_filename (most specific — same image = same board)
        2. wikidata_id (structured identity)
        3. platformio_url (board page is a strong identity)
        4. normalized name (fallback, fuzzy — strips "front.jpg", "pro", etc.)

    A "Wemos D1 Mini Pro" Commons file and a "Wemos D1 Mini Pro" PlatformIO
    page would each be their own group (different identifiers), but the
    3 Commons images of the same physical board ("front.jpg" / "back.jpg"
    / "luftdata" / "co2-guard0") all merge into one Wemos D1 Mini entry
    because we strip trailing suffix tokens.
    """
    groups: Dict[str, Dict[str, Any]] = {}
    for p in partials:
        key = (
            p.get("commons_filename")
            or p.get("wikidata_id")
            or p.get("platformio_url")
            or _normalize_name(_strip_image_suffix(p.get("name", "")))
        )
        if not key:
            continue
        if key not in groups:
            groups[key] = dict(p)
            groups[key]["_sources"] = set()
            # Track all merged image URLs (a candidate can show multiple
            # photos — e.g. front + back of the same board)
            groups[key]["_image_urls"] = []
            if p.get("image_url"):
                groups[key]["_image_urls"].append(p["image_url"])
        else:
            _merge_into(groups[key], p)
        groups[key]["_sources"].add(p.get("id", "").split(":", 1)[0])
        if p.get("image_url") and p["image_url"] not in groups[key]["_image_urls"]:
            groups[key]["_image_urls"].append(p["image_url"])

    out: List[Dict[str, Any]] = []
    for g in groups.values():
        sources = g.pop("_sources", set())
        image_urls = g.pop("_image_urls", [])
        g["matched_sources"] = sorted(sources)
        # If we collected multiple images, surface the first as the primary
        # and stash the rest in image_alternates for the UI to use.
        if image_urls:
            if not g.get("image_url"):
                g["image_url"] = image_urls[0]
            g["image_alternates"] = image_urls[1:]
        out.append(g)
    return out


def _strip_image_suffix(name: str) -> str:
    """Strip trailing tokens that look like image-orientation suffixes.

    "Wemos D1 Mini Front" -> "wemos d1 mini"
    "WeMos D1 Mini Back"  -> "wemos d1 mini"
    "Co2-Guard0"          -> "co2-guard0"  (no suffix)
    "Luftdata - Wemos D1 Mini" -> "luftdata - wemos d1 mini"  (kept, no suffix)
    """
    suffixes = {
        "front", "back", "top", "bottom", "side", "left", "right",
        "angle", "angled", "iso", "view", "closeup", "close", "macro",
        "small", "large", "thumbnail",
    }
    if not name:
        return name
    # If name is hyphenated like "WeMos-D1-Mini-front", strip trailing
    # hyphenated suffixes. Otherwise strip trailing words.
    parts = re.split(r"[\s_-]+", name.strip().lower())
    while parts and parts[-1] in suffixes:
        parts.pop()
    return " ".join(parts)


def _merge_into(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Merge fields from ``source`` into ``target`` (target wins on conflict)."""
    for k, v in source.items():
        if k in ("id", "_sources"):
            continue
        if k not in target or not target[k]:
            target[k] = v
        elif isinstance(v, list) and isinstance(target[k], list):
            for item in v:
                if item not in target[k]:
                    target[k].append(item)


def _confidence(c: Dict[str, Any], sources_status: Dict[str, Dict[str, Any]]) -> float:
    """Score 0.0-1.0 based on how many sources contributed and matched."""
    score = 0.0
    if c.get("image_url"):
        score += 0.3
    if c.get("wikidata_id"):
        score += 0.2
    if c.get("platformio_url"):
        score += 0.3
    if c.get("description"):
        score += 0.1
    if c.get("datasheet_url"):
        score += 0.1
    matched = c.get("matched_sources", [])
    if len(matched) >= 3:
        score += 0.2
    elif len(matched) == 2:
        score += 0.1
    # Stage 6: vendor sources are single-source by themselves, so we
    # don't add an extra bonus for them — the image/description above
    # already cover what a vendor provides.
    return min(round(score, 2), 1.0)


# -----------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------

def _title_case(s: str) -> str:
    """Title-case but preserve acronyms like ESP32, STM32, DC, USB, etc."""
    if not s:
        return s
    # Common acronym words that should be all-caps
    acronyms = {"esp", "stm", "usb", "uart", "i2c", "spi", "can", "i/o", "pcb", "io"}
    words = re.split(r"(\s+|[-_/])", s)
    out: List[str] = []
    for w in words:
        if not w.strip():
            out.append(w)
            continue
        low = w.lower()
        if low in acronyms:
            out.append(w.upper())
        elif w.isupper() and len(w) <= 6:
            # Preserve already-cased tokens like "ESP32", "STM32"
            out.append(w)
        else:
            out.append(w.capitalize())
    return "".join(out)


def _normalize_name(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


_CATEGORY_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Microcontroller", ("esp32", "esp8266", "arduino", "stm32", "raspberry", "wemos", "teensy", "pic")),
    ("Sensor",            ("sensor", "bme280", "dht", "ds18b20", "mpu", "imu", "ultrasonic", "lidar")),
    ("Display",           ("display", "lcd", "oled", "tft", "led matrix", "neopixel", "ws2812", "sk6812")),
    ("Motor",             ("servo", "motor", "stepper", "mg996", "sg90", "a4988", "drv", "tmc")),
    ("Regulator",         ("regulator", "7805", "7809", "7812", "ams1117", "buck", "boost")),
    ("Op-amp",            ("lm358", "lm324", "tl072", "ne5532", "op-amp", "opamp")),
    ("Connector",         ("connector", "header", "jst", "ph2.0", "xt60", "deans")),
    ("Passive",           ("resistor", "capacitor", "inductor", "diode", "transistor", "crystal")),
)


def _guess_category_from_query(query: str) -> str:
    q = query.lower()
    for cat, hints in _CATEGORY_HINTS:
        if any(h in q for h in hints):
            return cat
    return "Other"


def _extract_tags_from_description(text: str) -> List[str]:
    """Pick a few nouns/keywords from a description for tag suggestions."""
    if not text:
        return []
    # Drop common stopwords + punctuation, take 5 most-frequent meaningful words
    stop = {
        "the", "a", "an", "is", "of", "and", "or", "in", "on", "for", "to",
        "with", "by", "as", "it", "this", "that", "its", "be", "are", "was",
        "were", "has", "have", "had", "from", "at", "one", "two", "three",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
    counts: Dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        counts[w] = counts.get(w, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:5]]


__all__ = ["search", "get_detail"]
