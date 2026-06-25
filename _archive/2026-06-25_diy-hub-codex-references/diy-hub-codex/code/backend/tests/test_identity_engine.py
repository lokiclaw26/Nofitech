"""DIY-012 (Stage 12) — Component Identity Engine acceptance tests.

These tests verify the 8 NOFI acceptance cases:

  1. Wemos D1 Mini      -> top result exact, no "d1 mini pro" / "luftdata" / etc
  2. ESP32 DevKit V1    -> top result exact, no "esp32-s3" / "esp32-c3" / "devkitc"
  3. Arduino Uno R3     -> top result exact, has all 3 tokens (arduino/uno/r3)
  4. BME280             -> top result exact, no BMP280
  5. TP4056             -> top result exact, NO PlatformIO candidates anywhere
  6. LM358              -> top result exact, NO PlatformIO candidates anywhere
  7. INA219             -> top result exact, NO PlatformIO candidates anywhere
  8. ILI9488 XPT2046    -> top result exact, NO PlatformIO candidates anywhere

Tests are built around a STUBBED ``_fetch_*`` layer so they run without
the network. The stub layer fakes the partial candidates that each source
would return for a given query, then runs the same merge + rank + identity
pipeline that ``live_search.search()`` would. This isolates the identity
logic from network noise (which is what NOFI was complaining about).

Run with:
    cd code/backend && .venv/bin/python -m unittest tests.test_identity_engine -v
"""
from __future__ import annotations

import re
import sys
import unittest
from typing import Any, Callable, Dict, List, Tuple

# Ensure the ``app`` package is importable when this file is run from any
# working directory. Tests are run with ``cd code/backend && python -m unittest``.
sys.path.insert(0, ".")

from app import live_search  # noqa: E402
from app.identity import (  # noqa: E402
    KNOWN_COMPONENT_DICT,
    SHORT_TOKENS,
    classify_query,
    match_level_for,
    platformio_allowed,
    tokenize_query,
)
from app.quality import _all_tokens_match, _query_tokens  # noqa: E402


# ---------------------------------------------------------------------------
# Acceptance test cases (verbatim from DIY-012.md)
# ---------------------------------------------------------------------------

TEST_CASES: List[Dict[str, Any]] = [
    {
        "query": "Wemos D1 Mini",
        "match_level": "exact",
        "must_contain": ["wemos", "d1 mini"],
        "must_not_contain": ["d1 mini pro", "luftdata", "dvi sock", "front", "back"],
    },
    {
        "query": "ESP32 DevKit V1",
        "match_level": "exact",
        "must_contain": ["esp32", "devkit", "v1"],
        "must_not_contain": ["esp32-s3", "esp32-c3", "devkitc"],
    },
    {
        "query": "Arduino Uno R3",
        "match_level": "exact",
        "must_contain": ["arduino", "uno", "r3"],
        "must_not_contain": [],
    },
    {
        "query": "BME280",
        "match_level": "exact",
        "must_contain": ["bme280"],
        "must_not_contain": ["bmp280"],
    },
    {
        "query": "TP4056",
        "match_level": "exact",
        "must_contain": ["tp4056"],
        "must_not_contain": [],
        "no_platformio": True,
    },
    {
        "query": "LM358",
        "match_level": "exact",
        "must_contain": ["lm358"],
        "must_not_contain": [],
        "no_platformio": True,
    },
    {
        "query": "INA219",
        "match_level": "exact",
        "must_contain": ["ina219"],
        "must_not_contain": [],
        "no_platformio": True,
    },
    {
        "query": "ILI9488 XPT2046",
        "match_level": "exact",
        "must_contain": ["ili9488", "xpt2046"],
        "must_not_contain": [],
        "no_platformio": True,
    },
]


# ---------------------------------------------------------------------------
# Stubs: fake the 7 _fetch_* functions with canned partials.
# ---------------------------------------------------------------------------

