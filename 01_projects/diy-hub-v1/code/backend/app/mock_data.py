"""Mock component catalog for DIY Hub V1 (Stage 2).

NOFI explicit: NO remote calls. This module is the local-only source of
truth for the search and image-generation endpoints. The keys are real
component prefixes (esp32, arduino, raspberry, neopixel, servo, lm7805,
lm358). When a user-supplied name doesn't match any prefix, the
``search_components`` function returns one synthetic candidate so the
flow always has something to render.

Each candidate carries enough metadata for the confirmation popup:
name, model_number, category, voltage, interfaces (list), key_specs
(list), tags (list), datasheet_url, source_url, and a deferred
``mock_image_data`` field that is generated on demand by
``generate_mock_svg`` (category-coloured 400x400 square, name + model
centered).

The URLs in this module are display strings only — they are never
fetched, in line with the Stage 2 no-remote-calls constraint.
"""
from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from typing import Callable, Dict, List, Optional, TypedDict


# 5-7 background colours keyed by category. Kept tasteful + readable.
CATEGORY_COLORS: Dict[str, str] = {
    "Microcontroller": "#1e3a8a",  # deep blue
    "Sensor": "#047857",            # green
    "Motor": "#b45309",             # amber
    "Power": "#7c2d12",             # burnt orange
    "Display": "#6d28d9",           # purple
    "LED": "#be185d",               # pink
    "Other": "#475569",             # slate
}


class Candidate(TypedDict, total=False):
    id: str
    name: str
    model_number: str
    category: str
    voltage: str
    interfaces: List[str]
    key_specs: List[str]
    tags: List[str]
    datasheet_url: str
    source_url: str
    mock_image_data: str  # raw SVG string


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

ESP32_CANDIDATES: List[Candidate] = [
    {
        "id": "esp32-devkit-v1",
        "name": "ESP32 DevKit V1",
        "model_number": "DevKit V1",
        "category": "Microcontroller",
        "voltage": "3.3V",
        "interfaces": ["WiFi", "Bluetooth", "GPIO", "I2C", "SPI", "UART"],
        "key_specs": [
            "Xtensa LX6 dual-core",
            "240 MHz",
            "520 KB SRAM",
            "4 MB flash",
        ],
        "tags": ["esp32", "wifi", "bluetooth", "iot", "espressif"],
        "datasheet_url": "https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf",
        "source_url": "https://www.espressif.com/en/products/socs/esp32",
    },
    {
        "id": "esp32-wroom-32",
        "name": "ESP32-WROOM-32",
        "model_number": "WROOM-32",
        "category": "Microcontroller",
        "voltage": "3.3V",
        "interfaces": ["WiFi", "Bluetooth", "GPIO", "I2C", "SPI", "UART"],
        "key_specs": [
            "Xtensa LX6 dual-core",
            "240 MHz",
            "520 KB SRAM",
            "4 MB flash",
            "Module form factor",
        ],
        "tags": ["esp32", "wifi", "bluetooth", "module", "espressif"],
        "datasheet_url": "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf",
        "source_url": "https://www.espressif.com/en/products/modules/esp32",
    },
    {
        "id": "esp32-s3",
        "name": "ESP32-S3",
        "model_number": "S3",
        "category": "Microcontroller",
        "voltage": "3.3V",
        "interfaces": ["WiFi", "Bluetooth 5", "USB OTG", "GPIO", "I2C", "SPI"],
        "key_specs": [
            "Xtensa LX7 dual-core",
            "240 MHz",
            "512 KB SRAM",
            "Vector instructions for AI/ML",
        ],
        "tags": ["esp32", "wifi", "bluetooth", "ai", "espressif"],
        "datasheet_url": "https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf",
        "source_url": "https://www.espressif.com/en/products/socs/esp32-s3",
    },
]

