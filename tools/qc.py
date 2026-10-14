#!/usr/bin/env python3
"""Final quality check of a rendered video, plus images Claude Code looks at before calling it done.

usage: qc.py <rendered.mp4> [edit-plan.json]

Prints: duration, resolution, loudness (target about -14 LUFS), true peak (must be <= -1 dBTP), black frames.
Writes next to the video:
  <name>-contact.jpg   12 frames across the whole video (framing, captions, graphics)
  <name>-joins.jpg     the frames just before and after every cut (blinks, jumps, mid-word faces), if a plan is given
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ffmpeg, probe, run  # noqa: E402
from render import loudness  # noqa: E402


def grab(media, times, out, cols, label=None):
    from PIL import Image, ImageDraw
    info = probe(media)
    tw = 360
    th = int(tw * info['height'] / info['width'])
    tiles = []
    with tempfile.TemporaryDirectory() as td:
        for k, t in enumerate(times):
            f = Path(td) / f'{k}.jpg'
            run([ffmpeg(), '-y', '-v', 'error', '-ss', f'{max(0, t):.3f}', '-i', media, '-frames:v', '1',
                 '-vf', f'scale={tw}:{th}', f])
            im = Image.open(f).convert('RGB')
            ImageDraw.Draw(im).text((8, 8), label[k] if label else f'{t:.2f}s', fill=(255, 255, 0))
            tiles.append(im)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (tw * cols, th * rows), 'black')
    for k, im in enumerate(tiles):
        sheet.paste(im, ((k % cols) * tw, (k // cols) * th))
    sheet.save(out, quality=85)


def main(media, plan_path=None):
    media = Path(media).resolve()
    info = probe(media)
    lufs, tp = loudness(media)
    err = subprocess.run([ffmpeg(), '-hide_banner', '-nostats', '-i', str(media), '-vf',
                          'blackdetect=d=0.05:pix_th=0.06', '-an', '-f', 'null', '-'], capture_output=True, text=True).stderr
    blacks = re.findall(r'black_start:([\d.]+)', err)
    print(f'{media.name}: {info["width"]}x{info["height"]}, {info["duration"]:.2f}s, {info["fps"]:.2f} fps')
    print(f'  loudness {lufs} LUFS (target ≈ -14)  {"✓" if lufs and abs(lufs + 14) <= 1.5 else "✗"}')
    print(f'  true peak {tp} dBTP (must be ≤ -1)    {"✓" if tp is not None and tp <= -1 else "✗"}')
    print(f'  black frames: {len(blacks)}              {"✓" if not blacks else "✗ at " + ", ".join(blacks[:5])}')
    n = 12
    grab(media, [info['duration'] * (k + 0.5) / n for k in range(n)], media.with_name(media.stem + '-contact.jpg'), 4)
    print(f'  contact sheet → {media.with_name(media.stem + "-contact.jpg")}')
    if plan_path:
        d = json.loads(Path(plan_path).read_text())
        times, labels, t = [], [], 0.0
        for k, s in enumerate(d['segments'][:-1]):
            t += s['out'] - s['in']
            times += [t - 0.07, t + 0.07]
            labels += [f'cut {k + 1} before', f'cut {k + 1} after']
        if times:
            grab(media, times, media.with_name(media.stem + '-joins.jpg'), 4, labels)
            print(f'  join frames → {media.with_name(media.stem + "-joins.jpg")}  (look for blinks and odd faces)')


if __name__ == '__main__':
    main(*sys.argv[1:])