# Each test has its own stub. The shape mirrors what _merge() expects:
#   {id, name (or title), image_url, wikidata_id, source_url, ...}

def _stub_wemos_d1_mini() -> List[Dict[str, Any]]:
    return [
        # PlatformIO board — Wemos D1 Mini (ESP8266)
        {
            "id": "platformio:d1_mini",
            "title": "WeMos D1 Mini",
            "name": "WeMos D1 Mini",
            "model_number": "d1_mini",
            "category": "Microcontroller",
            "platformio_url": "https://platformio.org/boards/d1_mini",
            "source_url": "https://platformio.org/boards/d1_mini",
            "tags": ["wemos", "esp8266"],
            "image_url": None,
        },
        # Wikimedia Commons — front photo (must be rejected by quality.py)
        {
            "id": "commons:Wemos_D1_mini_front.jpg",
            "title": "Wemos D1 Mini Front",
            "name": "Wemos D1 Mini Front",
            "model_number": "Unknown",
            "category": "Microcontroller",
            "commons_filename": "Wemos_D1_mini_front.jpg",
            "image_url": "https://upload.wikimedia.org/wikimedia/d1-mini-front.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File:Wemos_D1_mini_front.jpg",
        },
        # The WRONG candidate the user complained about: D1 Mini Pro
        {
            "id": "platformio:d1_mini_pro",
            "title": "Wemos D1 Mini Pro",
            "name": "Wemos D1 Mini Pro",
            "model_number": "d1_mini_pro",
            "category": "Microcontroller",
            "platformio_url": "https://platformio.org/boards/d1_mini_pro",
            "source_url": "https://platformio.org/boards/d1_mini_pro",
            "tags": ["wemos", "esp8266"],
            "image_url": None,
        },
        # A pollution candidate (Luftdata — a real project that uses D1 Mini)
        {
            "id": "github:luftdaten",
            "title": "luftdaten",
            "name": "luftdaten",
            "model_number": "Unknown",
            "category": "Microcontroller",
            "source_url": "https://github.com/opendata-stuttgart/luftdaten",
            "tags": ["wemos", "luftdata"],
            "image_url": None,
        },
        # A weird unrelated DVI-sock candidate
        {
            "id": "github:wemos-dvi-sock",
            "title": "wemos-d1-mini-dvi-sock",
            "name": "wemos-d1-mini-dvi-sock",
            "model_number": "Unknown",
            "category": "Other",
            "source_url": "https://github.com/someuser/wemos-d1-mini-dvi-sock",
            "tags": [],
            "image_url": None,
        },
    ]


def _stub_esp32_devkit_v1() -> List[Dict[str, Any]]:
    return [
        # The right one: a Wikidata / vendor entry that has the exact
        # name "ESP32 DevKit V1" (this is what the top result must be).
        {
            "id": "wikidata:Q12345",
            "title": "ESP32 DevKit V1",
            "name": "ESP32 DevKit V1",
            "model_number": "ESP32-DevKit-V1",
            "category": "Microcontroller",
            "wikidata_id": "Q12345",
            "wikidata_url": "https://www.wikidata.org/wiki/Q12345",
            "source_url": "https://www.wikidata.org/wiki/Q12345",
            "tags": ["esp32", "espressif", "devkit"],
            "image_url": None,
        },
        # PlatformIO board — ESP32 DevKit V1 (close, but stripped of V1)
        {
            "id": "platformio:esp32dev",
            "title": "Espressif ESP32 Dev Module",
            "name": "Espressif ESP32 Dev Module",
            "model_number": "esp32dev",
            "category": "Microcontroller",
            "platformio_url": "https://platformio.org/boards/espressif32/esp32dev",
            "source_url": "https://platformio.org/boards/espressif32/esp32dev",
            "tags": ["esp32", "espressif"],
            "image_url": None,
        },
        # WRONG: ESP32-S3 DevKitC-1
        {
            "id": "platformio:esp32-s3-devkitc-1",
            "title": "Espressif ESP32-S3-DevKitC-1",
            "name": "Espressif ESP32-S3-DevKitC-1",
            "model_number": "esp32-s3-devkitc-1",
            "category": "Microcontroller",
            "platformio_url": "https://platformio.org/boards/espressif32/esp32-s3-devkitc-1",
            "source_url": "https://platformio.org/boards/espressif32/esp32-s3-devkitc-1",
            "tags": ["esp32", "s3", "espressif"],
            "image_url": None,
        },
        # WRONG: ESP32-C3 DevKitM
        {
            "id": "platformio:esp32-c3-devkitm-1",
            "title": "Espressif ESP32-C3-DevKitM-1",
            "name": "Espressif ESP32-C3-DevKitM-1",
            "model_number": "esp32-c3-devkitm-1",
            "category": "Microcontroller",
            "platformio_url": "https://platformio.org/boards/espressif32/esp32-c3-devkitm-1",
            "source_url": "https://platformio.org/boards/espressif32/esp32-c3-devkitm-1",
            "tags": ["esp32", "c3", "espressif"],
            "image_url": None,
        },
    ]


