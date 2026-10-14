"""Shared helpers for every Clip Studio tool: paths, ffmpeg discovery, brand, media probing, time formats."""
import functools
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the kit folder
BRAND_FILE = ROOT / 'brand' / 'brand.json'
FONTS = ROOT / 'fonts'
CANVAS = {'9:16': (1080, 1920), '16:9': (1920, 1080), '1:1': (1080, 1080), '4:5': (1080, 1350)}


def die(msg, code=1):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(code)


@functools.lru_cache
def ffmpeg():
    """An ffmpeg that has libass (needed to burn captions). Homebrew's default ffmpeg doesn't; ffmpeg-full does."""
    candidates = [os.environ.get('CLIP_FFMPEG'), '/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg',
                  '/usr/local/opt/ffmpeg-full/bin/ffmpeg', shutil.which('ffmpeg')]
    first = None
    for c in [c for c in candidates if c and Path(c).exists()]:
        first = first or c
        out = subprocess.run([c, '-hide_banner', '-filters'], capture_output=True, text=True).stdout
        if re.search(r'\bass\b', out):
            return c
    if first:
        return first
    die('ffmpeg not found. Run setup again (see START-HERE.md).')


def ffprobe():
    return str(Path(ffmpeg()).with_name('ffprobe' + ('.exe' if os.name == 'nt' else '')))


def has_libass():
    out = subprocess.run([ffmpeg(), '-hide_banner', '-filters'], capture_output=True, text=True).stdout
    return bool(re.search(r'\bass\b', out))


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe(media):
    out = subprocess.run([ffprobe(), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(media)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    v = next((s for s in j['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    fps = None
    if v:
        n, d = v.get('avg_frame_rate', '30/1').split('/')
        fps = float(n) / float(d) if float(d) else 30.0
    return {'duration': float(j['format']['duration']), 'width': v and int(v['width']), 'height': v and int(v['height']),
            'fps': fps, 'has_audio': a is not None, 'rotation': v and _rotation(v)}


def _rotation(v):
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            return int(sd['rotation'])
    return int(v.get('tags', {}).get('rotate', 0) or 0)


def brand():
    if not BRAND_FILE.exists():
        die('No brand profile yet. Ask Claude Code to run the brand interview first (brand/brand.json).')
    return json.loads(BRAND_FILE.read_text())


def to_sec(t):
    """'1:02:03.5', '10:19.98', '619.98' or a number -> seconds."""
    if isinstance(t, (int, float)):
        return float(t)
    t = str(t).strip().replace(',', '.')
    parts = [float(p) for p in t.split(':')]
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s


def fmt(t, ms=True):
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    core = f'{m:02d}:{s:05.2f}' if ms else f'{m:02d}:{int(s):02d}'
    return f'{h}:{core}' if h else core


def norm(w):
    return re.sub(r"[^a-z0-9']", '', w.lower().replace('’', "'"))


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60] or 'video'


def pcm(media, start=None, dur=None, sr=16000):
    """Mono float32 PCM of a span (numpy array)."""
    import numpy as np
    cmd = [ffmpeg(), '-v', 'error']
    if start is not None:
        cmd += ['-ss', f'{max(0.0, start):.3f}']
    if dur is not None:
        cmd += ['-t', f'{dur:.3f}']
    cmd += ['-i', str(media), '-ac', '1', '-ar', str(sr), '-f', 's16le', '-']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<i2').astype('float32') / 32768.0
