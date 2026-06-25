"""DIY Hub V1 — Stage 12: Component Identity Engine.

NOFI 2026-06-20: search has to become reliable RECOGNITION.

This module sits between ``live_search`` and the frontend. It:

  1. Classifies a query into ``component_type`` (dev_board / sensor / display /
     charger_power_module / ic_chip / passive / unknown).
  2. Tokenizes the query PRESERVING short electronics tokens (D1, V1, R3, S3,
     C3, 5V, 3V3) that the old Stage 11 splitter was dropping.
  3. Decides whether PlatformIO is allowed for this query (only dev_board).
  4. Detects known variants (e.g. ``d1 mini pro`` is a variant of ``d1 mini``)
     and known related parts (e.g. ``bmp280`` is related_to ``bme280``).
  5. Assigns each candidate a ``match_level`` (exact / variant / related /
     image_only / rejected).
  6. Computes a final ``confidence`` (0.0-1.0) and a human-readable
     ``confidence_reason``.
  7. Decides the ``source_quality`` and ``matched_sources`` for the candidate.

The module is PURE — no network, no DB. The frontend uses ``match_level`` to
render colored badges (Exact / Variant / Related / Image-only). Above the
hard 0.85 threshold, the system auto-confirms; below, the UI shows a
"Needs review" pill.

This module is EXTENDED next to ``quality.py`` (Stage 11). It does not modify
``quality.py``'s public surface.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 1. Component type classification
# ---------------------------------------------------------------------------
# Default Q2=C: hand-curated dict (~50 entries) + heuristic fallback.
# Each entry maps a normalized query substring -> component_type.
# The dict is checked first; the heuristic kicks in only for misses.

KNOWN_COMPONENT_DICT: Dict[str, str] = {
    # --- dev_board: Wemos / Lolin / ESP / Arduino / RPi / STM / Pico ---
    "wemos d1 mini": "dev_board",
    "wemos d1 mini pro": "dev_board",
    "wemos d1 mini lite": "dev_board",
    "wemos lolin d1 mini": "dev_board",
    "wemos d1": "dev_board",
    "wemos lolin": "dev_board",
    "nodemcu": "dev_board",
    "node mcu": "dev_board",
    "esp32 devkit v1": "dev_board",
    "esp32 devkit v4": "dev_board",
    "esp32 devkitc": "dev_board",
    "esp32-s3 devkitc": "dev_board",
    "esp32-c3 devkitc": "dev_board",
    "esp32 dev module": "dev_board",
    "esp32 wroom": "dev_board",
    "esp32 wrover": "dev_board",
    "esp8266": "dev_board",
    "esp-12": "dev_board",
    "esp-01": "dev_board",
    "arduino uno r3": "dev_board",
    "arduino uno": "dev_board",
    "arduino nano": "dev_board",
    "arduino mega": "dev_board",
    "arduino micro": "dev_board",
    "arduino pro mini": "dev_board",
    "arduino pro micro": "dev_board",
    "arduino leonardo": "dev_board",
    "arduino due": "dev_board",
    "arduino zero": "dev_board",
    "arduino mkr": "dev_board",
    "arduino nano every": "dev_board",
    "raspberry pi pico": "dev_board",
    "rpi pico": "dev_board",
    "raspberry pi 4": "dev_board",
    "raspberry pi 3": "dev_board",
    "raspberry pi zero": "dev_board",
    "raspberry pi 5": "dev_board",
    "raspberry pi pico w": "dev_board",
    "stm32f103": "dev_board",
    "stm32f4": "dev_board",
    "bluepill": "dev_board",
    "blackpill": "dev_board",
    "teensy 4": "dev_board",
    "teensy 3": "dev_board",
    "esp32": "dev_board",  # bare "esp32" alone defaults to dev_board
    "esp32-s3": "dev_board",
    "esp32-c3": "dev_board",
    "esp32-s2": "dev_board",
    "esp32-h2": "dev_board",
    # --- sensor_module ---
    "bme280": "sensor_module",
    "bmp280": "sensor_module",
    "bmp180": "sensor_module",
    "dht22": "sensor_module",
    "dht11": "sensor_module",
    "ds18b20": "sensor_module",
    "ina219": "sensor_module",
    "ina226": "sensor_module",
    "ina260": "sensor_module",
    "mpu6050": "sensor_module",
    "mpu9250": "sensor_module",
    "bmi270": "sensor_module",
    "bmi160": "sensor_module",
    "lidar": "sensor_module",
    "ultrasonic": "sensor_module",
    "hcsr04": "sensor_module",
    "mq-2": "sensor_module",
    "mq-135": "sensor_module",
    # --- display_module ---
    "ili9488": "display_module",
    "ili9341": "display_module",
    "ili9342": "display_module",
    "ssd1306": "display_module",
    "st7789": "display_module",
    "st7735": "display_module",
    "hd44780": "display_module",
    "nokia 5110": "display_module",
    "pcf8574": "display_module",  # I2C expander, treated as display-adjacent
    # --- touch_module ---
    "xpt2046": "touch_module",
    "ft6236": "touch_module",
    "gt911": "touch_module",
    # --- charger_power_module ---
    "tp4056": "charger_power_module",
    "bq25895": "charger_power_module",
    "bq24075": "charger_power_module",
    "mcp73831": "charger_power_module",
    "dw01": "charger_power_module",
    "ip5306": "charger_power_module",
    "mp1584": "charger_power_module",
    "lm2596": "charger_power_module",
    "mt3608": "charger_power_module",
    # --- ic_chip ---
    "lm358": "ic_chip",
    "lm324": "ic_chip",
    "ne555": "ic_chip",
    "tl072": "ic_chip",
    "ne5532": "ic_chip",
    "atmega328p": "ic_chip",
    "atmega32u4": "ic_chip",
    "attiny85": "ic_chip",
    "lm7805": "ic_chip",
    "lm7812": "ic_chip",
    "lm317": "ic_chip",
    "ams1117": "ic_chip",
    "a4988": "ic_chip",
    "drv8825": "ic_chip",
    "tmc2208": "ic_chip",
    "tmc2209": "ic_chip",
    "uln2003": "ic_chip",
    "ws2812": "ic_chip",  # addressable LED IC; treat as ic
    "ws2812b": "ic_chip",
    "neopixel": "ic_chip",  # alias
    "74hc595": "ic_chip",
    "pcf8574": "ic_chip",
    # --- passive ---
    "resistor": "passive",
    "capacitor": "passive",
    "inductor": "passive",
    "diode": "passive",
    "transistor": "passive",
    "crystal": "passive",
}


# Heuristic patterns. Applied only when the dict doesn't match. Order matters
# (more specific patterns first).
_HEURISTIC_TYPE_RULES: tuple[tuple[str, str], ...] = (
    # Dev boards
    (r"\b(dev\s?board|development\s+board)\b", "dev_board"),
    (r"\bdevkit\b", "dev_board"),
    (r"\b(wemos|lolin|nodemcu|teensy|bluepill|blackpill)\b", "dev_board"),
    (r"\b(uno|nano|mega|leonardo|micro)\b.*\b(r3|r2|r1)\b", "dev_board"),
    (r"\b(rpi|raspberry\s*pi)\b", "dev_board"),
    (r"\b(pico|picow)\b", "dev_board"),
    (r"\b(stm32[fx]\d+)\b", "dev_board"),
    (r"\b(esp32[-_]?[a-z0-9]*|esp8266)\b", "dev_board"),
    # Sensors
    (r"\b(sensor|module)\b", "sensor_module"),
    (r"^(bme|bmp|dht|ds18|ina|mpu|bmi|hcsr|mq-)", "sensor_module"),
    # Displays
    (r"\b(display|lcd|oled|tft|led\s*matrix|neopixel|ws2812|sk6812)\b", "display_module"),
    (r"^(ili|ssd|st7|hd44|nokia)", "display_module"),
    # Touch
    (r"\b(touch|touchscreen)\b", "touch_module"),
    (r"^(xpt|ft6|gt9)", "touch_module"),
    # Charger / power
    (r"\b(charger|charging|buck|boost|regulator|power\s*supply)\b", "charger_power_module"),
    (r"^(tp\d+|bq\d+|mcp738|dw01|ip53|mp15|lm2596|mt36)", "charger_power_module"),
    # ICs
    (r"\b(op-?amp|opamp|comparator|timer|ic|chip)\b", "ic_chip"),
    (r"^(lm\d+|ne\d+|tl\d+|attiny|atmega|pcf|drv|tmc|a4988|uln|74hc|74ls)", "ic_chip"),
    # Passive
    (r"\b(resistor|capacitor|inductor|diode|transistor|crystal)\b", "passive"),
)


def classify_query(query: str) -> str:
    """Return the component type for a free-text query.

    Default: dict lookup first, then heuristic fallback, then "unknown".

    Examples::

        >>> classify_query("Wemos D1 Mini")
        'dev_board'
        >>> classify_query("TP4056")
        'charger_power_module'
        >>> classify_query("ILI9488 XPT2046")
        'display_module'  # display wins; touch is secondary
    """
    q = (query or "").lower().strip()
    if not q:
        return "unknown"

    # 1) Direct dict lookup (longest key wins)
    best_key = ""
    best_type = ""
    for key, ctype in KNOWN_COMPONENT_DICT.items():
        if key in q and len(key) > len(best_key):
            best_key = key
            best_type = ctype
    if best_type:
        return best_type

    # 2) Heuristic fallback
    for pattern, ctype in _HEURISTIC_TYPE_RULES:
        if re.search(pattern, q, re.IGNORECASE):
            return ctype

    return "unknown"


# ---------------------------------------------------------------------------
# 2. Short-token-preserving tokenizer
# ---------------------------------------------------------------------------

# Short electronics tokens we MUST preserve (per NOFI's brief).
# These would normally be dropped by a `len(t) < 3` filter, but they're the
# whole point of a query like "Wemos D1 Mini", "ESP32 DevKit V1", "Arduino
# Uno R3", "5V regulator", "3V3 pin".
SHORT_TOKENS: Set[str] = {
    "d1", "v1", "r3", "s3", "c3", "c6", "a0", "5v", "3v3",
    "s2", "r4", "p4", "pico", "mini", "pro", "lite", "plus",
    "maxi", "xl", "v2", "v3", "v4", "h2",
    "uno", "nano", "mega", "due",  # short Arduino family names
    "rpi",
    # Voltage/pin tokens
    "vin", "vcc", "vdd", "vss", "gnd", "3v", "5v0",
}


def _is_short_token(tok: str) -> bool:
    """True if this short token should be preserved.

    A token is preserved if it is in ``SHORT_TOKENS`` OR it is < 3 chars but
    contains a digit (e.g. ``d1``, ``v1``, ``r3``, ``5v``).
    """
    if not tok:
        return False
    low = tok.lower()
    if low in SHORT_TOKENS:
        return True
    if len(tok) < 3 and re.search(r"\d", tok):
        return True
    return False


def tokenize_query(query: str) -> List[str]:
    """Tokenize a free-text query, preserving short electronics tokens.

    Differences from Stage 11 ``_query_tokens``:

    - Stage 11 only kept tokens of length >= 3. So "D1", "V1", "R3", "5V" all
      got dropped, which is exactly the bug NOFI reported.
    - This function keeps short tokens when they contain a digit OR are in the
      known short-token set.
    - The function returns BOTH the raw token (e.g. ``"D1"``) and a
      normalized form (e.g. ``"d1"``). Callers use whichever fits.
    - It also splits hyphenated forms like "ESP32-S3" into ["esp32", "s3"]
      so the variant detector can compare them.

    Pure alphanumeric+dash+dot+underscore splitter (same as Stage 11), with a
    second pass that splits on dash/dot for tokens that contain a digit.
    """
    q = (query or "").lower()
    raw = re.split(r"[^a-z0-9.-]+", q)
    out: List[str] = []
    for t in raw:
        if not t:
            continue
        if _is_short_token(t):
            out.append(t)
        elif len(t) >= 3 and re.search(r"[a-z0-9]", t):
            # Hyphen-split tokens that contain a digit: "esp32-s3" -> ["esp32", "s3"]
            if "-" in t and re.search(r"\d", t):
                for sub in t.split("-"):
                    sub = sub.strip(".")
                    if not sub:
                        continue
                    if _is_short_token(sub) or (len(sub) >= 3 and re.search(r"[a-z0-9]", sub)):
                        if sub not in out:
                            out.append(sub)
                continue
            out.append(t)
    return out


# ---------------------------------------------------------------------------
# 3. PlatformIO gating
# ---------------------------------------------------------------------------

# Component types that may use PlatformIO as an identity source.
# Boards: yes. Anything else: no.
PLATFORMIO_ALLOWED_TYPES: Set[str] = {"dev_board"}


def platformio_allowed(component_type: str) -> bool:
    """True if PlatformIO may be queried for this component type."""
    return component_type in PLATFORMIO_ALLOWED_TYPES


# ---------------------------------------------------------------------------
# 4. Variant detection (Q3=C: token-set + known dict)
# ---------------------------------------------------------------------------

# Known variants: a query like "D1 Mini" should be aware that "D1 Mini Pro"
# exists. Likewise "ESP32" should know that "ESP32-S3", "ESP32-C3" are
# related but different products.
#
# Mapping: lowercase variant name -> relation type.
#   - "variant_of:<base>"   = close variant of the base (Pro, Plus, v2, etc.)
#   - "related_to:<base>"   = same family but different product
#   - "image_of:<base>"     = the variant is just a photo of the base
KNOWN_VARIANTS: Dict[str, str] = {
    # Wemos D1 family
    "d1 mini pro": "variant_of:d1 mini",
    "d1 mini lite": "variant_of:d1 mini",
    "d1 mini v3": "variant_of:d1 mini",
    "d1 mini v2": "variant_of:d1 mini",
    "d1": "related_to:wemos d1",
    "wemos d1": "variant_of:wemos d1 mini",
    # ESP32 family
    "esp32-s3": "variant_of:esp32",
    "esp32-s2": "variant_of:esp32",
    "esp32-c3": "variant_of:esp32",
    "esp32-h2": "variant_of:esp32",
    "esp32-s3 devkitc": "variant_of:esp32 devkit v1",
    "esp32-c3 devkitc": "variant_of:esp32 devkit v1",
    "esp32-s3 devkitc-1": "variant_of:esp32 devkit v1",
    "esp32-c3 devkitm": "variant_of:esp32 devkit v1",
    # Arduino family
    "arduino uno r2": "variant_of:arduino uno r3",
    "arduino nano": "related_to:arduino",
    "arduino mega": "related_to:arduino",
    "arduino micro": "related_to:arduino",
    # Sensor family
    "bmp280": "related_to:bme280",  # same Bosch line, different sensor
    "bmp180": "related_to:bme280",
    # Display family
    "ili9341": "related_to:ili9488",
    "ili9342": "related_to:ili9488",
    "st7789": "related_to:ili9488",
    "ssd1306": "related_to:ili9488",  # OLED vs TFT, but both displays
    # Charger family
    "mcp73831": "related_to:tp4056",
    "bq25895": "related_to:tp4056",
    # IC family
    "lm324": "related_to:lm358",  # same op-amp family
    "ne5532": "related_to:lm358",
    "tl072": "related_to:lm358",
    # Op-amp LM358 is dual; LM324 is quad
    "tlc2274": "related_to:lm358",
    # Current sensor family
    "ina226": "related_to:ina219",
    "ina260": "related_to:ina219",
}


# Tokens that signal a variant (suffix-style). When the candidate title
# contains a variant token that the QUERY does NOT contain, it's a
# variant mismatch and the candidate is demoted.
# (Mirrors VARIANT_SUFFIXES in quality.py; duplicated here for the
# match-level classifier which runs BEFORE quality.py does the score work.)
VARIANT_SIGNAL_TOKENS: Set[str] = {
    "pro", "plus", "lite", "micro", "mini", "maxi", "xl",
    "v2", "v3", "v4", "v1.1", "v2.0",
    "s2", "s3", "c3", "h2",
    "esp32", "esp8266",
    "32u4", "168", "328", "328p",
    "r2", "r3",  # board rev markers
}


def detect_variant_mismatch(query: str, candidate: Dict[str, Any]) -> Optional[str]:
    """Return the variant token that mismatches, or None.

    A "mismatch" means: the candidate's title contains a token that signals
    a variant (e.g. "pro", "v2", "s3"), but the query does NOT contain it.
    Example: query "D1 Mini" vs candidate "D1 Mini Pro" -> "pro" mismatches.

    This is the FIRST-pass variant check. The known-variant dict above is
    consulted separately in ``match_level_for``.
    """
    if not query:
        return None
    q_norm = re.sub(r"[^a-z0-9]", " ", query.lower())
    title = (candidate.get("title") or candidate.get("name") or "").lower()
    title_norm = re.sub(r"[^a-z0-9]", " ", title)
    q_tokens = set(re.split(r"\s+", q_norm))
    t_tokens = set(re.split(r"\s+", title_norm))
    # Tokens present in title but NOT in query
    extras = t_tokens - q_tokens - {""}
    for tok in extras:
        if tok in VARIANT_SIGNAL_TOKENS:
            return tok
    return None


def match_level_for(
    query: str,
    candidate: Dict[str, Any],
    component_type: str,
) -> Tuple[str, str, float]:
    """Return (match_level, confidence_reason, confidence_boost).

    match_level is one of:
        - "exact"      = candidate is the same model the user asked for
        - "variant"    = known close variant (e.g. Pro, Plus, v2)
        - "related"    = same family but different product (e.g. BMP280 vs BME280)
        - "image_only" = candidate has only an image, no real identity match
        - "rejected"   = hard-rejected (not used here; quality.py handles hard rejects)

    confidence_boost is added to the Stage 11 quality score in the calling
    layer (so the 0.85 threshold check is calibrated).
    """
    title = (candidate.get("title") or candidate.get("name") or "").lower()
    title_norm = re.sub(r"[^a-z0-9]", " ", title)
    title_compact = re.sub(r"[^a-z0-9]", "", title)
    q_norm = query.lower().strip()
    q_compact = re.sub(r"[^a-z0-9]", "", q_norm)
    q_tokens = set(tokenize_query(q_norm))

    # 1. Image-only fallback: no token overlap at all -> image_only
    t_tokens = set(re.split(r"\s+", title_norm))
    t_tokens = {t for t in t_tokens if t}
    q_tokens_preserving_short = set(tokenize_query(q_norm))
    t_tokens_preserving_short = set(tokenize_query(title))
    overlap = q_tokens_preserving_short & t_tokens_preserving_short

    # 2. Exact: the candidate's compact title is contained in the query's
    #    compact form (or vice versa) AND the type matches.
    # Strict check: ALL query tokens (with short-token preservation) must
    # appear in the title. A "substring" match alone is not enough — e.g.
    # query "Arduino Uno R3" should NOT be exact for candidate "Arduino
    # Uno" (R3 is missing).
    if q_compact and title_compact:
        if q_compact == title_compact:
            return (
                "exact",
                f"Exact model tokens matched: {sorted(overlap)[:6] or [q_compact[:20]]}.",
                0.0,  # no extra boost; quality.py's existing score already
                      # rewards all-tokens-match
            )
        # Title is a SUPERSET of the query (e.g. "Wemos D1 Mini Front"
        # contains the query "Wemos D1 Mini" as a prefix). This is exact.
        if title_compact.startswith(q_compact):
            return (
                "exact",
                f"Exact prefix match on title.",
                0.0,
            )
        # All short-preserving query tokens appear in the title (e.g.
        # "Wemos D1 Mini" with title "Wemos D1 Mini ESP8266") — exact.
        if q_tokens_preserving_short and q_tokens_preserving_short.issubset(t_tokens_preserving_short):
            return (
                "exact",
                f"Exact model tokens matched: {sorted(overlap)[:6] or [q_compact[:20]]}.",
                0.0,
            )

    # 3. Known variant: title contains a known variant of the query
    for key, relation in KNOWN_VARIANTS.items():
        if key in title_compact:
            # relation is one of:
            #   - "variant_of:<base>"   = close variant (Pro, Plus, v2, ...)
            #   - "related_to:<base>"   = same family, different product
            #   - "image_of:<base>"     = the candidate is just a photo
            # Match if the relation's base matches the query's compact form.
            base = relation.split(":", 1)[1] if ":" in relation else relation
            if base != q_compact:
                continue
            if relation.startswith("variant_of"):
                return (
                    "variant",
                    f"Known variant of the queried model ({key!r}).",
                    -0.10,  # small penalty
                )
            if relation.startswith("related_to"):
                return (
                    "related",
                    f"Related part in the same family ({key!r}).",
                    -0.20,  # bigger penalty
                )
            if relation.startswith("image_of"):
                return (
                    "image_only",
                    f"Image-only candidate ({key!r}).",
                    -0.30,
                )

    # 4. Variant-mismatch signal: candidate has a variant token that the
    #    query doesn't. e.g. query "ESP32 DevKit V1", candidate "ESP32-S3 DevKitC"
    mismatch = detect_variant_mismatch(q_norm, candidate)
    if mismatch is not None:
        # If the title adds a "s3" but the query is "v1", this is a wrong
        # variant. Demote to "variant" (not exact).
        return (
            "variant",
            f"Variant mismatch: candidate has {mismatch!r}, query does not.",
            -0.25,
        )

    # 5. Token overlap but not exact: probably "related"
    if overlap:
        return (
            "related",
            f"Partial token overlap (shared: {sorted(overlap)[:6]}).",
            -0.10,
        )

    # 6. Image-only
    if candidate.get("image_url") and not overlap:
        return (
            "image_only",
            "Image found but no token overlap with query.",
            -0.30,
        )

    # 7. No signal at all
    return (
        "related",
        "Weak signal; fallback match.",
        -0.30,
    )


# ---------------------------------------------------------------------------
# 5. Source quality + matched_sources normalization
# ---------------------------------------------------------------------------

# Maps a raw source id (from live_search) to a human-readable source quality
# string. Order matters: more trusted first.
SOURCE_QUALITY_ORDER = (
    "vendor",        # Adafruit, SparkFun product page
    "datasheet",     # PDF datasheet
    "platformio",    # PlatformIO board page
    "wikipedia",     # Wikipedia article
    "wikidata",      # Wikidata entity
    "commons",       # Wikimedia Commons image
    "github",        # GitHub public repo
    "unknown",
)


def source_quality_for(candidate: Dict[str, Any]) -> str:
    """Return the highest-quality source present on this candidate."""
    srcs = candidate.get("matched_sources") or []
    srcs_l = {s.lower() for s in srcs}
    if "adafruit" in srcs_l or "vendor" in srcs_l or "sparkfun" in srcs_l or "pololu" in srcs_l:
        return "vendor"
    if isinstance(candidate.get("datasheet_url"), str) and candidate["datasheet_url"].lower().endswith(".pdf"):
        return "datasheet"
    if candidate.get("platformio_url") or "platformio" in srcs_l:
        return "platformio"
    if candidate.get("wikipedia_url") or "wikipedia" in srcs_l:
        return "wikipedia"
    if candidate.get("wikidata_id") or "wikidata" in srcs_l:
        return "wikidata"
    if candidate.get("image_url") and "commons" in srcs_l:
        return "wikimedia_commons"
    if "github" in srcs_l:
        return "github"
    return "unknown"


# ---------------------------------------------------------------------------
# 6. Final ranking (identity first, image second)
# ---------------------------------------------------------------------------

# Source-quality scores for ranking. Vendor > datasheet > platformio >
# wikipedia > wikidata > commons > github > unknown.
_SOURCE_QUALITY_SCORE: Dict[str, float] = {
    "vendor": 0.50,
    "datasheet": 0.45,
    "platformio": 0.40,
    "wikipedia": 0.30,
    "wikidata": 0.25,
    "wikimedia_commons": 0.10,
    "github": 0.05,
    "unknown": 0.00,
}

# Tier order: exact > variant > related > image_only > rejected
_MATCH_LEVEL_SCORE: Dict[str, float] = {
    "exact": 1.00,
    "variant": 0.50,
    "related": 0.20,
    "image_only": 0.05,
    "rejected": 0.00,
}


def rank_key(candidate: Dict[str, Any]) -> tuple:
    """Return a sort key that ranks candidates by:

        1. match_level (exact > variant > related > image_only)
        2. source quality (vendor > datasheet > platformio > ...)
        3. identity confidence (0.85 threshold check uses this)
        4. has image (image present boosts after identity)

    Use with ``sorted(candidates, key=rank_key, reverse=True)``.
    """
    ml = candidate.get("match_level", "related")
    sq = candidate.get("source_quality", "unknown")
    conf = float(candidate.get("confidence", 0.0))
    img = 1.0 if candidate.get("image_url") else 0.0
    return (
        _MATCH_LEVEL_SCORE.get(ml, 0.0),
        _SOURCE_QUALITY_SCORE.get(sq, 0.0),
        conf,
        img,
    )


# ---------------------------------------------------------------------------
# 7. Hard 0.85 threshold
# ---------------------------------------------------------------------------

# Per NOFI brief 5A: hard 0.85 threshold. Above = auto-confirm; below = needs review.
AUTO_CONFIRM_THRESHOLD = 0.85


def needs_review(candidate: Dict[str, Any]) -> bool:
    """True if the candidate is below the auto-confirm threshold."""
    return float(candidate.get("confidence", 0.0)) < AUTO_CONFIRM_THRESHOLD


# ---------------------------------------------------------------------------
# 8. Enrichment (vendor product page + datasheet + Wikipedia + Commons image)
# ---------------------------------------------------------------------------

# Per Q2 brief: candidate enrichment pulls:
#   - manufacturer/vendor product page URL
#   - public datasheet PDF URL
#   - Wikipedia/Wikidata entry
#   - Wikimedia Commons image URL
#
# In this stage we just NORMALIZE the enrichment fields a candidate
# already has. The actual fetching happens in live_search.get_detail().

def enrich_candidate(
    candidate: Dict[str, Any],
    *,
    component_type: str,
) -> Dict[str, Any]:
    """Mutate a candidate in-place to set identity-engine fields:

        - component_type
        - match_level
        - confidence_reason
        - source_quality
        - matched_sources (normalized)

    Does NOT touch ``confidence`` (that's quality.score_candidate's job).
    Does NOT touch the image URL (that's phase-2 of the search).
    """
    c = dict(candidate)
    c["component_type"] = component_type
    ml, reason, _ = match_level_for(c.get("query", ""), c, component_type)
    c["match_level"] = ml
    c["confidence_reason"] = reason
    c["source_quality"] = source_quality_for(c)
    # Normalize matched_sources: strip prefix like "wikidata:" -> "wikidata"
    raw_sources = c.get("matched_sources") or []
    norm_sources: List[str] = []
    for s in raw_sources:
        # Accept either a bare key like "wikidata" or a prefixed id like
        # "wikidata:Q12345"
        head = s.split(":", 1)[0].lower()
        if head and head not in norm_sources:
            norm_sources.append(head)
    c["matched_sources"] = norm_sources
    return c


__all__ = [
    "AUTO_CONFIRM_THRESHOLD",
    "KNOWN_COMPONENT_DICT",
    "KNOWN_VARIANTS",
    "PLATFORMIO_ALLOWED_TYPES",
    "SHORT_TOKENS",
    "VARIANT_SIGNAL_TOKENS",
    "classify_query",
    "detect_variant_mismatch",
    "enrich_candidate",
    "match_level_for",
    "needs_review",
    "platformio_allowed",
    "rank_key",
    "source_quality_for",
    "tokenize_query",
]
