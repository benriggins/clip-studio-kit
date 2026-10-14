#!/usr/bin/env python3
"""Style Lab: SHOW the user the choices, in their own brand, so they pick by looking, not by reading.

usage:
  stylelab.py looks                      slide templates, animation feels and caption styles → gallery.html
  stylelab.py clip <clip-plan.json> <clip-id>
                                         the same clip from their real footage, three ways (pace, crop, captions)
                                         → compare.html

Output goes to my-studio/stylelab/ and opens in the browser. Record their picks in my-studio/brand.json ("style"
and "captions.style") and in my-studio/MY-STYLE.md.
"""
import json
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, STUDIO, brand, die, ffmpeg, has_libass, run  # noqa: E402
from templates import FEELS, TEMPLATES  # noqa: E402

LAB = STUDIO / 'stylelab'
PY = sys.executable
SAMPLE = ("Most people think they need more time. They don't. They need a system that tells every hour where to go. "
          "That is the whole game.")

CAPTION_STYLES = {
    'rise': 'Each line rises into place. Clean and calm; the default.',
    'karaoke': 'The whole line shows, and the word being spoken lights up in your accent colour.',
    'pop': '1–3 big words at a time, popping in. High energy, very readable on mute.',
}
VARIANTS = {   # Style Lab "clip" variants: (label, override, description)
    'A': ({'style': {'pace': 'natural', 'crop': 'alternate'}, 'captions': {'style': 'rise'}},
          'Natural pace · wide/tight framing · rising captions'),
    'B': ({'style': {'pace': 'tight', 'crop': 'punch'}, 'captions': {'style': 'pop'}},
          'Tight pace (pauses cut) · punch-in on hooks and payoffs · pop captions'),
    'C': ({'style': {'pace': 'natural', 'crop': 'locked'}, 'captions': {'style': 'karaoke'}},
          'Natural pace · one locked framing · karaoke captions'),
}


def tool(name, *args, env=None):
    return subprocess.run([PY, str(ROOT / 'tools' / f'{name}.py'), *map(str, args)], check=True,
                          env={**os.environ, **(env or {})}, capture_output=True, text=True)


def caption_demo(style, out):
    """A 7 s caption sample over the brand background, with natural word timing."""
    proj = ROOT / 'projects' / '_stylelab'
    (proj / 'transcript' / 'V1').mkdir(parents=True, exist_ok=True)
    words, t = [], 0.4
    for w in SAMPLE.split():
        d = 0.16 + 0.035 * len(w)
        words.append({'w': w, 's': round(t, 2), 'e': round(t + d, 2)})
        t += d + (0.35 if w[-1] in '.,' else 0.05)
    (proj / 'transcript' / 'V1' / 'words.json').write_text(json.dumps(words))
    plan = {'id': f'cap-{style}', 'canvas': {'width': 1080, 'height': 1920, 'fps': 30}, 'accents': ['system', 'whole game'],
            'segments': [{'id': 'S1', 'take': 'V1', 'in': 0.0, 'out': round(t + 0.3, 2), 'text': SAMPLE}]}
    pdir = proj / f'cap-{style}'
    pdir.mkdir(exist_ok=True)
    (pdir / 'edit-plan.json').write_text(json.dumps(plan))
    tool('captions', pdir / 'edit-plan.json', env={'CLIP_BRAND_OVERRIDE': json.dumps({'captions': {'style': style}})})
    b = brand()['colors']
    ass = str(pdir / 'captions.ass').replace(':', '\\:')
    fonts = str(ROOT / 'fonts').replace(':', '\\:')
    run([ffmpeg(), '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=c={b["surface"]}:s=1080x1920:r=30:d={t + 0.6:.2f}',
         '-vf', f"ass='{ass}':fontsdir='{fonts}',format=yuv420p", '-c:v', 'libx264', '-crf', '22', out])


def page(title, intro, sections):
    css = ('body{margin:0;background:#0d0f12;color:#eee;font:16px/1.5 system-ui,sans-serif}'
           'main{max-width:1280px;margin:0 auto;padding:40px 24px}h1{font-size:34px;margin:0 0 6px}'
           'h2{margin:48px 0 6px;font-size:24px}.intro{color:#aaa;max-width:760px}'
           '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:22px;margin-top:18px}'
           '.card{background:#171a1f;border-radius:14px;overflow:hidden;border:1px solid #262a31}'
           '.card video{width:100%;display:block;background:#000}.card div{padding:12px 14px 16px}'
           '.card b{display:block;font-size:17px;margin-bottom:4px}.card span{color:#aaa;font-size:14px}'
           '.wide{grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}')
    body = ''.join(
        f'<h2>{h}</h2><p class="intro">{p}</p><div class="grid {cls}">' +
        ''.join(f'<div class="card"><video src="{v}" autoplay loop muted playsinline></video>'
                f'<div><b>{n}</b><span>{d}</span></div></div>' for n, v, d in cards) + '</div>'
        for h, p, cls, cards in sections)
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>{css}</style></head>'
            f'<body><main><h1>{title}</h1><p class="intro">{intro}</p>{body}</main></body></html>')


