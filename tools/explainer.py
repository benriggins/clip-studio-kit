#!/usr/bin/env python3
"""Animated explainer graphics (HyperFrames: HTML + GSAP rendered to video; free, Apache-2.0), on YOUR brand.

usage:
  explainer.py new    <project> <name> --canvas 1080x1920 [--duration 6]   scaffold from the brand template
  explainer.py check  <project> <name>                                   HyperFrames lint/layout/contrast check
  explainer.py render <project> <name>                                   -> graphics/<name>/renders/<name>.mp4
  explainer.py brand                                                     rebuild every brand.css from brand.json

Files live in projects/<project>/graphics/<name>/. Edit index.html to build the idea; then add to the edit plan:
  "graphics": [{"file": "graphics/<name>/renders/<name>.mp4", "at": <seconds in the cut>}]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, brand, die  # noqa: E402

HF = 'hyperframes@0.8.34'
TEMPLATE = ROOT / 'graphics' / '_template' / 'index.html'
NODE_MODULES = ROOT / 'graphics' / 'node_modules'


def npx():
    exe = shutil.which('npx') or shutil.which('npx.cmd')
    if not exe:
        die('Node.js (npx) not found. Run setup again.')
    return exe


def brand_css(W, H):
    b = brand()
    c, f = b['colors'], b['fonts']
    vertical = H > W
    faces = []
    for role in ('display', 'display_italic', 'body'):
        if role in f:
            fam = f[role]['family']
            style = 'italic' if role.endswith('italic') else 'normal'
            faces.append(f'@font-face {{ font-family: "{fam}"; src: url("assets/fonts/{Path(f[role]["file"]).name}"); '
                         f'font-style: {style}; font-weight: 100 900; }}')
    disp = f['display']['family']
    body = f['body']['family']
    return '\n'.join(faces) + f'''
:root {{
  --bg: {c['background']}; --surface: {c['surface']}; --text: {c['text']}; --muted: {c['muted']}; --accent: {c['accent']};
  --font-display: "{disp}", Georgia, serif; --font-body: "{body}", system-ui, sans-serif;
  --pad-x: {96 if vertical else 160}px; --safe-top: {int(H * 0.29) if vertical else 120}px;
  --safe-bottom: {int(H * 0.32) if vertical else 150}px;
  --h1: {92 if vertical else 96}px; --step: {46 if vertical else 40}px;
}}
* {{ box-sizing: border-box; margin: 0; }}
.b-root {{ position: relative; overflow: hidden; background: radial-gradient(90% 60% at 50% 40%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 62%), var(--bg); color: var(--text); font-family: var(--font-body); }}
.fill {{ position: absolute; inset: 0; pointer-events: none; }}
.b-grid {{ background-image: linear-gradient(color-mix(in srgb, var(--text) 5%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--text) 5%, transparent) 1px, transparent 1px); background-size: 60px 60px; mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%); }}
.b-vignette {{ background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.45)); }}
.b-eyebrow {{ font: 700 {24 if vertical else 22}px/1 var(--font-body); letter-spacing: .28em; text-transform: uppercase; color: var(--accent); }}
.b-headline {{ margin-top: 22px; font: 400 var(--h1)/1.02 var(--font-display); letter-spacing: -.02em; color: var(--text); }}
.b-headline em {{ font-style: italic; color: var(--accent); }}
.b-rule {{ margin-top: 30px; width: 120px; height: 3px; background: var(--accent); }}
.b-step {{ display: flex; align-items: baseline; gap: 22px; font: 600 var(--step)/1.2 var(--font-body); color: var(--text); }}
.b-step .n {{ font: 400 calc(var(--step) * 1.1)/1 var(--font-display); color: var(--accent); min-width: 1.2em; }}
.is-accent {{ color: var(--accent); }}
'''


def comp_dir(project, name):
    return ROOT / 'projects' / project / 'graphics' / name


def new(project, name, canvas, duration):
    W, H = (int(v) for v in canvas.lower().split('x'))
    d = comp_dir(project, name)
    if d.exists():
        die(f'{d} already exists')
    d.parent.mkdir(parents=True, exist_ok=True)
    env = {**__import__('os').environ, 'HYPERFRAMES_SKIP_SKILLS': '1'}
    subprocess.run([npx(), '--yes', HF, 'init', name, '--example', 'blank', '--non-interactive', '--skip-transcribe'],
                   cwd=d.parent, check=True, env=env, stdout=subprocess.DEVNULL)
    (d / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)
    (d / 'assets' / 'js').mkdir(parents=True, exist_ok=True)
    for f in brand()['fonts'].values():
        if isinstance(f, dict) and f.get('file'):
            shutil.copy(ROOT / f['file'], d / 'assets' / 'fonts')
    for js in ('gsap.min.js', 'CustomEase.min.js'):
        shutil.copy(NODE_MODULES / 'gsap' / 'dist' / js, d / 'assets' / 'js')
    (d / 'brand.css').write_text(brand_css(W, H))
    html = (TEMPLATE.read_text().replace('__COMP_ID__', name).replace('__W__', str(W)).replace('__H__', str(H))
            .replace('__DUR__', str(duration)).replace('__TOUT__', f'{duration - 0.45:.2f}'))
    (d / 'index.html').write_text(html)
    print(f'scaffolded {d}\n  edit index.html (labels = the speaker\'s words), then: explainer.py check / render')


def check(project, name):
    subprocess.run([npx(), '--yes', HF, 'check'], cwd=comp_dir(project, name), check=False)


def render(project, name):
    d = comp_dir(project, name)
    (d / 'renders').mkdir(exist_ok=True)
    out = d / 'renders' / f'{name}.mp4'
    subprocess.run([npx(), '--yes', HF, 'render', '.', '--fps', '30', '--quality', 'high', '--format', 'mp4',
                    '-o', str(out), '--quiet'], cwd=d, check=True)
    print(f'rendered {out}')


def rebrand():
    import re
    for idx in (ROOT / 'projects').glob('*/graphics/*/index.html'):
        m = re.search(r'data-width="(\d+)"\s+data-height="(\d+)"', idx.read_text())
        if m:
            (idx.parent / 'brand.css').write_text(brand_css(int(m.group(1)), int(m.group(2))))
            print(f'rebranded {idx.parent}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['new', 'check', 'render', 'brand'])
    ap.add_argument('project', nargs='?')
    ap.add_argument('name', nargs='?')
    ap.add_argument('--canvas', default='1080x1920')
    ap.add_argument('--duration', type=float, default=6.0)
    a = ap.parse_args()
    if a.cmd == 'brand':
        rebrand()
    elif not (a.project and a.name):
        die('project and name are required')
    elif a.cmd == 'new':
        new(a.project, a.name, a.canvas, a.duration)
    elif a.cmd == 'check':
        check(a.project, a.name)
    else:
        render(a.project, a.name)
