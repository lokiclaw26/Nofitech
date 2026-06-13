"""OFFLINE FALLBACK catalog for DIY Hub V1 (Stage 5).

⚠️ OFFLINE FALLBACK ONLY — NOT the primary lookup path. ⚠️

The primary lookup path is now ``app.live_search`` (real live HTTP
queries to Wikimedia Commons, Wikidata, Wikipedia, PlatformIO, and
public GitHub repos — all free, all no-key, all no-login).

This catalog remains ONLY for the explicit operator-triggered offline
fallback flow:
    1. Live search returns 0 candidates
    2. UI shows "No reliable live result found"
    3. Operator clicks "Try offline mock fallback" button
    4. THEN this catalog is consulted

NEVER use this catalog as a default. NEVER pre-populate candidates
from here when the live search succeeds. The whole point of Stage 5
is real live data, not a hard-coded list.

When the operator clicks ADD TO DATABASE for a candidate from this
catalog, the saved record is marked with ``source = "mock_fallback"``
in the notes blob so we can tell, later, which records came from real
live data and which came from this offline fallback.

The URLs in this module are display strings only — they are never
fetched here. Image lookup happens in ``app.live_search``.
"""
from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional, TypedDict


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
    image_url: Optional[str]  # hardcoded Commons thumbnail (pre-verified)
    wikipedia_title: str      # fallback for wikipedia.py fetcher if image_url is None


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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Espressif_ESP-WROOM-32_Wi-Fi_%26_Bluetooth_Module.jpg/500px-Espressif_ESP-WROOM-32_Wi-Fi_%26_Bluetooth_Module.jpg",
        "wikipedia_title": "ESP32",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Espressif_ESP-WROOM-32_Wi-Fi_%26_Bluetooth_Module.jpg/500px-Espressif_ESP-WROOM-32_Wi-Fi_%26_Bluetooth_Module.jpg",
        "wikipedia_title": "ESP32",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/ESP32-S3_on_paper.jpg/500px-ESP32-S3_on_paper.jpg",
        "wikipedia_title": "ESP32-S3",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Arduino_Uno_-_R3.jpg/500px-Arduino_Uno_-_R3.jpg",
        "wikipedia_title": "Arduino Uno",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Arduino_Nano.jpg/500px-Arduino_Nano.jpg",
        "wikipedia_title": "Arduino Nano",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Arduino_Mega_2560_%28HW-888%29_front.jpg/500px-Arduino_Mega_2560_%28HW-888%29_front.jpg",
        "wikipedia_title": "Arduino Mega",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Raspberry_Pi_4_Model_B_-_Top.jpg/500px-Raspberry_Pi_4_Model_B_-_Top.jpg",
        "wikipedia_title": "Raspberry Pi",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Raspberry_Pi_Zero.jpg/500px-Raspberry_Pi_Zero.jpg",
        "wikipedia_title": "Raspberry Pi Zero",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/WS2812Closeup2.jpg/500px-WS2812Closeup2.jpg",
        "wikipedia_title": "WS2812",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Mini_NeoPixel.jpg/500px-Mini_NeoPixel.jpg",
        "wikipedia_title": "SK6812",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Tower_Pro_SG90_micro_servo_motor.jpg/500px-Tower_Pro_SG90_micro_servo_motor.jpg",
        "wikipedia_title": "Servo (radio control)",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Tower_Pro_SG90_micro_servo_motor.jpg/500px-Tower_Pro_SG90_micro_servo_motor.jpg",
        "wikipedia_title": "Servo (radio control)",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/17/Voltage_Regulator.png",
        "wikipedia_title": "78xx",
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
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/48/LM358_low-cost_op_amp.jpg/500px-LM358_low-cost_op_amp.jpg",
        "wikipedia_title": "LM358",
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
    popup they can either accept (save) or cancel. The ``wikipedia_title``
    is a best-effort attempt — the search handler will call the lookup and
    gracefully get null back if Wikipedia has nothing for that name.
    """
    base = _slugify(f"{name} {model_number}", max_length=40)
    clean_name = name.strip() or "Unknown Component"
    return {
        "id": f"generic-{base}-{uuid.uuid4().hex[:6]}",
        "name": clean_name,
        "model_number": model_number.strip() or "Unknown",
        "category": "Other",
        "voltage": "Unknown",
        "interfaces": [],
        "key_specs": ["User-supplied — not in local catalog"],
        "tags": ["uncategorized"],
        "datasheet_url": "",
        "source_url": "",
        "image_url": None,  # no real image; UI shows "No real image found"
        "wikipedia_title": clean_name,
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


def slug_for_image(name: str, model_number: str) -> str:
    """Build the image filename slug (without extension)."""
    return _slugify(f"{name}-{model_number}")


# Public surface used by the FastAPI router.
__all__ = [
    "Candidate",
    "search_components",
    "slug_for_image",
]