def _stub_arduino_uno_r3() -> List[Dict[str, Any]]:
    return [
        {
            "id": "wikidata:Q54321",
            "title": "Arduino Uno R3",
            "name": "Arduino Uno R3",
            "model_number": "Uno R3",
            "category": "Microcontroller",
            "wikidata_id": "Q54321",
            "wikidata_url": "https://www.wikidata.org/wiki/Q54321",
            "source_url": "https://www.wikidata.org/wiki/Q54321",
            "tags": ["arduino", "uno", "r3"],
            "image_url": None,
        },
        {
            "id": "platformio:uno",
            "title": "Arduino Uno",
            "name": "Arduino Uno",
            "model_number": "uno",
            "category": "Microcontroller",
            "platformio_url": "https://platformio.org/boards/uno",
            "source_url": "https://platformio.org/boards/uno",
            "tags": ["arduino"],
            "image_url": None,
        },
    ]


def _stub_bme280() -> List[Dict[str, Any]]:
    return [
        # Right one
        {
            "id": "wikidata:Q17594232",
            "title": "BME280",
            "name": "BME280",
            "model_number": "BME280",
            "category": "Sensor",
            "wikidata_id": "Q17594232",
            "wikidata_url": "https://www.wikidata.org/wiki/Q17594232",
            "source_url": "https://www.wikidata.org/wiki/Q17594232",
            "tags": ["bosch", "sensor"],
            "image_url": None,
        },
        # WRONG: BMP280 (related but not the same)
        {
            "id": "wikidata:Q17594233",
            "title": "BMP280",
            "name": "BMP280",
            "model_number": "BMP280",
            "category": "Sensor",
            "wikidata_id": "Q17594233",
            "wikidata_url": "https://www.wikidata.org/wiki/Q17594233",
            "source_url": "https://www.wikidata.org/wiki/Q17594233",
            "tags": ["bosch", "sensor"],
            "image_url": None,
        },
    ]


def _stub_tp4056() -> List[Dict[str, Any]]:
    return [
        {
            "id": "wikidata:Q17005050",
            "title": "TP4056",
            "name": "TP4056",
            "model_number": "TP4056",
            "category": "Power",
            "wikidata_id": "Q17005050",
            "source_url": "https://www.wikidata.org/wiki/Q17005050",
            "tags": ["tp4056", "charger"],
            "matched_sources": ["wikidata"],
            "image_url": None,
        },
        # PlatformIO pollution: TP4056 is not a board, but PlatformIO
        # shouldn't show up at all. Stub it so we can verify it gets
        # dropped.
        {
            "id": "platformio:tp4056",
            "title": "TP4056",
            "name": "TP4056",
            "model_number": "tp4056",
            "category": "Power",
            "platformio_url": "https://platformio.org/boards/tp4056",
            "source_url": "https://platformio.org/boards/tp4056",
            "tags": ["tp4056"],
            "matched_sources": ["platformio"],
            "image_url": None,
        },
    ]