def looks():
    import explainer
    LAB.mkdir(parents=True, exist_ok=True)
    proj = '_stylelab'
    gdir = ROOT / 'projects' / proj / 'graphics'
    shutil.rmtree(gdir, ignore_errors=True)
    feel = brand().get('style', {}).get('feel', 'smooth')
    tcards, fcards, ccards = [], [], []
    print('rendering slide templates …')
    for name in TEMPLATES:
        explainer.new(proj, f't-{name}', name, '1080x1920', 5.0, feel, quiet=True)
        src = explainer.render(proj, f't-{name}', quiet=True)
        shutil.copy(src, LAB / f'template-{name}.mp4')
        tcards.append((name, f'template-{name}.mp4', TEMPLATES[name]['about']))
        print(f'  {name}')
    print('rendering animation feels …')
    for f in FEELS:
        explainer.new(proj, f'f-{f}', 'steps', '1080x1920', 4.5, f, quiet=True)
        src = explainer.render(proj, f'f-{f}', quiet=True)
        shutil.copy(src, LAB / f'feel-{f}.mp4')
        fcards.append((f, f'feel-{f}.mp4', FEELS[f]))
        print(f'  {f}')
    if has_libass():
        print('rendering caption styles …')
        for st, about in CAPTION_STYLES.items():
            caption_demo(st, LAB / f'captions-{st}.mp4')
            ccards.append((st, f'captions-{st}.mp4', about))
            print(f'  {st}')
    b = brand()
    html = page(f'Style Lab: {b.get("name", "your brand")}',
                'Everything below is rendered in YOUR colours and fonts. Pick one of each. Tell Claude Code the names '
                '(for example: "tiers and compare, punchy, karaoke"). You can change your mind any time.',
                [('1. Slide templates (pick your favourites; every video can mix them)',
                  'Animated explainers appear while you talk, showing what your words alone can\'t.', '', tcards),
                 ('2. Animation feel (pick one)', 'How every slide moves.', '', fcards),
                 ('3. Caption style (pick one)', 'Captions on every line (most people watch muted).', '', ccards)])
    out = LAB / 'gallery.html'
    out.write_text(html)
    if not os.environ.get("CLIP_NO_OPEN"):
        webbrowser.open(out.as_uri())
    print(f'\ngallery → {out}')


def clip(plan_path, cid):
    plan_path = Path(plan_path).resolve()
    project = plan_path.parent.parent if plan_path.parent.name == 'chatgpt' else plan_path.parent
    LAB.mkdir(parents=True, exist_ok=True)
    cards = []
    for v, (override, about) in VARIANTS.items():
        env = {'CLIP_BRAND_OVERRIDE': json.dumps(override)}
        print(f'variant {v}: {about}')
        tool('plan', plan_path, '--only', cid, '--suffix', f'style{v}', env=env)
        p = project / f'{cid}-style{v}' / 'edit-plan.json'
        if not p.exists():
            die(f'plan for {cid} failed; run plan.py on it first to see why')
        tool('captions', p, env=env)
        tool('render', p, '--draft', env=env)
        src = project / f'{cid}-style{v}' / 'exports' / f'{cid}-style{v}-draft.mp4'
        shutil.copy(src, LAB / f'variant-{v}.mp4')
        cards.append((f'Variant {v}', f'variant-{v}.mp4', about))
    html = page('Style Lab: your footage, three ways',
                'The same clip, edited three ways. Watch each with sound. Pick a favourite, or mix: for example "B\'s '
                'pace with A\'s captions".', [('Pick your editing style', '', 'wide', cards)])
    out = LAB / 'compare.html'
    out.write_text(html)
    if not os.environ.get("CLIP_NO_OPEN"):
        webbrowser.open(out.as_uri())
    print(f'\ncompare → {out}')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('looks', 'clip'):
        die(__doc__)
    if sys.argv[1] == 'looks':
        looks()
    else:
        clip(*sys.argv[2:4])
