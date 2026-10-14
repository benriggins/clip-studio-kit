#!/usr/bin/env python3
"""Export still frames so Claude Code can SEE the footage before deciding crops, cuts or graphic placement.

usage: frames.py <media> <t1> [t2 …] [--crop x,y,w,h] [--out DIR]
       frames.py <media> --every 30            (one frame every 30 s)
Times accept seconds or mm:ss. With --crop, the crop box is drawn on each frame so a framing can be judged.
"""
import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ffmpeg, probe, run, to_sec  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('media')
    ap.add_argument('times', nargs='*')
    ap.add_argument('--every', type=float)
    ap.add_argument('--crop')
    ap.add_argument('--out')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    media = Path(a.media).resolve()
    info = probe(media)
    times = [to_sec(t) for t in a.times]
    if a.every:
        times += [k * a.every for k in range(int(info['duration'] // a.every) + 1)]
    out = Path(a.out) if a.out else media.parent / f'{media.stem}-frames'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for t in times:
            f = Path(td) / 'f.png'
            run([ffmpeg(), '-y', '-v', 'error', '-ss', f'{t:.3f}', '-i', media, '-frames:v', '1', f])
            im = Image.open(f).convert('RGB')
            dr = ImageDraw.Draw(im)
            if a.crop:
                x, y, w, h = (int(v) for v in a.crop.split(','))
                dr.rectangle([x, y, x + w, y + h], outline=(255, 220, 0), width=6)
            dr.text((20, 20), f'{t:.2f}s', fill=(255, 220, 0))
            im.thumbnail((1280, 1280))
            dest = out / f'{t:08.2f}.jpg'
            im.save(dest, quality=88)
            print(dest)


if __name__ == '__main__':
    main()