def _stub_lm358() -> List[Dict[str, Any]]:
    return [
        {
            "id": "wikidata:Q917257",
            "title": "LM358",
            "name": "LM358",
            "model_number": "LM358",
            "category": "Op-amp",
            "wikidata_id": "Q917257",
            "source_url": "https://www.wikidata.org/wiki/Q917257",
            "tags": ["lm358", "op-amp"],
            "matched_sources": ["wikidata"],
            "image_url": None,
        },
        {
            "id": "platformio:lm358",
            "title": "LM358",
            "name": "LM358",
            "model_number": "lm358",
            "category": "Op-amp",
            "platformio_url": "https://platformio.org/boards/lm358",
            "source_url": "https://platformio.org/boards/lm358",
            "tags": ["lm358"],
            "matched_sources": ["platformio"],
            "image_url": None,
        },
    ]


def _stub_ina219() -> List[Dict[str, Any]]:
    return [
        {
            "id": "wikidata:Q17005051",
            "title": "INA219",
            "name": "INA219",
            "model_number": "INA219",
            "category": "Sensor",
            "wikidata_id": "Q17005051",
            "source_url": "https://www.wikidata.org/wiki/Q17005051",
            "tags": ["ina219", "ti"],
            "matched_sources": ["wikidata"],
            "image_url": None,
        },
        {
            "id": "platformio:ina219",
            "title": "INA219",
            "name": "INA219",
            "model_number": "ina219",
            "category": "Sensor",
            "platformio_url": "https://platformio.org/boards/ina219",
            "source_url": "https://platformio.org/boards/ina219",
            "tags": ["ina219"],
            "matched_sources": ["platformio"],
            "image_url": None,
        },
    ]


def _stub_ili9488_xpt2046() -> List[Dict[str, Any]]:
    return [
        {
            "id": "wikidata:Q17005052",
            "title": "ILI9488 XPT2046",
            "name": "ILI9488 XPT2046",
            "model_number": "ILI9488",
            "category": "Display",
            "wikidata_id": "Q17005052",
            "source_url": "https://www.wikidata.org/wiki/Q17005052",
            "tags": ["ili9488", "xpt2046", "display"],
            "matched_sources": ["wikidata"],
            "image_url": None,
        },
        {
            "id": "platformio:ili9488",
            "title": "ILI9488",
            "name": "ILI9488",
            "model_number": "ili9488",
            "category": "Display",
            "platformio_url": "https://platformio.org/boards/ili9488",
            "source_url": "https://platformio.org/boards/ili9488",
            "tags": ["ili9488"],
            "matched_sources": ["platformio"],
            "image_url": None,
        },
    ]


# Map queries to their stub partials.
STUBS: Dict[str, List[Dict[str, Any]]] = {
    "Wemos D1 Mini": _stub_wemos_d1_mini(),
    "ESP32 DevKit V1": _stub_esp32_devkit_v1(),
    "Arduino Uno R3": _stub_arduino_uno_r3(),
    "BME280": _stub_bme280(),
    "TP4056": _stub_tp4056(),
    "LM358": _stub_lm358(),
    "INA219": _stub_ina219(),
    "ILI9488 XPT2046": _stub_ili9488_xpt2046(),
}


# ---------------------------------------------------------------------------
# Identity engine pipeline (testable form of live_search.search)
# ---------------------------------------------------------------------------