ARDUINO_CANDIDATES: List[Candidate] = [
    {
        "id": "arduino-uno-r3",
        "name": "Arduino Uno R3",
        "model_number": "Uno R3",
        "category": "Microcontroller",
        "voltage": "5V",
        "interfaces": ["USB-B", "GPIO", "I2C", "SPI", "UART", "ICSP"],
        "key_specs": [
            "ATmega328P",
            "16 MHz",
            "2 KB SRAM",
            "32 KB flash",
            "14 digital I/O pins",
        ],
        "tags": ["arduino", "atmega", "beginner", "open-source"],
        "datasheet_url": "https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf",
        "source_url": "https://store.arduino.cc/products/arduino-uno-rev3",
    },
    {
        "id": "arduino-nano",
        "name": "Arduino Nano",
        "model_number": "Nano",
        "category": "Microcontroller",
        "voltage": "5V",
        "interfaces": ["Mini-USB", "GPIO", "I2C", "SPI", "UART"],
        "key_specs": [
            "ATmega328P",
            "16 MHz",
            "2 KB SRAM",
            "32 KB flash",
            "Breadboard-friendly form factor",
        ],
        "tags": ["arduino", "atmega", "compact", "open-source"],
        "datasheet_url": "https://docs.arduino.cc/resources/datasheets/A000005-datasheet.pdf",
        "source_url": "https://store.arduino.cc/products/arduino-nano",
    },
    {
        "id": "arduino-mega-2560",
        "name": "Arduino Mega 2560",
        "model_number": "Mega 2560",
        "category": "Microcontroller",
        "voltage": "5V",
        "interfaces": ["USB-B", "GPIO", "I2C", "SPI", "UART", "ICSP"],
        "key_specs": [
            "ATmega2560",
            "16 MHz",
            "8 KB SRAM",
            "256 KB flash",
            "54 digital I/O pins",
        ],
        "tags": ["arduino", "atmega", "large", "open-source"],
        "datasheet_url": "https://docs.arduino.cc/resources/datasheets/A000067-datasheet.pdf",
        "source_url": "https://store.arduino.cc/products/arduino-mega-2560-rev3",
    },
]

RASPBERRY_CANDIDATES: List[Candidate] = [
    {
        "id": "raspberry-pi-4b",
        "name": "Raspberry Pi 4 Model B",
        "model_number": "Pi 4 Model B",
        "category": "Microcontroller",
        "voltage": "5V",
        "interfaces": ["USB-C", "HDMI x2", "GPIO", "I2C", "SPI", "Ethernet", "WiFi"],
        "key_specs": [
            "Broadcom BCM2711 quad-core Cortex-A72",
            "1.5 GHz",
            "1/2/4/8 GB RAM",
            "MicroSD boot",
        ],
        "tags": ["raspberry-pi", "linux", "sbc", "wifi"],
        "datasheet_url": "https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf",
        "source_url": "https://www.raspberrypi.com/products/raspberry-pi-4-model-b/",
    },
    {
        "id": "raspberry-pi-zero-w",
        "name": "Raspberry Pi Zero W",
        "model_number": "Pi Zero W",
        "category": "Microcontroller",
        "voltage": "5V",
        "interfaces": ["Mini-HDMI", "Micro-USB", "GPIO", "I2C", "SPI", "WiFi"],
        "key_specs": [
            "Broadcom BCM2835 single-core",
            "1 GHz",
            "512 MB RAM",
            "Compact form factor",
        ],
        "tags": ["raspberry-pi", "linux", "sbc", "compact", "wifi"],
        "datasheet_url": "https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-product-brief.pdf",
        "source_url": "https://www.raspberrypi.com/products/raspberry-pi-zero/",
    },
]

NEOPIXEL_CANDIDATES: List[Candidate] = [
    {
        "id": "ws2812b-5050",
        "name": "WS2812B 5050",
        "model_number": "WS2812B",
        "category": "LED",
        "voltage": "5V",
        "interfaces": ["Single-wire digital", "GPIO"],
        "key_specs": [
            "5050 RGB LED",
            "24-bit color",
            "Individually addressable",
            "Built-in driver",
        ],
        "tags": ["led", "rgb", "addressable", "neopixel", "ws2812"],
        "datasheet_url": "https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf",
        "source_url": "https://www.adafruit.com/category/168",
    },
    {
        "id": "sk6812-rgbw",
        "name": "SK6812 RGBW",
        "model_number": "SK6812",
        "category": "LED",
        "voltage": "5V",
        "interfaces": ["Single-wire digital", "GPIO"],
        "key_specs": [
            "5050 RGBW LED",
            "32-bit color (with white channel)",
            "Individually addressable",
            "Drop-in WS2812B replacement",
        ],
        "tags": ["led", "rgbw", "addressable", "neopixel", "sk6812"],
        "datasheet_url": "https://cdn-shop.adafruit.com/product-files/2757/p2757_SK6812RGBW_REV01.pdf",
        "source_url": "https://www.adafruit.com/product/2757",
    },
]

