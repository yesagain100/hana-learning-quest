#!/usr/bin/env python3
"""Generate real-voice audio for Hana's Learning Quest using Azure Speech.

Usage:
    python3 generate_audio.py <AZURE_SPEECH_KEY> <REGION>
    e.g. python3 generate_audio.py abc123... uaenorth

Reads speech_manifest.json (619 clips) and writes audio/<key>.mp3 for each.
Voices: English = en-GB-SoniaNeural (warm British teacher)
        Arabic  = ar-EG-SalmaNeural (native Egyptian female)
Resumable: already-generated files are skipped, so re-running is safe.
"""
import json, os, sys, time, urllib.request, html as htmllib, ssl, certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

if len(sys.argv) != 3:
    print(__doc__); sys.exit(1)
KEY, REGION = sys.argv[1].strip(), sys.argv[2].strip()

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio")
os.makedirs(OUT, exist_ok=True)

VOICES = {"en": ("en-GB-SoniaNeural", "-4%"), "ar": ("ar-SA-ZariyahNeural", "-10%"), "arm": ("ar-EG-ShakirNeural", "-12%")}

# light cleanup of symbols TTS reads badly (filenames still hash the ORIGINAL text)
SPOKEN_FIXES = [
    ("→", ", "), ("×", " times "), ("÷", " divided by "), ("−", " minus "),
    ("²", " squared"), ("³", " cubed"), ("¼", " one quarter"), ("⅝", " five eighths"),
    ("⅛", " one eighth"), ("½", " one half"), ("%", " percent"),
]

def fnv(lang, text):
    h = 0x811C9DC5
    for i, b in enumerate(memoryview((lang + "|" + text).encode("utf-16-le"))):
        pass
    units = (lang + "|" + text).encode("utf-16-le")
    h = 0x811C9DC5
    for i in range(0, len(units), 2):
        cu = units[i] | (units[i + 1] << 8)
        h ^= cu
        h = (h * 0x01000193) & 0xFFFFFFFF
    return format(h, "08x")

def synth(voice, rate, text):
    spoken = text
    for a, b in SPOKEN_FIXES:
        spoken = spoken.replace(a, b)
    ssml = (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        f"xml:lang='en-GB'><voice name='{voice}'><prosody rate='{rate}'>"
        + htmllib.escape(spoken)
        + "</prosody></voice></speak>"
    )
    req = urllib.request.Request(
        f"https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "HanaLearningQuest",
        },
    )
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        return r.read()

items = json.load(open(os.path.join(HERE, "speech_manifest.json"), encoding="utf-8"))
done = skipped = failed = 0
for n, it in enumerate(items, 1):
    key = it["key"]
    # safety: recomputed key must match the manifest
    if fnv(it["lang"], it["text"]) != key:
        print(f"[{n}] HASH MISMATCH — skipping: {it['text'][:40]}"); failed += 1; continue
    path = os.path.join(OUT, key + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 200:
        skipped += 1; continue
    voice, rate = VOICES[it["lang"]]
    for attempt in range(3):
        try:
            audio = synth(voice, rate, it["text"])
            with open(path, "wb") as f:
                f.write(audio)
            done += 1
            print(f"[{n}/{len(items)}] {it['lang']} {key} ok ({len(audio)//1024} KB)  {it['text'][:50]}")
            break
        except Exception as e:
            print(f"[{n}] attempt {attempt+1} failed: {e}")
            time.sleep(2 + attempt * 3)
    else:
        failed += 1
    time.sleep(0.15)  # gentle on the free tier

print(f"\nDone. generated={done} skipped(existing)={skipped} failed={failed}")
if failed:
    print("Re-run the same command to retry the failed ones.")