def _run_identity_pipeline(query: str) -> Dict[str, Any]:
    """Run the same merge + rank + identity-enrichment that live_search does.

    Uses the stub partials (no network). Returns a dict with the same
    shape as live_search.search()'s return value.
    """
    partials = STUBS.get(query, [])
    # Merge (one candidate per stub partial — the test stubs are already
    # de-duplicated)
    candidates = list(partials)
    # Compute confidence (mirrors live_search._confidence roughly)
    for c in candidates:
        c["confidence"] = _stub_confidence(c)
    # Quality filter
    from app.quality import rank_and_filter
    ranked = rank_and_filter(candidates, query)
    # Identity enrichment
    component_type = classify_query(query)
    pio_allowed = platformio_allowed(component_type)
    final = live_search._apply_identity_engine(
        ranked["candidates"], query, component_type
    )
    return {
        "query": query,
        "candidates": final,
        "component_type": component_type,
        "platformio_allowed": pio_allowed,
        "auto_confirm_threshold": 0.85,
        "best_confidence": max((c.get("confidence", 0.0) for c in final), default=0.0),
    }


def _stub_confidence(c: Dict[str, Any]) -> float:
    """Simple 0.0-1.0 confidence for a stub candidate.

    Mirrors quality.score_candidate's intent without the noise.
    """
    score = 0.30
    if c.get("image_url"):
        score += 0.20
    if c.get("wikidata_id"):
        score += 0.20
    if c.get("platformio_url"):
        score += 0.20
    if c.get("datasheet_url"):
        score += 0.10
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class ClassifyQueryTests(unittest.TestCase):
    """DIY-012 rule 1: classify queries into types."""

    def test_dev_boards(self):
        for q in ("Wemos D1 Mini", "ESP32 DevKit V1", "Arduino Uno R3",
                  "NodeMCU", "Raspberry Pi Pico", "STM32F103"):
            self.assertEqual(classify_query(q), "dev_board", q)

    def test_sensors(self):
        for q in ("BME280", "INA219", "DHT22", "DS18B20", "MPU6050"):
            self.assertEqual(classify_query(q), "sensor_module", q)

    def test_chargers(self):
        for q in ("TP4056", "BQ25895", "MCP73831"):
            self.assertEqual(classify_query(q), "charger_power_module", q)

    def test_ics(self):
        for q in ("LM358", "NE555", "ATmega328P", "WS2812B"):
            self.assertEqual(classify_query(q), "ic_chip", q)

    def test_displays(self):
        for q in ("ILI9488", "ILI9341", "SSD1306"):
            self.assertEqual(classify_query(q), "display_module", q)

    def test_touch(self):
        for q in ("XPT2046",):
            self.assertEqual(classify_query(q), "touch_module", q)

    def test_ili9488_xpt2046_prefers_display(self):
        # When both are mentioned, display wins (it's the more dominant
        # identity).
        self.assertEqual(classify_query("ILI9488 XPT2046"), "display_module")


class ShortTokenTests(unittest.TestCase):
    """DIY-012 rule 2: preserve short tokens like D1, V1, R3."""

    def test_preserves_d1(self):
        self.assertIn("d1", tokenize_query("Wemos D1 Mini"))

    def test_preserves_v1(self):
        self.assertIn("v1", tokenize_query("ESP32 DevKit V1"))

    def test_preserves_r3(self):
        self.assertIn("r3", tokenize_query("Arduino Uno R3"))

    def test_preserves_s3_c3(self):
        self.assertIn("s3", tokenize_query("ESP32-S3"))
        self.assertIn("c3", tokenize_query("ESP32-C3"))

    def test_short_token_set_documented(self):
        for tok in ("d1", "v1", "r3", "s3", "c3", "5v", "3v3", "uno", "nano"):
            self.assertIn(tok, SHORT_TOKENS, f"{tok!r} must be in SHORT_TOKENS")


class PlatformIOGateTests(unittest.TestCase):
    """DIY-012 rule 3: PlatformIO only for dev_board."""

    def test_dev_board_allows_platformio(self):
        self.assertTrue(platformio_allowed("dev_board"))

    def test_other_types_block_platformio(self):
        for t in ("sensor_module", "display_module", "touch_module",
                  "charger_power_module", "ic_chip", "passive", "unknown"):
            self.assertFalse(platformio_allowed(t), t)