SERVO_CANDIDATES: List[Candidate] = [
    {
        "id": "servo-sg90",
        "name": "SG90 Micro Servo",
        "model_number": "SG90",
        "category": "Motor",
        "voltage": "4.8V - 6V",
        "interfaces": ["PWM", "3-wire (signal, power, ground)"],
        "key_specs": [
            "180-degree rotation",
            "1.8 kg-cm torque",
            "Plastic gears",
            "9g weight",
        ],
        "tags": ["servo", "micro", "pwm", "beginner"],
        "datasheet_url": "https://www.towerpro.com.tw/product/sg90-7/",
        "source_url": "https://www.adafruit.com/product/169",
    },
    {
        "id": "servo-mg996r",
        "name": "MG996R High-Torque Servo",
        "model_number": "MG996R",
        "category": "Motor",
        "voltage": "4.8V - 7.2V",
        "interfaces": ["PWM", "3-wire (signal, power, ground)"],
        "key_specs": [
            "180-degree rotation",
            "10-11 kg-cm torque",
            "Metal gears",
            "55g weight",
        ],
        "tags": ["servo", "high-torque", "metal-gears", "pwm"],
        "datasheet_url": "https://www.towerpro.com.tw/product/mg996r/",
        "source_url": "https://www.adafruit.com/product/1142",
    },
]

LM7805_CANDIDATES: List[Candidate] = [
    {
        "id": "lm7805-regulator",
        "name": "LM7805 5V Regulator",
        "model_number": "LM7805",
        "category": "Power",
        "voltage": "5V output (7-35V input)",
        "interfaces": ["Vin", "GND", "Vout"],
        "key_specs": [
            "1.5A output current",
            "TO-220 package",
            "Thermal overload protection",
            "Short-circuit protection",
        ],
        "tags": ["regulator", "linear", "5v", "power"],
        "datasheet_url": "https://www.ti.com/lit/ds/symlink/lm7805.pdf",
        "source_url": "https://www.ti.com/product/LM7805",
    },
]

LM358_CANDIDATES: List[Candidate] = [
    {
        "id": "lm358-opamp",
        "name": "LM358 Op-Amp",
        "model_number": "LM358",
        "category": "Other",
        "voltage": "3V - 32V single supply",
        "interfaces": ["In+", "In-", "Vcc", "GND", "Out"],
        "key_specs": [
            "Dual op-amp",
            "1 MHz gain-bandwidth",
            "Low power",
            "8-pin DIP/SOIC",
        ],
        "tags": ["op-amp", "analog", "signal-conditioning"],
        "datasheet_url": "https://www.ti.com/lit/ds/symlink/lm358.pdf",
        "source_url": "https://www.ti.com/product/LM358",
    },
]


