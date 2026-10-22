#!/usr/bin/env python3
"""Make a generated clip look like it was shot with the A-roll: trim, conform to 1080x1920 30 fps, the same grade
as the takes, an eased push-in (or pull-out), optional speed ramp, fine grain.

usage: broll_fx.py <in.mp4> <out.mp4> --start 0.4 --dur 2.6 [--push 1.10] [--speed 1.0] [--grade takes/grade.txt]
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ffmpeg  # noqa: E402
FF = ffmpeg()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--dur', type=float, required=True)
    ap.add_argument('--push', type=float, default=1.10, help='end zoom; <1 pulls out')
    ap.add_argument('--speed', type=float, default=1.0)
    ap.add_argument('--grade')
    ap.add_argument('--focus', default='0.5,0.5', help='x,y (0-1) the push travels toward')
    a = ap.parse_args()
    n = int(round(a.dur * 30))
    z0, z1 = (1.0, a.push) if a.push >= 1 else (1 / a.push, 1.0)
    # smoothstep ease on the zoom so the move starts and lands softly
    ease = f"({z0}+({z1}-{z0})*(3*pow(on/{n},2)-2*pow(on/{n},3)))"
    fx, fy = (float(v) for v in a.focus.split(','))
    grade = (Path(a.grade).read_text().strip() + ',') if a.grade else ''
    vf = (f'setpts=PTS/{a.speed},fps=30,scale=1296:2304:force_original_aspect_ratio=increase,crop=1296:2304,'
          f"zoompan=z='{ease}':x='max(0,min(iw-iw/zoom,iw*{fx}-iw/zoom/2))':y='max(0,min(ih-ih/zoom,ih*{fy}-ih/zoom/2))':d=1:s=1080x1920:fps=30,"
          f'{grade}format=yuv420p')
    subprocess.run([FF, '-y', '-v', 'error', '-ss', str(a.start), '-i', a.src, '-t', f'{a.dur * a.speed:.3f}', '-an', '-vf', vf,
                    '-frames:v', str(n), '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', a.out], check=True)
    print(f'b-roll → {a.out}')


if __name__ == '__main__':
    main()
