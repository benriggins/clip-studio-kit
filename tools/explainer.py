#!/usr/bin/env python3
"""Animated explainer slides (HyperFrames: HTML + GSAP rendered to video; free, Apache-2.0), on YOUR brand.

usage:
  explainer.py list                                                 the slide templates and animation feels
  explainer.py new    <project> <name> --template steps --canvas 1080x1920 [--duration 6] [--feel smooth] [--split]
  explainer.py check  <project> <name>                              HyperFrames lint, layout and contrast check
  explainer.py render <project> <name>                              -> graphics/<name>/renders/<name>.mp4
  explainer.py brand                                                rebuild every brand.css from my-studio/brand.json

Templates: steps, compare, stat, quote, timeline, tiers/stairs (see list). --tone dark|light and --backdrop <photo>
choose the backdrop (defaults: brand.json style.backdrop). --split leaves room for the speaker's live face
card (left in 16:9, top in 9:16). The feel defaults to the user's choice in my-studio/brand.json (style.feel).
Files live in projects/<project>/graphics/<name>/. Replace every placeholder label with the speaker's own words,
set the beat times, check, render, then add to the edit plan:
  "graphics": [{"file": "graphics/<name>/renders/<name>.mp4", "at": <seconds in the cut>}]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, brand, die  # noqa: E402
from templates import FEELS, TEMPLATE_CSS, TEMPLATES, page  # noqa: E402

HF = 'hyperframes@0.8.34'
NODE_MODULES = ROOT / 'graphics' / 'node_modules'


def npx():
    exe = shutil.which('npx') or shutil.which('npx.cmd')
    if not exe:
        die('Node.js (npx) not found. Run setup again.')
    return exe


def brand_css(W, H, split=False, tone='light'):
    b = brand()
    c, f = b['colors'], b['fonts']
    vertical = H > W
    faces = []
    for role in ('display', 'display_italic', 'body'):
        if role in f:
            style = 'italic' if role.endswith('italic') else 'normal'
            faces.append(f'@font-face {{ font-family: "{f[role]["family"]}"; src: url("assets/fonts/'
                         f'{Path(f[role]["file"]).name}"); font-style: {style}; font-weight: 100 900; }}')
    pad = 96 if vertical else 150
    if split and vertical:
        box = f'left: {pad}px; right: {pad}px; top: {int(H * 0.30)}px; bottom: {int(H * 0.32)}px;'
    elif split:
        box = f'left: {int(W * 0.46)}px; right: {pad - 30}px; top: 120px; bottom: 160px;'
    else:   # text stays clear of the platform's top UI and above the caption band
        box = (f'left: {pad}px; right: {pad}px; top: {int(H * 0.11) if vertical else 100}px; '
               f'bottom: {int(H * 0.335) if vertical else 200}px;')
    fill = c.get('fill', c['accent'])
    grain = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>"
             "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/>"
             "</filter><rect width='100%' height='100%' filter='url(%23n)' opacity='.55'/></svg>")
    return '\n'.join(faces) + f'''
:root {{
  --bg: {c['background']}; --surface: {c['surface']}; --text: {c['text']}; --muted: {c['muted']}; --accent: {c['accent']};
  --fill: {fill}; --on-fill: {c.get('on_fill', '#2A2118')};
  --card: #FFFFFF; --card-solid: #FFFFFF; --card-line: color-mix(in srgb, {c['text']} 10%, transparent);
  --card-shadow: 0 18px 50px rgba(60, 40, 20, .10), 0 2px 6px rgba(60, 40, 20, .06);
  --rail: color-mix(in srgb, {c['text']} 12%, transparent);
  --font-display: "{f['display']['family']}", Georgia, serif; --font-body: "{f['body']['family']}", system-ui, sans-serif;
  --h1: {(96 if split else 120) if vertical else (80 if split else 92)}px; --step: {58 if vertical else (46 if split else 42)}px;
}}
.tone-dark {{
  --text: #FFFFFF; --muted: rgba(255, 255, 255, .74); --accent: {c.get('accent_on_dark', fill)};
  --card: rgba(255, 255, 255, .10); --card-solid: #2A241E; --card-line: rgba(255, 255, 255, .20);
  --card-shadow: 0 24px 60px rgba(0, 0, 0, .35); --rail: rgba(255, 255, 255, .22);
}}
* {{ box-sizing: border-box; margin: 0; }}
.b-root {{ position: relative; overflow: hidden; color: var(--text); font-family: var(--font-body);
  background: radial-gradient(90% 55% at 50% 30%, color-mix(in srgb, var(--fill) 22%, transparent), transparent 65%), var(--bg); }}
.b-root.tone-dark {{ background: radial-gradient(90% 60% at 50% 35%, #3A3027, #15110D 75%); }}
.fill {{ position: absolute; inset: 0; pointer-events: none; }}
.bd-photo-wrap {{ overflow: hidden; }}
.bd-photo {{ width: 100%; height: 100%; object-fit: cover; transform-origin: 50% 60%; }}
.tone-dark .bd-shade {{ background: linear-gradient(180deg, rgba(20, 15, 10, .46) 0%, rgba(20, 15, 10, .58) 45%, rgba(20, 15, 10, .80) 100%),
  radial-gradient(80% 50% at 50% 40%, rgba(214, 178, 138, .10), transparent 70%); }}
.tone-light .bd-photo-wrap {{ top: auto; height: {38 if vertical else 34}%;
  -webkit-mask-image: linear-gradient(transparent, #000 42%); mask-image: linear-gradient(transparent, #000 42%); }}
.tone-light .bd-shade {{ background: linear-gradient(180deg, transparent {66 if vertical else 70}%, rgba(20, 15, 10, .42) 100%); }}
.bd-grain {{ background-image: url("{grain}"); opacity: .07; mix-blend-mode: overlay; }}
.tone-dark .b-step, .tone-dark .b-statcard, .tone-dark .b-compare .col, .tone-dark .b-stairs .blk {{
  -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px); }}
#content {{ position: absolute; {box} display: flex; flex-direction: column; justify-content: center; }}
.b-pill {{ align-self: flex-start; display: inline-block; width: max-content; padding: 16px 30px 15px; border-radius: 999px;
  background: var(--fill); color: var(--on-fill); font: 700 {30 if vertical else 22}px/1 var(--font-body); letter-spacing: .16em; text-transform: uppercase; }}
.b-headline {{ margin-top: 30px; font: 600 var(--h1)/1.04 var(--font-display); letter-spacing: -.03em; color: var(--text); }}
.split .w {{ display: inline-block; overflow: hidden; vertical-align: top; padding: .06em 0 .16em; margin: -.06em 0 -.16em; }}
.split .w.has-swash {{ overflow: visible; }}
.split .wi {{ display: inline-block; }}
.swash {{ position: relative; display: inline-block; }}
.swash-svg {{ position: absolute; left: -3%; width: 106%; bottom: -.3em; height: .36em; overflow: visible; }}
.swash-svg path {{ fill: none; stroke: var(--fill); stroke-width: 6; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1; }}
.is-accent {{ color: var(--accent); }}
''' + TEMPLATE_CSS


def pick_photo(name, choice=None):
    """The backdrop photo for a graphic: an explicit path or photo name, 'none', or one of brand style.backdrop.photos."""
    if choice == 'none':
        return None
    photos = [ROOT / p for p in brand().get('style', {}).get('backdrop', {}).get('photos', [])]
    if choice:
        p = Path(choice)
        cands = [p, ROOT / p] + [x for x in photos if x.stem == choice or x.name == choice]
        hit = next((x for x in cands if x.exists()), None)
        if not hit:
            die(f'backdrop photo {choice} not found (give a path, or a name from brand.json style.backdrop.photos)')
        return hit
    photos = [x for x in photos if x.exists()]
    return photos[sum(map(ord, name)) % len(photos)] if photos else None


def comp_dir(project, name):
    return ROOT / 'projects' / project / 'graphics' / name


def new(project, name, template, canvas, duration, feel=None, split=False, quiet=False, tone=None, backdrop=None):
    if template not in TEMPLATES:
        die(f'unknown template {template}: use one of {", ".join(TEMPLATES)}')
    feel = feel or brand().get('style', {}).get('feel', 'smooth')
    if feel not in FEELS:
        die(f'unknown feel {feel}: use one of {", ".join(FEELS)}')
    W, H = (int(v) for v in canvas.lower().split('x'))
    tone = tone or brand().get('style', {}).get('backdrop', {}).get('tone', 'light')
    if tone not in ('light', 'dark'):
        die(f'unknown tone {tone}: use light or dark')
    photo = pick_photo(name, backdrop)
    d = comp_dir(project, name)
    if d.exists():
        die(f'{d} already exists')
    d.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'HYPERFRAMES_SKIP_SKILLS': '1'}
    subprocess.run([npx(), '--yes', HF, 'init', name, '--example', 'blank', '--non-interactive', '--skip-transcribe'],
                   cwd=d.parent, check=True, env=env, stdout=subprocess.DEVNULL)
    (d / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)
    (d / 'assets' / 'js').mkdir(parents=True, exist_ok=True)
    for f in brand()['fonts'].values():
        if isinstance(f, dict) and f.get('file'):
            shutil.copy(ROOT / f['file'], d / 'assets' / 'fonts')
    for js in ('gsap.min.js', 'CustomEase.min.js'):
        shutil.copy(NODE_MODULES / 'gsap' / 'dist' / js, d / 'assets' / 'js')
    rel = None
    if photo:   # a cover-sized JPEG copy keeps renders fast and the composition self-contained
        from PIL import Image
        im = Image.open(photo).convert('RGB')
        k = max(W * 1.25 / im.width, H * 1.25 / im.height, 0.0)
        if k < 1:
            im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        (d / 'assets' / 'img').mkdir(parents=True, exist_ok=True)
        im.save(d / 'assets' / 'img' / 'backdrop.jpg', quality=88)
        rel = 'assets/img/backdrop.jpg'
    (d / 'brand.css').write_text(brand_css(W, H, split, tone))
    (d / 'index.html').write_text(page(name, template, W, H, duration, feel, split, tone, rel))
    if not quiet:
        print(f'scaffolded {d} ({template}, {feel}, {tone}{", " + photo.name if photo else ""}{", split" if split else ""})\n'
              f'  replace every placeholder with the speaker\'s words, set beat times, then: check / render')


def check(project, name):
    subprocess.run([npx(), '--yes', HF, 'check'], cwd=comp_dir(project, name), check=False)


def render(project, name, quiet=False):
    d = comp_dir(project, name)
    (d / 'renders').mkdir(exist_ok=True)
    out = d / 'renders' / f'{name}.mp4'
    subprocess.run([npx(), '--yes', HF, 'render', '.', '--fps', '30', '--quality', 'high', '--format', 'mp4',
                    '-o', str(out), '--quiet'], cwd=d, check=True,
                   stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.DEVNULL if quiet else None)
    if not quiet:
        print(f'rendered {out}')
    return out


def rebrand():
    for idx in (ROOT / 'projects').glob('*/graphics/*/index.html'):
        html = idx.read_text()
        m = re.search(r'data-width="(\d+)" data-height="(\d+)"', html)
        if m:
            tone = re.search(r'tone-(light|dark)', html)
            (idx.parent / 'brand.css').write_text(brand_css(int(m.group(1)), int(m.group(2)), ' split' in html,
                                                            tone.group(1) if tone else 'light'))
            print(f'rebranded {idx.parent}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'new', 'check', 'render', 'brand'])
    ap.add_argument('project', nargs='?')
    ap.add_argument('name', nargs='?')
    ap.add_argument('--template', default='steps')
    ap.add_argument('--canvas', default='1080x1920')
    ap.add_argument('--duration', type=float, default=6.0)
    ap.add_argument('--feel')
    ap.add_argument('--split', action='store_true')
    ap.add_argument('--tone', choices=['light', 'dark'])
    ap.add_argument('--backdrop', help="photo path or name from brand.json style.backdrop.photos, or 'none'")
    a = ap.parse_args()
    if a.cmd == 'list':
        print('Templates:')
        for k, v in TEMPLATES.items():
            print(f'  {k:9s} {v["about"]}')
        print('Feels:')
        for k, v in FEELS.items():
            print(f'  {k:9s} {v}')
    elif a.cmd == 'brand':
        rebrand()
    elif not (a.project and a.name):
        die('project and name are required')
    elif a.cmd == 'new':
        new(a.project, a.name, a.template, a.canvas, a.duration, a.feel, a.split, tone=a.tone, backdrop=a.backdrop)
    elif a.cmd == 'check':
        check(a.project, a.name)
    else:
        render(a.project, a.name)