# Order matters: most-specific prefix first.
PREFIX_TABLE: List[tuple[tuple[str, ...], List[Candidate], str]] = [
    (("esp32",), ESP32_CANDIDATES, "ESP32 family"),
    (("arduino", "uno"), ARDUINO_CANDIDATES, "Arduino family"),
    (("raspberry", "pi"), RASPBERRY_CANDIDATES, "Raspberry Pi family"),
    (("neopixel", "ws2812"), NEOPIXEL_CANDIDATES, "Neopixel / WS2812 family"),
    (("servo", "sg90"), SERVO_CANDIDATES, "Servo family"),
    (("lm7805", "7805"), LM7805_CANDIDATES, "LM7805 regulator"),
    (("lm358",), LM358_CANDIDATES, "LM358 op-amp"),
]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _slugify(text: str, max_length: int = 60) -> str:
    """Lowercase, alphanumerics only, joined by dashes. Used for image filenames."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_length] if s else "component"


def _match_prefix(name: str, model_number: str) -> Optional[List[Candidate]]:
    """Return the candidate list whose prefix appears in name OR model_number."""
    haystack = f"{name} {model_number}".lower()
    for prefixes, candidates, _label in PREFIX_TABLE:
        for p in prefixes:
            if p in haystack:
                return candidates
    return None


def _synthesize_candidate(name: str, model_number: str) -> Candidate:
    """Build a generic candidate when the prefix table doesn't match.

    Keeps the flow alive for any input: the user always sees a confirmation
    popup they can either accept (save) or cancel.
    """
    base = _slugify(f"{name} {model_number}", max_length=40)
    return {
        "id": f"generic-{base}-{uuid.uuid4().hex[:6]}",
        "name": name.strip() or "Unknown Component",
        "model_number": model_number.strip() or "Unknown",
        "category": "Other",
        "voltage": "Unknown",
        "interfaces": [],
        "key_specs": ["User-supplied — not in local catalog"],
        "tags": ["uncategorized"],
        "datasheet_url": "",
        "source_url": "",
    }


def search_components(name: str, model_number: str) -> List[Candidate]:
    """Return candidate list for the given name+model.

    Falls back to a synthetic candidate so the flow always has something
    to show.
    """
    matches = _match_prefix(name, model_number)
    if matches is None:
        return [_synthesize_candidate(name, model_number)]
    return list(matches)


# ---------------------------------------------------------------------------
# Mock image (SVG) generation
# ---------------------------------------------------------------------------

def generate_mock_svg(name: str, model_number: str, category: str) -> str:
    """Return a 400x400 SVG string.

    Background colour is keyed by category. The component name and model
    number are centred, with a thin border. No fonts, no images, no
    network — just ElementTree.
    """
    color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["Other"])
    safe_name = (name or "Unknown").strip()[:40]
    safe_model = (model_number or "").strip()[:40]

    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": "0 0 400 400",
            "width": "400",
            "height": "400",
        },
    )
    ET.SubElement(
        svg,
        "rect",
        {"x": "0", "y": "0", "width": "400", "height": "400", "fill": color},
    )
    ET.SubElement(
        svg,
        "rect",
        {
            "x": "4",
            "y": "4",
            "width": "392",
            "height": "392",
            "fill": "none",
            "stroke": "#ffffff",
            "stroke-width": "2",
            "opacity": "0.4",
        },
    )
    text = ET.SubElement(
        svg,
        "text",
        {
            "x": "200",
            "y": "190",
            "fill": "#ffffff",
            "font-family": "system-ui, -apple-system, sans-serif",
            "font-size": "24",
            "font-weight": "600",
            "text-anchor": "middle",
        },
    )
    text.text = safe_name
    sub = ET.SubElement(
        svg,
        "text",
        {
            "x": "200",
            "y": "220",
            "fill": "#ffffff",
            "font-family": "system-ui, -apple-system, sans-serif",
            "font-size": "14",
            "opacity": "0.85",
            "text-anchor": "middle",
        },
    )
    sub.text = safe_model
    badge = ET.SubElement(
        svg,
        "text",
        {
            "x": "200",
            "y": "370",
            "fill": "#ffffff",
            "font-family": "system-ui, -apple-system, sans-serif",
            "font-size": "12",
            "opacity": "0.6",
            "text-anchor": "middle",
            "letter-spacing": "2",
        },
    )
    badge.text = (category or "OTHER").upper()

    # ElementTree doesn't pretty-print by default; we keep it compact.
    return '<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(svg, encoding="unicode")


def slug_for_image(name: str, model_number: str) -> str:
    """Build the SVG filename slug (without extension)."""
    return _slugify(f"{name}-{model_number}")


# Public surface used by the FastAPI router.
__all__ = [
    "Candidate",
    "CATEGORY_COLORS",
    "search_components",
    "generate_mock_svg",
    "slug_for_image",
]