class MatchLevelTests(unittest.TestCase):
    """DIY-012 rule 4: classify candidates as exact / variant / related / image_only."""

    def _cand(self, title, **kw):
        return {"id": "test", "name": title, "title": title, **kw}

    def test_exact_match(self):
        ml, reason, boost = match_level_for(
            "Wemos D1 Mini", self._cand("Wemos D1 Mini"), "dev_board"
        )
        self.assertEqual(ml, "exact")

    def test_variant_mismatch_demoted(self):
        ml, _, _ = match_level_for(
            "ESP32 DevKit V1", self._cand("ESP32-S3 DevKitC-1"), "dev_board"
        )
        self.assertIn(ml, ("variant", "related"))

    def test_related_same_family(self):
        ml, _, _ = match_level_for(
            "BME280", self._cand("BMP280"), "sensor_module"
        )
        self.assertEqual(ml, "related")

    def test_image_only_when_no_overlap(self):
        ml, _, _ = match_level_for(
            "BME280", self._cand("Some Random Photo", image_url="https://x/y.jpg"),
            "sensor_module",
        )
        self.assertEqual(ml, "image_only")


class VariantDetectionTests(unittest.TestCase):
    """DIY-012 rule 6: variant detection."""

    def test_d1_mini_pro_is_variant_of_d1_mini(self):
        from app.identity import detect_variant_mismatch
        m = detect_variant_mismatch("D1 Mini", {"title": "Wemos D1 Mini Pro"})
        self.assertEqual(m, "pro")

    def test_no_mismatch_for_exact(self):
        from app.identity import detect_variant_mismatch
        m = detect_variant_mismatch("Wemos D1 Mini", {"title": "Wemos D1 Mini"})
        self.assertIsNone(m)

    def test_v1_query_rejects_s3(self):
        from app.identity import detect_variant_mismatch
        m = detect_variant_mismatch(
            "ESP32 DevKit V1", {"title": "ESP32-S3 DevKitC"}
        )
        # The mismatch detector looks for tokens in title that aren't in query.
        self.assertIsNotNone(m)


class IdentityEngineAcceptanceTests(unittest.TestCase):
    """The 8 NOFI acceptance cases."""

    def _check(self, tc: Dict[str, Any]) -> None:
        result = _run_identity_pipeline(tc["query"])
        candidates = result["candidates"]
        self.assertGreater(
            len(candidates), 0,
            f"{tc['query']!r}: expected at least 1 candidate, got 0. "
            f"Result: {result}",
        )
        top = candidates[0]
        # match_level check
        self.assertEqual(
            top.get("match_level"), tc["match_level"],
            f"{tc['query']!r}: top match_level expected {tc['match_level']!r}, "
            f"got {top.get('match_level')!r}. Top: {top.get('title') or top.get('name')!r}",
        )
        # must_contain check (against the top candidate's title/name, lowercased)
        haystack = (
            (top.get("title") or "") + " " + (top.get("name") or "")
        ).lower()
        for tok in tc["must_contain"]:
            self.assertIn(
                tok, haystack,
                f"{tc['query']!r}: top result {haystack!r} must contain {tok!r}",
            )
        # must_not_contain check: walk the entire candidates list and make
        # sure none of them is the bad variant.
        all_titles = " | ".join(
            (c.get("title") or c.get("name") or "").lower() for c in candidates
        )
        for bad in tc["must_not_contain"]:
            self.assertNotIn(
                bad.lower(), all_titles,
                f"{tc['query']!r}: result list contains forbidden token "
                f"{bad!r} in: {all_titles!r}",
            )
        # no_platformio check: NO candidate in the result list may have a
        # platformio_url (because PlatformIO shouldn't even be queried for
        # this component_type).
        if tc.get("no_platformio"):
            for c in candidates:
                self.assertFalse(
                    c.get("platformio_url"),
                    f"{tc['query']!r}: result has platformio pollution: "
                    f"{c.get('title') or c.get('name')!r}",
                )
        # Print a one-line summary for the test log
        print(
            f"  -> {tc['query']!r}: top={top.get('title') or top.get('name')!r}, "
            f"match_level={top.get('match_level')!r}, confidence={top.get('confidence')!r}"
        )

    def test_wemos_d1_mini(self):
        self._check(TEST_CASES[0])

    def test_esp32_devkit_v1(self):
        self._check(TEST_CASES[1])

    def test_arduino_uno_r3(self):
        self._check(TEST_CASES[2])

    def test_bme280(self):
        self._check(TEST_CASES[3])

    def test_tp4056(self):
        self._check(TEST_CASES[4])

    def test_lm358(self):
        self._check(TEST_CASES[5])

    def test_ina219(self):
        self._check(TEST_CASES[6])

    def test_ili9488_xpt2046(self):
        self._check(TEST_CASES[7])


