#!/usr/bin/env python3
"""Generate ONE alternate voice set into audio/<voiceId>/ for a single language.

Usage:
    python3 generate_voice_set.py <AZURE_KEY> <REGION> <lang> <voiceId> <azureVoiceName> [rate]
    e.g. python3 generate_voice_set.py KEY eastus en ryan  en-GB-RyanNeural   -4%
         python3 generate_voice_set.py KEY eastus ar hamed ar-SA-HamedNeural  -10%

Reads speech_manifest.json, filters to clips of <lang>, and writes audio/<voiceId>/<key>.mp3.
Resumable: existing files are skipped.
"""
import json, os, sys, time, urllib.request, html as htmllib, ssl, certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

if len(sys.argv) < 6:
    print(__doc__); sys.exit(1)
KEY, REGION, LANG, VOICE_ID, AZURE_VOICE = [a.strip() for a in sys.argv[1:6]]
RATE = sys.argv[6].strip() if len(sys.argv) > 6 else "-6%"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio", VOICE_ID)
os.makedirs(OUT, exist_ok=True)

SPOKEN_FIXES = [
    ("→", ", "), ("×", " times "), ("÷", " divided by "), ("−", " minus "),
    ("²", " squared"), ("³", " cubed"), ("¼", " one quarter"), ("⅝", " five eighths"),
    ("⅛", " one eighth"), ("½", " one half"), ("%", " percent"),
]

def synth(text):
    spoken = text
    for a, b in SPOKEN_FIXES:
        spoken = spoken.replace(a, b)
    ssml = ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-GB'>"
            f"<voice name='{AZURE_VOICE}'><prosody rate='{RATE}'>" + htmllib.escape(spoken)
            + "</prosody></voice></speak>")
    req = urllib.request.Request(
        f"https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={"Ocp-Apim-Subscription-Key": KEY, "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "HanaLearningQuest"})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        return r.read()

items = [i for i in json.load(open(os.path.join(HERE, "speech_manifest.json"), encoding="utf-8")) if i["lang"] == LANG]
done = skipped = failed = 0
for n, it in enumerate(items, 1):
    path = os.path.join(OUT, it["key"] + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 200:
        skipped += 1; continue
    for attempt in range(3):
        try:
            with open(path, "wb") as f:
                f.write(synth(it["text"]))
            done += 1
            if done % 100 == 0:
                print(f"[{n}/{len(items)}] {VOICE_ID} … {done} done")
            break
        except Exception as e:
            print(f"[{n}] retry {attempt+1}: {e}"); time.sleep(2 + attempt * 3)
    else:
        failed += 1
    time.sleep(0.12)

print(f"Done ({VOICE_ID}). generated={done} skipped={skipped} failed={failed} → audio/{VOICE_ID}/")
