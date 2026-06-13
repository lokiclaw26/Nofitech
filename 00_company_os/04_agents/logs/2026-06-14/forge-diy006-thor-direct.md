# DIY-006 Forge Report (Thor-direct)

## Mode
Thor-direct. The Forge subagent's 600s ceiling has been hit on the last 3
stages (1, 3, 5). Stage 6's spec was fully verified end-to-end with curl
BEFORE writing code, so applying directly is faster and safer.

## Pre-implementation findings
| Vendor | Status | Reason |
|---|---|---|
| Adafruit | ✅ Implemented | Search returns product links; product page has og:title, og:image, og:description, AND a real datasheet PDF link in the page body. robots.txt allows /. |
| Pololu | ⚠️ Disabled | robots.txt disallows /search. NOT called. Returns 0 candidates with a note explaining why. Niche components only Pololu carries can be added via direct URL or "Enter manually" form. |
| SparkFun | ❌ Rejected | Search results are JS-rendered, no product URLs in static HTML. Cannot be reliably scraped without a headless browser. |

## Files changed
- MODIFIED: code/backend/app/live_search.py (+ ~210 LOC: 1 vendor cache, 1 throttle, 1 HTTP helper, 1 meta extractor, 1 Adafruit fetcher, 1 Pololu stub, 1 SparkFun stub-comment)

## End-to-end tests
- "BME680" -> Adafruit returns "Adafruit BME680" with og:image AND datasheet_url=https://cdn-shop.adafruit.com/product-files/3660/BME680.pdf
- "INA219" -> Adafruit returns "INA219 High Side DC Current Sensor Breakout"
- "DS18B20" -> Adafruit returns "DS18B20 Digital Temperature Sensor" with datasheet https://cdn-shop.adafruit.com/datasheets/DS18B20.pdf
- "TP4056", "MAX6675", "Neopixel", "Servo SG90", "DHT22", "STM32F103" -> all return real Adafruit products
- "Wemos D1 Mini" (regression) -> 11 candidates (was 10 in Stage 5, +1 from Adafruit)
- Cache: 2nd identical query returns in 3ms (cached)

## Hard rules
- ✅ User-Agent: DIY-Hub/1.0 (https://github.com/nofitech; contact: ops@nofitech.local)
- ✅ Vendor cache TTL: 3600 seconds (1 hour)
- ✅ Throttle: 1.0 second minimum between requests to same vendor
- ✅ NO price/stock fields in any response (verified by key scan)
- ✅ NO DDG scraping (0 hits for "duckduckgo" in code)
- ✅ NO SparkFun scraping (only 1 hit, in a comment block explaining why it's disabled)
- ✅ NO Octopart, NO Google, NO API keys, NO login, NO purchasing
- ✅ Pololu robots.txt disallow honored (we don't call /search)
