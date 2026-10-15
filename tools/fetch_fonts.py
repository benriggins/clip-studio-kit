#!/usr/bin/env python3
"""Download the brand's fonts (free Google Fonts, OFL) into fonts/. Run by setup; safe to re-run.

usage: fetch_fonts.py [google-fonts-path ...]
  With no arguments: the defaults plus every font listed in my-studio/brand.json.
  A google-fonts-path looks like  ofl/anton/Anton-Regular.ttf  (browse github.com/google/fonts).
  A brand font with "instance": {"wght": 800} is cut from its variable font into a static file (its "file"), so a
  variable family such as Montserrat can be used for captions, which need a static font.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import BRAND_FILE, FONTS  # noqa: E402

BASE = 'https://github.com/google/fonts/raw/main/'
DEFAULTS = ['ofl/anton/Anton-Regular.ttf',                 # captions: condensed, heavy, very readable on phones
            'ofl/dmserifdisplay/DMSerifDisplay-Regular.ttf',  # explainer headlines
            'ofl/dmserifdisplay/DMSerifDisplay-Italic.ttf',
            'ofl/inter/Inter[opsz,wght].ttf']               # explainer labels and body


def fetch(path):
    dest = FONTS / Path(path).name
    if dest.exists() and dest.stat().st_size > 10000:
        return dest
    url = BASE + urllib.parse.quote(path, safe='/')
    with urllib.request.urlopen(url, timeout=60) as r:
        dest.write_bytes(r.read())
    print(f'  font {dest.name}')
    return dest


def instance(src, dest, axes):
    if dest.exists() and dest.stat().st_size > 10000:
        return
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    font = instancer.instantiateVariableFont(TTFont(src), {k: float(v) for k, v in axes.items()}, updateFontNames=True)
    font.save(dest)
    print(f'  font {dest.name} (static cut of {src.name}: {axes})')


def main(paths):
    FONTS.mkdir(exist_ok=True)
    wanted = list(paths) or list(DEFAULTS)
    if not paths and BRAND_FILE.exists():
        b = json.loads(BRAND_FILE.read_text())
        wanted += [f['google'] for f in b.get('fonts', {}).values() if isinstance(f, dict) and f.get('google')]
    for p in dict.fromkeys(wanted):
        fetch(p)
    if not paths and BRAND_FILE.exists():
        for f in json.loads(BRAND_FILE.read_text()).get('fonts', {}).values():
            if isinstance(f, dict) and f.get('instance') and f.get('google'):
                instance(FONTS / Path(f['google']).name, FONTS.parent / f['file'], f['instance'])
    print(f'fonts ready in {FONTS}')


if __name__ == '__main__':
    main(sys.argv[1:])
