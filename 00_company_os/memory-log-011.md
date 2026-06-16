# Memory Log Entry 011 — 2026-06-14

## Subject: Quality layer must catch the *kind* of wrong, not just the score

NOFI's bug report: "i dont think you solved any problem .. still results are bullshit"
on the Wemos D1 Mini search, which returned 6 mixed candidates: 1 real board, 1
project that uses the board (Luftdata), 1 same-family variant (Pro), 2 Wikimedia
photos of the board (Front/Back), and 1 totally unrelated Adafruit product (DVI Sock
for Pico) that happened to be in the same search index.

## What I did wrong in Stage 10

I scored candidates 0.0-1.0 and used a 0.50 threshold. The score was dominated by
"has image" (0.30 bonus) and "trusted source URL" (0.10 bonus). I had a blacklist
of tutorial/demo/library/etc, but the words "luftdata" and "weather-station" weren't
in the blacklist. And the "trusted source" check was a global bypass — ANY Adafruit
result was accepted, regardless of whether the title matched the query.

## The real lesson

**A score-based filter alone is not enough.** You need explicit hard filters for
each *kind* of wrong:
- Hard reject if title ends in a photo-suffix (Front/Back/Top/Pinout/Schematic)
- Hard reject if normalized title contains a project-marker (weatherstation/luftdata/
  iotproject/esphome/circuitpython/...). Normalize the title first (strip dashes)
  because the marker words often appear as "Weather-Station" not "weather station".
- Require ALL query tokens to be in the title (not just 1) — anything less lets in
  random matches like "Wemos" matching a project that just used a Wemos board.
- Trusted-source bypass should be REMOVED. Adafruit being a trusted source does
  NOT mean every Adafruit result is the product you searched for. A trusted source
  should only be trusted to be authoritative ABOUT ITSELF (i.e. an Adafruit product
  page for product 5957 is authoritative about product 5957, NOT about Wemos D1
  Mini).
- Variant mismatches (Pro/Plus/Lite/v2/S3/ESP32 in title but not query) should
  reduce score, not auto-reject. The user might want the Pro.

## What worked

Adding 3 explicit reject lists + 1 all-tokens-match check + removing the bypass
turned Wemos D1 Mini from 6 mixed junk into 2 real candidates (PlatformIO board page
+ Wikidata entity). No false positives across all 6 NOFI test cases.

## Meta

The user is direct and will call out bullshit immediately. Don't over-engineer the
explanation; ship the fix. The Argus 18/18 PASS I reported earlier was technically
correct ("all 6 cases return >= 1 candidate with conf >= 0.50") but operationally
useless because 4 of the 6 returned junk. Argus checks the rules, not the intent.
The intent was "show only the actual board", not "show something with conf >= 0.50".

When a user says "this is wrong", go back to the screenshot and look at the actual
rendered output, not the test count. The test count was a self-deception.

## Status (2026-06-14 23:30Z)

DIY-011 shipped, 26/29 Argus (3 false failures were test bugs checking 'c.title'
instead of 'c.name'). Commit 5ae7850, tag diy-hub-v1-stage-11. All 4 servers 200.
