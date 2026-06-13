"""Free-text query parser for DIY Hub V1 (Stage 4).

NOFI redesign: the Add Component form is now a single text input. The
backend AI parses the query to identify the component and its model, then
returns 1+ candidates.

This is a **rule-based keyword parser**, not a real LLM. Per NOFI's
explicit constraints:
    - NO Google
    - NO Octopart
    - NO paid APIs
    - NO API keys
    - NO login
    - NO purchasing

If NOFI later wants a real LLM, that's a separate stage with explicit
approval. The rule-based parser satisfies the spirit of "the AI
figures out what it is" while respecting the constraints.

Approach
--------
1. Lowercase the query.
2. Match keywords to a known family (esp32, arduino, raspberry pi,
   neopixel/ws2812, servo, lm7805, lm358, stm32, ...).
3. Within the family, pick a specific model candidate based on additional
   keywords (e.g. "devkit" -> DevKit V1, "wroom" -> WROOM-32,
   "s3" -> S3, "uno" -> Uno R3, "nano" -> Nano,
   "mega" -> Mega 2560, "pi 4" -> Pi 4, "zero" -> Pi Zero W).
4. If the family matches but the model is ambiguous (e.g. user types
   just "esp32"), return all candidates for the family so the user
   picks one.
5. If no family matches, return a synthetic candidate based on the
   raw query. Image and spec fields will be null/unknown.

The candidate dicts are imported from :mod:`app.mock_data`.
"""
from __future__ import annotations

import re
from typing import List

from . import mock_data
from .mock_data import Candidate


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    """True if any of the needles (already-lowercased) appear in haystack."""
    return any(n in haystack for n in needles)


def _esp32(query: str) -> List[Candidate]:
    """Disambiguate within the ESP32 family."""
    if _has_any(query, ("s3", "esp32-s3")):
        return [c for c in mock_data.ESP32_CANDIDATES if c["id"] == "esp32-s3"]
    if _has_any(query, ("wroom",)):
        return [c for c in mock_data.ESP32_CANDIDATES if c["id"] == "esp32-wroom-32"]
    if _has_any(query, ("devkit", "dev kit", "v1",)):
        return [c for c in mock_data.ESP32_CANDIDATES if c["id"] == "esp32-devkit-v1"]
    # Family matched but model ambiguous — show all 3.
    return list(mock_data.ESP32_CANDIDATES)


def _arduino(query: str) -> List[Candidate]:
    if _has_any(query, ("uno",)):
        return [c for c in mock_data.ARDUINO_CANDIDATES if c["id"] == "arduino-uno-r3"]
    if _has_any(query, ("nano",)):
        return [c for c in mock_data.ARDUINO_CANDIDATES if c["id"] == "arduino-nano"]
    if _has_any(query, ("mega",)):
        return [c for c in mock_data.ARDUINO_CANDIDATES if c["id"] == "arduino-mega-2560"]
    return list(mock_data.ARDUINO_CANDIDATES)


def _raspberry(query: str) -> List[Candidate]:
    # Order matters: "zero" must be checked before "pi" alone.
    if _has_any(query, ("zero",)):
        return [c for c in mock_data.RASPBERRY_CANDIDATES if c["id"] == "raspberry-pi-zero-w"]
    if _has_any(query, ("4", "iv")) and "pi" in query:
        return [c for c in mock_data.RASPBERRY_CANDIDATES if c["id"] == "raspberry-pi-4b"]
    if "pi" in query or "raspberry" in query:
        return list(mock_data.RASPBERRY_CANDIDATES)
    return list(mock_data.RASPBERRY_CANDIDATES)


def _neopixel(query: str) -> List[Candidate]:
    if "sk6812" in query or "rgbw" in query:
        return [c for c in mock_data.NEOPIXEL_CANDIDATES if c["id"] == "neopixel-sk6812"]
    if "ws2812" in query or "neopixel" in query or "rgb" in query:
        return [c for c in mock_data.NEOPIXEL_CANDIDATES if c["id"] == "neopixel-ws2812b"]
    return list(mock_data.NEOPIXEL_CANDIDATES)


def _servo(query: str) -> List[Candidate]:
    if "mg996" in query or "996" in query:
        return [c for c in mock_data.SERVO_CANDIDATES if c["id"] == "servo-mg996r"]
    if "sg90" in query or "sg-90" in query or "servo" in query:
        return [c for c in mock_data.SERVO_CANDIDATES if c["id"] == "servo-sg90"]
    return list(mock_data.SERVO_CANDIDATES)


def _stm32(query: str) -> List[Candidate]:
    if "black" in query or "f4" in query:
        return [mock_data._synthesize_candidate("STM32 Black Pill", "F411")]
    if "blue" in query or "f103" in query or "c8t6" in query:
        return [c for c in _synthetic_stm32_blue_pill()]
    return _synthetic_stm32_blue_pill()


def _synthetic_stm32_blue_pill() -> List[Candidate]:
    """STM32 Blue Pill — synthesized inline since it's a single candidate."""
    return [{
        "id": "stm32-blue-pill",
        "name": "STM32 Blue Pill",
        "model_number": "F103C8T6",
        "category": "Microcontroller",
        "voltage": "3.3V",
        "interfaces": ["USB", "SPI", "I2C", "UART", "CAN"],
        "key_specs": [
            "ARM Cortex-M3",
            "72 MHz",
            "64 KB flash",
            "20 KB SRAM",
        ],
        "tags": ["stm32", "arm", "cortex-m3", "blue-pill"],
        "datasheet_url": "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
        "source_url": "https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html",
        "wikipedia_title": "STM32",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Core_Learning_Board_module_Arduino_STM32_F103_C8T6.jpg/500px-Core_Learning_Board_module_Arduino_STM32_F103_C8T6.jpg",
    }]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

def parse_query(query: str) -> List[Candidate]:
    """Parse a free-text query and return 1+ candidate components.

    Always returns at least one candidate (synthetic fallback).
    """
    if not query or not query.strip():
        return []
    q = query.lower().strip()
    # Normalize: collapse multiple spaces, strip punctuation that breaks
    # the keyword `in` checks.
    q = re.sub(r"[\s,;:.!?]+", " ", q).strip()

    # Family dispatch (most specific keywords first).
    if "esp32" in q or "espressif" in q:
        return _esp32(q)
    if "arduino" in q or ("uno" in q and "raspberry" not in q):
        return _arduino(q)
    if "raspberry" in q or ("pi" in q and "raspberry" in q):
        return _raspberry(q)
    if "neopixel" in q or "ws2812" in q or "sk6812" in q or "rgbw" in q:
        return _neopixel(q)
    if "servo" in q or "sg90" in q or "mg996" in q:
        return _servo(q)
    if "lm7805" in q or "7805" in q or "78xx" in q:
        return list(mock_data.LM7805_CANDIDATES)
    if "lm358" in q or "op-amp" in q or "opamp" in q:
        return list(mock_data.LM358_CANDIDATES)
    if "stm32" in q or "blue pill" in q or "black pill" in q or "f103" in q:
        return _stm32(q)

    # No family match — synthetic.
    # Split the query on whitespace to get a name + a tentative model.
    parts = q.split(" ", 1)
    if len(parts) == 1:
        name = parts[0]
        model_number = "Unknown"
    else:
        name, model_number = parts[0], parts[1]
    return [mock_data._synthesize_candidate(name, model_number)]


__all__ = ["parse_query"]
