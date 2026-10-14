#!/usr/bin/env python3
"""Animated explainer slides (HyperFrames: HTML + GSAP rendered to video; free, Apache-2.0), on YOUR brand.

usage:
  explainer.py list                                                 the slide templates and animation feels
  explainer.py new    <project> <name> --template steps --canvas 1080x1920 [--duration 6] [--feel smooth] [--split]
  explainer.py check  <project> <name>                              HyperFrames lint, layout and contrast check
  explainer.py render <project> <name>                              -> graphics/<name>/renders/<name>.mp4
  explainer.py brand                                                rebuild every brand.css from my-studio/brand.json

Templates: steps, compare, stat, quote, timeline, tiers (see list). --split leaves room for the speaker's live face
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


def brand_css(W, H, split=False):
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
    else:
        box = (f'left: {pad}px; right: {pad}px; top: {int(H * 0.22) if vertical else 120}px; '
               f'bottom: {int(H * 0.32) if vertical else 160}px;')
    return '\n'.join(faces) + f'''
:root {{
  --bg: {c['background']}; --surface: {c['surface']}; --text: {c['text']}; --muted: {c['muted']}; --accent: {c['accent']};
  --font-display: "{f['display']['family']}", Georgia, serif; --font-body: "{f['body']['family']}", system-ui, sans-serif;
  --h1: {(84 if split else 96) if vertical else (78 if split else 96)}px; --step: {44 if vertical else (36 if split else 40)}px;
}}
* {{ box-sizing: border-box; margin: 0; }}
.b-root {{ position: relative; overflow: hidden; color: var(--text); font-family: var(--font-body);
  background: radial-gradient(90% 60% at 50% 40%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 62%), var(--bg); }}
.fill {{ position: absolute; inset: 0; pointer-events: none; }}
#content {{ position: absolute; {box} display: flex; flex-direction: column; justify-content: center; }}
.b-grid {{ background-image: linear-gradient(color-mix(in srgb, var(--text) 5%, transparent) 1px, transparent 1px),
  linear-gradient(90deg, color-mix(in srgb, var(--text) 5%, transparent) 1px, transparent 1px); background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%); }}
.b-vignette {{ background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.45)); }}
.b-eyebrow {{ font: 700 {24 if vertical else 22}px/1 var(--font-body); letter-spacing: .28em; text-transform: uppercase; color: var(--accent); }}
.b-headline {{ margin-top: 22px; font: 400 var(--h1)/1.02 var(--font-display); letter-spacing: -.02em; color: var(--text); }}
.b-headline em {{ font-style: italic; color: var(--accent); }}
.b-rule {{ margin-top: 30px; width: 120px; height: 3px; background: var(--accent); }}
.is-accent {{ color: var(--accent); }}
''' + TEMPLATE_CSS


def comp_dir(project, name):
    return ROOT / 'projects' / project / 'graphics' / name


def new(project, name, template, canvas, duration, feel=None, split=False, quiet=False):
    if template not in TEMPLATES:
        die(f'unknown template {template}: use one of {", ".join(TEMPLATES)}')
    feel = feel or brand().get('style', {}).get('feel', 'smooth')
    if feel not in FEELS:
        die(f'unknown feel {feel}: use one of {", ".join(FEELS)}')
    W, H = (int(v) for v in canvas.lower().split('x'))
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
    (d / 'brand.css').write_text(brand_css(W, H, split))
    (d / 'index.html').write_text(page(name, template, W, H, duration, feel, split))
    if not quiet:
        print(f'scaffolded {d} ({template}, {feel}{", split" if split else ""})\n'
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
            (idx.parent / 'brand.css').write_text(brand_css(int(m.group(1)), int(m.group(2)), ' split"' in html))
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
        new(a.project, a.name, a.template, a.canvas, a.duration, a.feel, a.split)
    elif a.cmd == 'check':
        check(a.project, a.name)
    else:
        render(a.project, a.name)
