"""Turn the next unposted script into a vertical YouTube Short.

Usage:
    python make_short.py                 # next unposted script, real AI voice
    python make_short.py --id rule-of-72 # a specific script
    python make_short.py --silent-test   # no voice (for testing the video only)

Writes out/short.mp4 and out/meta.json.
"""

import argparse
import asyncio
import json
import random
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "out"
SCRIPTS = HERE / "scripts.json"
POSTED = HERE / "state" / "posted.json"

VOICE = "en-US-AndrewNeural"
RATE = "+8%"
W, H, FPS = 1080, 1920, 30
WORDS_PER_CAPTION = 3

# Background gradient pairs (dark, money-ish colours); one is picked per video.
PALETTES = [
    ("0x0b3d2e", "0x061a14"),
    ("0x0d2b45", "0x050f1a"),
    ("0x1e1b4b", "0x0a0820"),
    ("0x14532d", "0x0a0a0a"),
    ("0x3b2a0b", "0x0d0903"),
]

DISCLAIMER = "For education and entertainment only, not financial advice."


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def pick_script(script_id):
    scripts = load_json(SCRIPTS, [])
    if script_id:
        return next(s for s in scripts if s["id"] == script_id)
    posted = set(load_json(POSTED, []))
    for s in scripts:
        if s["id"] not in posted:
            return s
    raise SystemExit("Every script has been posted. Add more to scripts.json.")


async def synthesize(text, audio_path):
    """Free Microsoft Edge neural voice. Returns [(start_sec, end_sec, word)]."""
    import edge_tts

    words = []
    with open(audio_path, "wb") as f:
        tts = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    return words


def silent_track(text, audio_path):
    """Fake timings + silent audio, so the video step can be tested offline."""
    words, t = [], 0.3
    for w in text.split():
        words.append((t, t + 0.28, w))
        t += 0.33
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=24000:cl=mono", "-t", f"{t + 0.5:.2f}", str(audio_path)],
        check=True,
    )
    return words


def ass_time(sec):
    cs = int(round(sec * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def group_words(words):
    """Split words into short caption chunks, breaking after punctuation."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= WORDS_PER_CAPTION or w[2][-1] in ".,?!:;":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def write_captions(words, path):
    """Big centred captions; the word being spoken is highlighted yellow."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,5,80,80,0,1
Style: Tag,DejaVu Sans,52,&H0000D7FF,&H0000D7FF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,4,0,8,80,80,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = group_words(words)
    for ci, chunk in enumerate(chunks):
        chunk_end = chunks[ci + 1][0][0] if ci + 1 < len(chunks) else chunk[-1][1] + 0.6
        for wi, (start, _, _) in enumerate(chunk):
            end = chunk[wi + 1][0] if wi + 1 < len(chunk) else chunk_end
            parts = [
                ("{\\c&H0000D7FF&}" + w.upper() + "{\\c&H00FFFFFF&}") if j == wi else w.upper()
                for j, (_, _, w) in enumerate(chunk)
            ]
            # Pop-in on the first word of each chunk.
            pop = "{\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{pop}{' '.join(parts)}")
    total = chunks[-1][-1][1] + 0.6
    lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Tag,,0,0,0,,MONEY TIP")
    path.write_text(header + "\n".join(lines) + "\n")
    return total


def render(audio, captions, duration, video):
    c0, c1 = random.choice(PALETTES)
    bar = "0xFFD700"
    # Animated gradient background -> captions -> progress bar along the bottom.
    filters = (
        f"gradients=s={W}x{H}:c0={c0}:c1={c1}:x0=0:y0=0:x1={W}:y1={H}:speed=0.008:r={FPS}:d={duration:.2f},"
        f"vignette=PI/5,ass={captions.name}[bg];"
        f"color=c={bar}:s={W}x16:r={FPS}:d={duration:.2f}[bar];"
        f"[bg][bar]overlay=x='-w+w*t/{duration:.2f}':y=H-16[v]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-i", audio.name, "-filter_complex", filters,
         "-map", "[v]", "-map", "0:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-t", f"{duration:.2f}", "-movflags", "+faststart", video.name],
        check=True, cwd=OUT,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="script id to render")
    ap.add_argument("--silent-test", action="store_true", help="skip the AI voice")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    script = pick_script(args.id)
    text = f"{script['hook']} {script['body']}"
    audio, captions, video = OUT / "voice.mp3", OUT / "captions.ass", OUT / "short.mp4"

    if args.silent_test:
        words = silent_track(text, audio)
    else:
        words = asyncio.run(synthesize(text, audio))
    if not words:
        raise SystemExit("Voice service returned no word timings.")

    duration = write_captions(words, captions)
    render(audio, captions, duration, video)

    hashtags = " ".join("#" + t.replace(" ", "").replace("&", "") for t in script["tags"][:3])
    meta = {
        "id": script["id"],
        "title": f"{script['title']} #shorts"[:100],
        "description": f"{script['hook']}\n\n{DISCLAIMER}\n\n{hashtags} #shorts #money",
        "tags": script["tags"] + ["shorts", "money", "finance tips"],
        "duration": round(duration, 1),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Made {video} ({duration:.1f}s): {meta['title']}")


if __name__ == "__main__":
    main()