class OldQualityBehaviorTests(unittest.TestCase):
    """DIY-012 rule: don't break Stage 11 quality.py.

    Smoke-tests that the public surface of quality.py still works.
    """

    def test_rank_and_filter_returns_shape(self):
        from app.quality import rank_and_filter
        raws = [
            {"id": "a", "title": "Wemos D1 Mini", "name": "Wemos D1 Mini"},
            {"id": "b", "title": "Wemos D1 Mini Pro", "name": "Wemos D1 Mini Pro"},
            {"id": "tutorial", "title": "Wemos D1 Mini tutorial", "name": "tutorial"},
        ]
        out = rank_and_filter(raws, "Wemos D1 Mini")
        self.assertIn("candidates", out)
        self.assertIn("rejected_count", out)
        self.assertIn("quality_threshold", out)
        self.assertIn("best_confidence", out)
        # The tutorial must be rejected
        titles = [c.get("title") for c in out["candidates"]]
        self.assertNotIn("Wemos D1 Mini tutorial", titles)


class VerifiedCacheTests(unittest.TestCase):
    """DIY-012 rule 10: verified_components table works.

    Uses a temp DB so it doesn't pollute the real one.
    """

    def setUp(self):
        import os
        import tempfile
        from app import db
        self._orig_db_path = db._DB_PATH
        self._tmpdir = tempfile.mkdtemp()
        db._DB_PATH = type(db._DB_PATH)(self._tmpdir) / "test.db"
        # Re-import the cache module so it picks up the new path
        import importlib
        import app.identity_cache
        importlib.reload(app.identity_cache)
        # Re-init the schema
        from app.init_db import init_db
        init_db()

    def tearDown(self):
        from app import db
        db._DB_PATH = self._orig_db_path
        import importlib
        import app.identity_cache
        importlib.reload(app.identity_cache)

    def test_put_and_get_verified(self):
        from app.identity_cache import get_verified, put_verified
        put_verified(
            query="Wemos D1 Mini",
            canonical_name="Wemos D1 Mini",
            manufacturer="Wemos",
            model_number="D1 Mini",
            component_type="dev_board",
            interfaces=["WiFi", "USB"],
            specs={"mcu": "ESP-12F", "flash_mb": 4},
        )
        hit = get_verified("Wemos D1 Mini")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["canonical_name"], "Wemos D1 Mini")
        self.assertEqual(hit["interfaces"], ["WiFi", "USB"])
        self.assertEqual(hit["specs"]["mcu"], "ESP-12F")

    def test_rejected_signature_round_trip(self):
        from app.identity_cache import (
            candidate_signature,
            get_rejected_signatures,
            put_rejected,
        )
        cand = {"title": "Wemos D1 Mini Pro", "source_url": "https://x.com/p"}
        sig = candidate_signature(cand)
        put_rejected("Wemos D1 Mini", cand, reason="not what I asked for")
        rejected = get_rejected_signatures("Wemos D1 Mini")
        self.assertIn(sig, rejected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
