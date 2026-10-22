#!/usr/bin/env python3
"""Business-cinema motion graphics, themed from my-studio/brand.json (colours + fonts). Used by cinema.py.

Look: real-UI objects (iOS-style cream glass) floating in 3D around him, some BEHIND his head (layer "back" +
depth.py), editorial stat pages, AI-image stickers. Colours: cream/white first, Sovereign gold second, royal third.
Motion (hf-motion-doctrine): one current (content travels LEFT: enters from the right mid-flight, exits left
mid-flight), no idle floating; every hold is owned by UI life (typing, ticks, timers, progress bars).

kinds
  search   Spotlight-style bar that types the query on the words that say it
  cards    glass cards (icon + title), optional strike-through; each card "layer": front | back
  check    big glass card: eyebrow, title, row of chips that tick in one by one
  timer    iOS-style timer card that counts 0:00:00 -> 1:00:00 with a progress ring
  fan      app cards fanned around the head (layer back), progress bars running, then thrown out left
  stat     editorial page (cream, gold brackets, giant number, royal footer band) + face card + stickers
  person   glass statement card + "DM me" pill
A graphic lists its "parts" (all share one clock). Times are seconds from the graphic's start; "out" = exit time.
Every label is the speaker's own words.

usage: motionpack.py <spec.json> [name …]  -> projects/<p>/graphics/<name>/renders/<name>.mov (+ <name>-back.mov)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from _common import brand  # noqa: E402
W, H = 1080, 1920
HF = 'hyperframes@0.8.34'

CSS_TEMPLATE = '''
@font-face { font-family: "Display"; src: url("assets/fonts/Display.ttf"); font-weight: 100 900; }
@font-face { font-family: "Display"; src: url("assets/fonts/Display-Italic.ttf"); font-style: italic; font-weight: 100 900; }
@font-face { font-family: "UI"; src: url("assets/fonts/UI.ttf"); font-weight: 100 900; }
@font-face { font-family: "PlexMono"; src: url("assets/fonts/Mono.ttf"); }
:root { __TOKENS__ }
html, body { margin: 0; width: 1080px; height: 1920px; background: transparent; overflow: hidden; }
#root { position: relative; width: 1080px; height: 1920px; perspective: 1700px; font-family: "UI", sans-serif; color: var(--ink);
  -webkit-font-smoothing: antialiased; }
.g { position: absolute; border-radius: 44px; transform-style: preserve-3d; will-change: transform; backface-visibility: hidden;
  background: linear-gradient(165deg, rgba(255,254,250,.97) 0%, rgba(247,242,231,.95) 60%, rgba(239,232,217,.94) 100%);
  border: 1.5px solid rgba(255,255,255,.9); outline: 1px solid rgba(166,135,76,.28); outline-offset: -1px;
  box-shadow: 0 40px 80px -10px rgba(20,8,40,.42), 0 10px 22px rgba(20,8,40,.20), inset 0 2px 0 rgba(255,255,255,1),
              inset 0 -2px 6px rgba(166,135,76,.10); }
.mono { font-family: "PlexMono"; text-transform: uppercase; letter-spacing: .18em; color: var(--gold-t); font-size: 21px; }
.search { display: flex; align-items: center; gap: 22px; padding: 26px 34px; border-radius: 36px; }
.search svg { width: 46px; height: 46px; flex: none; fill: none; stroke: var(--muted); stroke-width: 6; stroke-linecap: round; }
.search .q { font-size: 46px; font-weight: 560; letter-spacing: -.015em; white-space: nowrap; }
.search .q i { font-style: normal; opacity: 0; }
.caret { width: 4px; height: 52px; background: var(--royal); border-radius: 2px; margin-left: -14px; }
.card { display: flex; align-items: center; gap: 24px; padding: 22px 38px 22px 22px; }
.ico { flex: none; width: 88px; height: 88px; border-radius: 24px; display: grid; place-items: center;
  background: linear-gradient(150deg, var(--royal-hi), var(--royal-dd)); box-shadow: inset 0 2px 0 rgba(255,255,255,.22), 0 6px 14px rgba(28,8,56,.3); }
.ico svg { width: 52px; height: 52px; fill: none; stroke: var(--gold); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
.card .t { font-weight: 650; font-size: 44px; letter-spacing: -.02em; white-space: nowrap; }
.card .s { margin-bottom: 6px; }
.strike { position: absolute; left: 20px; right: 20px; top: 50%; height: 6px; margin-top: -3px; border-radius: 3px;
  background: var(--royal-dd); transform: scaleX(0); transform-origin: left center; opacity: .85; }
.check { left: 60px; right: 60px; padding: 36px 44px 40px; }
.check .h { font-family: "Display"; font-weight: 520; font-size: 82px; line-height: 1; letter-spacing: -.02em; color: var(--royal-dd); margin-top: 14px; }
.check .h em, .person .h em, .stat em { font-style: italic; color: var(--gold-d); font-weight: 480; }
.chips { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 26px; }
.chip { display: flex; align-items: center; gap: 12px; padding: 14px 24px 14px 16px; border-radius: 999px; background: rgba(75,30,138,.07);
  border: 1.5px solid rgba(75,30,138,.14); font-size: 32px; font-weight: 600; white-space: nowrap; }
.tick { width: 38px; height: 38px; border-radius: 50%; background: var(--royal); display: grid; place-items: center; transform: scale(0); }
.tick svg { width: 22px; height: 22px; fill: none; stroke: #fff; stroke-width: 4.5; stroke-linecap: round; stroke-linejoin: round; }
.timer { display: flex; align-items: center; gap: 30px; padding: 30px 44px 30px 30px; }
.ring { width: 150px; height: 150px; flex: none; transform: rotate(-90deg); }
.ring circle { fill: none; stroke-width: 12; }
.digits { display: flex; font-size: 118px; font-weight: 300; letter-spacing: -.03em; font-variant-numeric: tabular-nums; line-height: 1; color: var(--ink); margin-top: 8px; }
.reel { height: 1em; overflow: hidden; display: inline-block; }
.reel > span { display: block; }
.reel > span > b { display: block; height: 1em; font-weight: 300; }
.sep { width: .32em; text-align: center; color: var(--muted); }
.fan { display: flex; align-items: center; gap: 26px; padding: 20px 36px 20px 20px; width: 600px; border-radius: 40px; }
.art { width: 150px; height: 150px; flex: none; border-radius: 28px; display: grid; place-items: center; font-family: "Display";
  font-style: italic; font-size: 86px; color: var(--gold); background: radial-gradient(120% 120% at 20% 10%, var(--royal-hi), var(--royal-dd) 70%);
  box-shadow: inset 0 2px 0 rgba(255,255,255,.2); }
.fan .t { font-size: 44px; font-weight: 680; letter-spacing: -.02em; }
.bar { height: 8px; border-radius: 4px; background: rgba(23,16,31,.12); margin-top: 18px; overflow: hidden; width: 330px; }
.bar i { display: block; height: 100%; width: 100%; background: var(--royal); transform: scaleX(.05); transform-origin: left; }
.person { left: 60px; right: 60px; padding: 34px 44px 40px; }
.person .h { font-family: "Display"; font-weight: 520; font-size: 76px; line-height: 1.02; letter-spacing: -.02em; color: var(--royal-dd); margin-top: 14px; }
.dm { position: absolute; padding: 18px 34px; border-radius: 999px; background: var(--royal-dd); color: #fff; font-weight: 650;
  font-size: 36px; display: flex; gap: 14px; align-items: center; box-shadow: 0 22px 44px rgba(20,8,40,.4); border: 1.5px solid var(--gold); }
.dm svg { width: 32px; height: 32px; fill: none; stroke: var(--gold); stroke-width: 4; stroke-linejoin: round; }
.page { position: absolute; inset: 0; background: var(--cream); }
.band { position: absolute; left: 0; right: 0; bottom: 0; height: 470px; background: var(--royal-dd); }
.band:before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: var(--gold); }
.mark { position: absolute; bottom: 52px; left: 0; right: 0; text-align: center; font-family: "PlexMono"; font-size: 22px; letter-spacing: .34em; color: var(--gold); }
.frame { position: absolute; border: 3px solid var(--gold); border-radius: 50px; }
.br { position: absolute; width: 64px; height: 64px; border-color: var(--gold-d); border-style: solid; border-width: 0; }
.stat { position: absolute; left: 90px; right: 90px; }
.stat .s { font-size: 26px; display: flex; align-items: center; gap: 18px; }
.stat .s:before { content: ""; width: 56px; height: 3px; background: var(--gold-d); }
.stat .num { font-family: "Display"; font-weight: 560; font-size: 200px; line-height: .9; letter-spacing: -.035em; color: var(--royal); }
.stat .line { font-size: 60px; font-weight: 650; letter-spacing: -.02em; margin-top: 14px; }
.mask { overflow: hidden; display: block; padding-bottom: .08em; }
.mask > span { display: inline-block; }
.big { position: absolute; left: 0; right: 0; text-align: center; font-family: "Display"; font-style: italic; font-weight: 420;
  font-size: 250px; line-height: .9; letter-spacing: -.03em; color: #FBF7EE; text-shadow: 0 20px 60px rgba(20,8,40,.35); white-space: nowrap; }
.stk { position: absolute; filter: drop-shadow(0 26px 28px rgba(28,8,56,.38)) drop-shadow(0 4px 6px rgba(28,8,56,.25)); }
'''

ICONS = {
    'megaphone': '<path d="M14 34 L44 22 L44 58 L14 46 Z"/><path d="M44 22 L68 12 L68 68 L44 58"/><path d="M22 47 L26 64 L36 64 L33 51"/>',
    'play': '<rect x="10" y="16" width="60" height="48" rx="12"/><path d="M34 29 L50 40 L34 51 Z"/>',
    'funnel': '<path d="M12 16 H68 L47 42 V62 L33 68 V42 Z"/>',
    'plane': '<path d="M10 40 L70 12 L54 68 L38 46 Z"/><path d="M38 46 L70 12"/>',
}
TICK = '<svg viewBox="0 0 24 24"><path d="M5 12.5 L10 17 L19 7"/></svg>'
LENS = '<svg viewBox="0 0 60 60"><circle cx="25" cy="25" r="16"/><path d="M37 37 L52 52"/></svg>'
PLANE = '<svg viewBox="0 0 80 80"><path d="M10 40 L70 12 L54 68 L38 46 Z"/><path d="M38 46 L70 12"/></svg>'

ENTER = 'x:{x}, opacity:0, rotationY:-38, rotationX:{rx}, z:-260'   # arrives from the right, mid-flight
EASE_IN = 'power4.out'


def pos(p):
    return ';'.join(f'{k}:{v}px' for k, v in p.items())


def exit_left(sel, at, i=0):
    return (f'tl.to("{sel}", {{x:-1300, rotationY:28, opacity:0, filter:"blur(14px)", duration:.5, '
            f'ease:"power4.in"}}, {at + i * .05});')


def p_search(p):
    q = ''.join(f'<i>{c if c != " " else "&nbsp;"}</i>' for c in p['query'])
    html = f'<div class="g search" id="sr" style="{pos(p["pos"])}">{LENS}<div class="q" id="q">{q}</div><div class="caret" id="ct"></div></div>'
    t0, t1 = p['type']
    n = len(p['query'])
    js = [f'tl.fromTo("#sr", {{y:-260, opacity:0, rotationX:55}}, {{y:0, opacity:1, rotationX:{p.get("rx", 10)}, duration:.75, ease:"{EASE_IN}"}}, {p["at"]});',
          f'gsap.utils.toArray("#q i").forEach((el, k) => tl.set(el, {{opacity:1}}, {t0} + k * {(t1 - t0) / max(n, 1):.4f}));',
          f'for (let k = 0; k < {int((p["out"] - p["at"]) / .5)}; k++) tl.set("#ct", {{opacity: k % 2 ? 1 : 0}}, {p["at"]} + k * .5);',
          exit_left('#sr', p['out'])]
    return [(p.get('layer', 'front'), html, '\n'.join(js))]


def p_cards(p):
    out = []
    for i, c in enumerate(p['cards']):
        cid = f'c{p.get("id", "")}{i}'
        sub = f'<div class="mono s">{c["sub"]}</div>' if c.get('sub') else ''
        html = (f'<div class="g card" id="{cid}" style="{pos(c["pos"])}"><div class="ico"><svg viewBox="0 0 80 80">{ICONS[c["icon"]]}</svg></div>'
                f'<div>{sub}<div class="t">{c["title"]}</div></div><div class="strike" id="k{cid}"></div></div>')
        t = c.get('tilt', [6, -10, 0])
        js = [f'tl.fromTo("#{cid}", {{{ENTER.format(x=420, rx=t[0] + 20)}, rotation:{t[2] + 8}}}, '
              f'{{x:0, opacity:1, z:0, rotationX:{t[0]}, rotationY:{t[1]}, rotation:{t[2]}, duration:.7, ease:"{EASE_IN}"}}, {c["at"]});']
        if p.get('strike'):
            js.append(f'tl.to("#k{cid}", {{scaleX:1, duration:.28, ease:"power3.out"}}, {c["at"] + .55});')
            js.append(f'tl.to("#{cid}", {{opacity:.86, filter:"saturate(.3)", duration:.28}}, {c["at"] + .6});')
        js.append(exit_left(f'#{cid}', p['out'], i))
        out.append((c.get('layer', 'front'), html, '\n'.join(js)))
    return out


def p_check(p):
    chips = ''.join(f'<div class="chip" id="ch{i}"><div class="tick" id="tk{i}">{TICK}</div>{c["label"]}</div>'
                    for i, c in enumerate(p['chips']))
    html = (f'<div class="g check" id="ck" style="top:{p.get("top", 140)}px"><div class="mono">{p["eyebrow"]}</div>'
            f'<div class="h">{p["title"]}</div><div class="chips">{chips}</div></div>')
    js = [f'tl.fromTo("#ck", {{{ENTER.format(x=600, rx=30)}}}, {{x:0, opacity:1, z:0, rotationX:8, rotationY:-6, duration:.8, ease:"{EASE_IN}"}}, {p["at"]});']
    for i, c in enumerate(p['chips']):
        js.append(f'tl.fromTo("#ch{i}", {{opacity:0, x:60}}, {{opacity:1, x:0, duration:.35, ease:"power3.out"}}, {c["at"]});')
        js.append(f'tl.to("#tk{i}", {{scale:1, duration:.3, ease:"back.out(1.7)"}}, {c["at"] + .25});')
    js.append(exit_left('#ck', p['out']))
    return [(p.get('layer', 'front'), html, '\n'.join(js))]


def reel(seq, rid):
    return f'<span class="reel"><span id="{rid}">' + ''.join(f'<b>{d}</b>' for d in seq) + '</span></span>'


def p_timer(p):
    # rolling digit reels that land on 1:00:00; each reel is a strip of digits moved by transform (seek-safe)
    reels = {'h': list('01'), 'mt': list('0123450'), 'mo': [str(k % 10) for k in range(61)],
             'st': [str(k % 6) for k in range(25)], 'so': [str(k % 10) for k in range(91)]}
    digits = (reel(reels['h'], 'rh') + '<span class="sep">:</span>' + reel(reels['mt'], 'rmt') + reel(reels['mo'], 'rmo')
              + '<span class="sep">:</span>' + reel(reels['st'], 'rst') + reel(reels['so'], 'rso'))
    ring = ('<svg class="ring" viewBox="0 0 160 160"><circle cx="80" cy="80" r="66" stroke="rgba(23,16,31,.1)"/>'
            '<circle id="rg" cx="80" cy="80" r="66" stroke="#4B1E8A" stroke-linecap="round" stroke-dasharray="414.7" stroke-dashoffset="414.7"/></svg>')
    html = (f'<div class="g timer" id="tm" style="{pos(p["pos"])}">{ring}<div><div class="mono">{p["label"]}</div>'
            f'<div class="digits">{digits}</div></div></div>')
    a, b = p['count']
    js = [f'tl.fromTo("#tm", {{{ENTER.format(x=500, rx=24)}}}, {{x:0, opacity:1, z:0, rotationX:6, rotationY:-8, rotation:-2, duration:.7, ease:"{EASE_IN}"}}, {p["at"]});']
    js.append(f'tl.set("#rh", {{yPercent:-50}}, {b - .02});')   # the hour flips only when the minutes wrap
    for k, seq in reels.items():
        if k == 'h':
            continue
        # clean digit snaps (no half-rolled digits): linear steps, one per cell
        js.append(f'tl.to("#r{k}", {{yPercent:-100 * {len(seq) - 1} / {len(seq)}, duration:{b - a}, ease:"steps({len(seq) - 1})"}}, {a});')
    js.append(f'tl.to("#rg", {{attr:{{"stroke-dashoffset":0}}, duration:{b - a}, ease:"none"}}, {a});')
    js.append(f'tl.to("#tm", {{scale:1.06, duration:.12, yoyo:true, repeat:1, ease:"power2.out"}}, {b});')
    js.append(exit_left('#tm', p['out']))
    return [(p.get('layer', 'front'), html, '\n'.join(js))]


def p_fan(p):
    out = []
    for i, c in enumerate(p['cards']):
        fid = f'f{i}'
        html = (f'<div class="g fan" id="{fid}" style="{pos(c["pos"])}"><div class="art">{c.get("art", c["label"][0])}</div>'
                f'<div><div class="mono">{c.get("sub", "")}</div><div class="t">{c["label"]}</div><div class="bar"><i id="b{fid}"></i></div></div></div>')
        js = [f'tl.fromTo("#{fid}", {{{ENTER.format(x=700, rx=0)}, rotation:{c["rot"] + 25}}}, {{x:0, opacity:1, z:0, rotationX:0, '
              f'rotationY:{c.get("ry", 0)}, rotation:{c["rot"]}, duration:.7, ease:"{EASE_IN}"}}, {p["at"] + i * .1});',
              f'tl.to("#b{fid}", {{scaleX:{c.get("progress", .8)}, duration:{p["out"] - p["at"]}, ease:"none"}}, {p["at"]});',
              exit_left(f'#{fid}', p['out'], i)]
        out.append((c.get('layer', 'back'), html, '\n'.join(js)))
    return out


def p_person(p):
    html = (f'<div class="g person" id="pc" style="top:{p.get("top", 140)}px"><div class="mono">{p["eyebrow"]}</div>'
            f'<div class="h">{p["title"]}</div></div>')
    js = [f'tl.fromTo("#pc", {{{ENTER.format(x=600, rx=30)}}}, {{x:0, opacity:1, z:0, rotationX:8, rotationY:-6, duration:.8, ease:"{EASE_IN}"}}, {p["at"]});']
    if p.get('dm_at') is not None:
        html += f'<div class="dm" id="dm" style="right:70px;top:{p.get("top", 140) + p.get("dm_offset", 330)}px">{PLANE}DM me</div>'
        js.append(f'tl.fromTo("#dm", {{x:240, opacity:0, scale:.8}}, {{x:0, opacity:1, scale:1, duration:.5, ease:"{EASE_IN}"}}, {p["dm_at"]});')
    return [(p.get('layer', 'front'), html, '\n'.join(js))]


def p_stat(p):
    fc = p['face_card']
    x, y, w, h = fc['x'], fc['y'], fc['w'], fc['h']
    stk = ''.join(f'<img class="stk" id="st{i}" src="assets/img/{Path(k["src"]).name}" style="left:{k["x"]}px;top:{k["y"]}px;width:{k["w"]}px" />'
                  for i, k in enumerate(p.get('stickers', [])))
    html = f'''<div class="page" id="pg"></div>
<div class="frame" id="fr" style="left:{x - 10}px;top:{y - 10}px;width:{w + 14}px;height:{h + 14}px"></div>
<div class="br" style="left:40px;top:40px;border-top-width:4px;border-left-width:4px"></div>
<div class="br" style="right:40px;top:40px;border-top-width:4px;border-right-width:4px"></div>
<div class="br" style="left:40px;top:1360px;border-bottom-width:4px;border-left-width:4px"></div>
<div class="br" style="right:40px;top:1360px;border-bottom-width:4px;border-right-width:4px"></div>
<div class="stat" style="top:{y + h + 70}px"><div class="mono s" id="se">{p["eyebrow"]}</div>
<div class="num mask"><span id="sn">{p["number"]}</span></div><div class="line mask"><span id="sl">{p["line"]}</span></div></div>
<div class="band" id="bd"><div class="mark">{p.get("mark", "SOVEREIGN STRATEGY SYSTEMS")}</div></div>{stk}'''
    js = ['tl.fromTo("#pg", {xPercent:100}, {xPercent:0, duration:.5, ease:"power4.out"}, 0);',
          'tl.fromTo("#bd", {xPercent:100}, {xPercent:0, duration:.5, ease:"power4.out"}, .04);',
          'tl.from("#fr", {opacity:0, x:200, duration:.5, ease:"power4.out"}, .08);',
          'tl.from(".br", {opacity:0, scale:.4, stagger:.05, duration:.3, ease:"back.out(1.6)"}, .2);',
          'tl.from("#se", {opacity:0, x:60, duration:.35, ease:"power3.out"}, .3);',
          f'tl.from("#sn", {{yPercent:110, duration:.6, ease:"power4.out"}}, {p["number_at"]});',
          f'tl.from("#sl", {{yPercent:110, duration:.5, ease:"power4.out"}}, {p["line_at"]});']
    for i, k in enumerate(p.get('stickers', [])):
        r = k.get('rot', 0)
        js.append(f'tl.fromTo("#st{i}", {{opacity:0, scale:.3, x:260, rotation:{r + 30}}}, {{opacity:1, scale:1, x:0, rotation:{r}, duration:.55, ease:"back.out(1.6)"}}, {k["at"]});')
        js.append(f'tl.to("#st{i}", {{rotation:{r - 4}, scale:1.04, duration:{p["out"] - k["at"] - .6:.2f}, ease:"power1.inOut"}}, {k["at"] + .55});')
    js.append(f'tl.to(["#pg", "#bd", "#fr", ".br", ".stat", ".stk"], {{xPercent:-100, duration:.45, ease:"power4.in"}}, {p["out"]});')
    return [('front', html, '\n'.join(js))]


def p_bigword(p):
    # the "stuck." move: a giant italic word that sits BEHIND his head (layer back + depth.py)
    bid = f'bw{abs(hash(p["word"])) % 9999}'
    html = f'<div class="big" id="{bid}" style="top:{p.get("top", 520)}px;font-size:{p.get("size", 250)}px">{p["word"]}</div>'
    js = (f'tl.fromTo("#{bid}", {{x:500, opacity:0, filter:"blur(18px)"}}, {{x:0, opacity:1, filter:"blur(0px)", duration:.6, ease:"power4.out"}}, {p["at"]});'
          f'tl.to("#{bid}", {{x:-90, duration:{p["out"] - p["at"] - .6:.2f}, ease:"none"}}, {p["at"] + .6});'
          + exit_left(f'#{bid}', p['out']))
    return [(p.get('layer', 'back'), html, js)]


def tokens():
    c = brand().get('colors', {})
    m = brand().get('motion', {})          # optional overrides, same names as the CSS variables below
    acc = c.get('accent', '#D4B470')
    v = {'cream': c.get('paper', '#FBF7EE'), 'ink': c.get('ink', '#17101F'), 'muted': '#776E80', 'gold': acc,
         'gold-d': c.get('gold', acc), 'gold-t': c.get('gold_text', c.get('gold', acc)),
         'royal': c.get('royal', c.get('surface', '#2E2E2E')), 'royal-hi': c.get('royal_hi', c.get('royal', c.get('surface', '#444'))),
         'royal-d': c.get('surface', '#222'), 'royal-dd': c.get('background', '#111'), **m}
    return ' '.join(f'--{k}: {val};' for k, val in v.items())


def font_files():
    f = brand().get('fonts', {})
    pick = lambda *roles: next((ROOT / f[r]['file'] for r in roles if isinstance(f.get(r), dict) and (ROOT / f[r]['file']).exists()), None)  # noqa: E731
    ui = ROOT / 'fonts' / 'Inter[opsz,wght].ttf'
    return {'Display.ttf': pick('display'), 'Display-Italic.ttf': pick('display_italic', 'display'),
            'UI.ttf': pick('ui') or (ui if ui.exists() else pick('body')), 'Mono.ttf': pick('mono', 'body')}


KINDS = {'bigword': p_bigword, 'search': p_search, 'cards': p_cards, 'check': p_check, 'timer': p_timer, 'fan': p_fan,
         'person': p_person, 'stat': p_stat}


def page(name, dur, html, js):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<script src="assets/js/gsap.min.js"></script><style>{CSS_TEMPLATE.replace('__TOKENS__', tokens())}</style></head>
<body><div id="root" data-composition-id="{name}" data-start="0" data-duration="{dur}" data-width="{W}" data-height="{H}">
{html}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
gsap.set(".g", {{ force3D: true }});
{js}
tl.set({{}}, {{}}, {dur});
window.__timelines["{name}"] = tl;
</script></body></html>
'''


def render(d, name, out):
    r = subprocess.run([shutil.which('npx'), '--yes', HF, 'render', '.', '--fps', '30', '--format', 'mov', '--workers', '2',
                        '-o', str(out), '--quiet'], cwd=d, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'render failed for {name}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')
    print(f'rendered {out}')


def build(project, g):
    d = ROOT / 'projects' / project / 'graphics' / g['name']
    (d / 'assets' / 'js').mkdir(parents=True, exist_ok=True)
    (d / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / 'graphics' / 'node_modules' / 'gsap' / 'dist' / 'gsap.min.js', d / 'assets' / 'js')
    for dst, src in font_files().items():
        if src:
            shutil.copy(src, d / 'assets' / 'fonts' / dst)
    for p in g['parts']:
        for k in p.get('stickers', []):
            (d / 'assets' / 'img').mkdir(exist_ok=True)
            shutil.copy(ROOT / 'projects' / project / k['src'], d / 'assets' / 'img' / Path(k['src']).name)
    layers = {'front': ([], []), 'back': ([], [])}
    for p in g['parts']:
        for layer, html, js in KINDS[p['kind']](p):
            layers[layer][0].append(html)
            layers[layer][1].append(js)
    (d / 'renders').mkdir(exist_ok=True)
    for layer, (html, js) in layers.items():
        if not html:
            continue
        suffix = '' if layer == 'front' else '-back'
        sub = d if layer == 'front' else d / 'back'
        if layer == 'back':
            if sub.exists():
                shutil.rmtree(sub)
            shutil.copytree(d / 'assets', sub / 'assets')
        (sub / 'index.html').write_text(page(g['name'] + suffix, g['duration'], '\n'.join(html), '\n'.join(js)))
        render(sub, g['name'] + suffix, d / 'renders' / f'{g["name"]}{suffix}.mov')


if __name__ == '__main__':
    spec = json.loads(Path(sys.argv[1]).read_text())
    only = sys.argv[2:] or None
    for g in spec['graphics']:
        if not only or g['name'] in only:
            build(spec['project'], g)
