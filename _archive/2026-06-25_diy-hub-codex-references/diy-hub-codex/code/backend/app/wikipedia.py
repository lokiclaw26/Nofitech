"""Wikipedia REST image lookup for DIY Hub V1 (Stage 3).

NOFI explicit: NO Google, NO Octopart, NO paid APIs, NO API keys, NO login,
NO purchasing. We only call the public Wikipedia REST endpoint to grab the
lead-image thumbnail for a known component.

Endpoint:
    https://en.wikipedia.org/api/rest_v1/page/summary/<title>

Returns JSON with a ``thumbnail.source`` field when the page has a lead
image. Some components (e.g. WS2812, SG90) do not have a thumbnail in the
English Wikipedia summary, so we return null and let the UI show a "No
real image found" empty state.

Per Wikimedia's User-Agent policy
(https://meta.wikimedia.org/wiki/User-Agent_policy), every request MUST
carry a UA string that identifies the project and a contact method. We
also cap each request at 5s so a slow Wikipedia mirror can't stall the
search endpoint.

Cache: in-memory, keyed by lowercased title. No disk, no expiry — the
catalog is small and the search box is hit by a single user, so a simple
dict is fine. Re-running the backend drops the cache.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request


# Wikimedia's UA policy requires contact info in the User-Agent header.
USER_AGENT = "DIYHubV1/0.1 (https://github.com/nofidofi; contact: nofidofi@local) Python-urllib"

# Per-request timeout. 5s is generous for a single REST call.
_TIMEOUT = 5

# In-memory cache. Keyed by lowercased title so case variants collapse.
_cache: dict[str, dict] = {}

# Result of a single lookup.
_EMPTY: dict = {"url": None, "source": None, "attribution": None}


def _empty() -> dict:
    """Always return a fresh dict so callers can mutate safely."""
    return {"url": None, "source": None, "attribution": None}


def fetch_wikipedia_image(title: str) -> dict:
    """Return ``{url, source, attribution}`` for the given Wikipedia page title.

    On any failure (timeout, HTTP 4xx/5xx, no ``thumbnail`` field, JSON
    parse error), returns ``{url: None, source: None, attribution: None}``
    and NEVER raises — the search flow must keep working even when
    Wikipedia is unreachable.

    The result is cached in-process by lowercased title. Logs every call
    to stderr so the operator can see what got hit.
    """
    if not title:
        return _empty()

    # Use the original (case-preserved) title for the HTTP request:
    # Wikipedia's REST API is case-sensitive on titles — "Arduino Uno"
    # works, "arduino uno" returns 404. But use the lowercased title as
    # the cache key so case variants collapse into a single entry.
    display_title = title.strip()
    key = display_title.lower()
    if key in _cache:
        return _cache[key]

    result = _lookup(display_title)
    _cache[key] = result
    print(f"[wikipedia] title={title} -> {result['source']}", file=sys.stderr)
    return result


def _lookup(display_title: str) -> dict:
    """Do the actual network call. Separated for testability + cache key use.

    ``display_title`` is the case-preserved Wikipedia page title (e.g.
    "Arduino Uno", "ESP32", "Raspberry Pi"). We percent-encode the
    whole thing for the URL.
    """
    # Wikipedia REST uses underscores for spaces in URLs. We percent-encode
    # everything else so titles with parentheses, ampersands, etc. survive.
    safe = display_title.replace(" ", "_")
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(safe, safe="")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        # Network is down, DNS failed, Wikipedia returned 4xx/5xx, or the
        # title contained characters urllib refuses. We swallow ALL of
        # these — the catalog must still work.
        print(f"[wikipedia] error for {display_title}: {exc}", file=sys.stderr)
        return _empty()

    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"[wikipedia] json error for {display_title}: {exc}", file=sys.stderr)
        return _empty()

    thumbnail = data.get("thumbnail")
    if not isinstance(thumbnail, dict):
        # No lead image for this page (e.g. WS2812, SG90). That's a normal
        # outcome, not an error — return null and let the UI handle it.
        return _empty()

    image_url = thumbnail.get("source")
    if not image_url or not isinstance(image_url, str):
        return _empty()

    # Wikipedia thumbnails are always returned under a CC BY-SA license
    # (with attribution required for the original uploader). We don't
    # fetch the full page metadata in this stage; the attribution block
    # here is just enough to render "Source: Wikipedia · CC BY-SA"
    # in the confirmation popup.
    return {
        "url": image_url,
        "source": "wikipedia",
        "attribution": {
            "license": "CC BY-SA",
            "source_url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(safe, safe=""),
        },
    }


__all__ = ["USER_AGENT", "fetch_wikipedia_image"]
