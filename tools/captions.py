#!/usr/bin/env python3
"""Word-timed captions for an edit plan: the speaker's real words, line by line, rising into place.

usage: captions.py <edit-plan.json> [out.ass]       (default: next to the plan, captions.ass)

Styles (my-studio/brand.json → captions.style):
  "rise"    each line rises into place from behind a mask; its words light up from dim to full as they are spoken
  "karaoke" the whole line, with the spoken word lit in the accent colour
  "pop"     1-3 big words at a time: the group pops in, words appear as they are spoken, and the word being spoken
            sits in a filled highlight box (brand colours.fill)
Lines are wrapped by measured pixel width (the caption font's real glyph widths), not by character count.
Timing comes from the source transcript's word timestamps mapped onto the cut's clock (each segment's words,
offset by where that segment sits in the cut). Style comes from my-studio/brand.json: caption font, text colour,
accent colour on the plan's "accents" phrases, soft shadow (never a hard outline). verify.py re-transcribes the
render afterwards and flags drift.
"""
import functools
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import FONTS, ROOT, brand, die, norm  # noqa: E402

REVEAL_FRAMES = 16          # ~0.53 s at 30 fps, ease-out quart
FPS = 30
MAX_CHARS = 18
WEAK = {'of', 'a', 'an', 'the', 'to', 'in', 'and', 'from', 'on', 'be', 'i', "i'd", "i'm", 'my', 'your', 'is', 'was',
        'that', 'for', 'at', 'with', 'into', 'but', 'or', 'so'}


def ass_color(hex_):
    h = hex_.lstrip('#')
    return f'&H00{h[4:6]}{h[2:4]}{h[0:2]}&'.upper()


def font_family(path):
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    return f['name'].getDebugName(1)


@functools.lru_cache
def _metrics(path):
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    os2 = f['OS/2']
    return f.getBestCmap(), f['hmtx'].metrics, (os2.usWinAscent + os2.usWinDescent) or f['head'].unitsPerEm


def text_width(text, path, size, spacing=1):
    """Rendered width in pixels: libass scales a font so its win ascent + descent equals the font size."""
    cmap, hmtx, h = _metrics(str(path))
    adv = sum(hmtx.get(cmap.get(ord(ch), '.notdef'), (h * 0.55, 0))[0] for ch in text)
    return adv * size / h + spacing * len(text)


def cut_words(plan, words_by_take):
    """Words of every segment on the cut clock, from that segment's take transcript."""
    out, t = [], 0.0
    for si, s in enumerate(plan['segments']):
        inside = [w for w in words_by_take[s.get('take', 'V1')] if w['s'] >= s['in'] - 0.05 and w['e'] <= s['out'] + 0.05]
        for w in inside:
            out.append({'w': w['w'], 's': t + max(0.0, w['s'] - s['in']), 'e': t + min(s['out'], w['e']) - s['in'],
                        'seg': si})
        t += s['out'] - s['in']
    return out


def mark_accents(words, accents):
    low = [norm(w['w']) for w in words]
    for w in words:
        w['gold'] = False
    for phrase in accents:
        p = [norm(x) for x in phrase.split() if norm(x)]
        for i in range(len(low) - len(p) + 1):
            if p and low[i:i + len(p)] == p:
                for k in range(i, i + len(p)):
                    words[k]['gold'] = True


def lines_of(words, fits=None):
    lines, cur = [], []
    txt = lambda ln: ' '.join(x['w'] for x in ln)  # noqa: E731
    fits = fits or (lambda ws: len(txt(ws)) <= MAX_CHARS)
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (nxt is None or nxt['seg'] != w['seg'] or w['w'][-1] in '.?!'
                or not fits(cur + [nxt])):
            lines.append(cur)
            cur = []
    for i in range(len(lines) - 1):       # never end a line on a weak word mid-thought
        while (len(lines[i]) > 1 and norm(lines[i][-1]['w']) in WEAK and lines[i][-1]['w'][-1] not in '.,?!'
               and lines[i + 1][0]['seg'] == lines[i][-1]['seg']):
            lines[i + 1].insert(0, lines[i].pop())
    out = []                               # fold a lone short word into its neighbour
    for ln in lines:
        if (out and len(ln) == 1 and len(ln[0]['w']) <= 7 and out[-1][-1]['seg'] == ln[0]['seg']
                and fits(out[-1] + ln)):
            out[-1] = out[-1] + ln
        else:
            out.append(ln)
    return out


def ts(t):
    t = max(0.0, t)
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'


def main(plan_path, out_ass=None):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    out_ass = Path(out_ass) if out_ass else plan_path.parent / 'captions.ass'
    b = brand()
    cap = b.get('captions', {})
    font_file = ROOT / b['fonts']['captions']['file']
    if not font_file.exists():
        die(f'caption font {font_file} missing (run: .venv python tools/fetch_fonts.py)')
    family = font_family(font_file)
    upper = cap.get('uppercase', True)
    white, gold = ass_color(cap.get('text', '#FFFFFF')), ass_color(cap.get('accent', b['colors']['accent']))
    W, H = plan['canvas']['width'], plan['canvas']['height']
    if W > H:
        size, base = cap.get('size_landscape', 88), cap.get('baseline_landscape', int(H * 0.89))
    else:
        size, base = cap.get('size_vertical', 112), cap.get('baseline_vertical', int(H * 0.77))
    project = plan_path.parent.parent
    takes = {s.get('take', 'V1') for s in plan['segments']}
    words = cut_words(plan, {t: json.loads((project / 'transcript' / t / 'words.json').read_text()) for t in takes})
    if not words:
        die('no words found inside the plan segments')
    mark_accents(words, plan.get('accents', []))
    # per-clip override, then per-platform default, then the brand default
    style = (plan.get('caption_style') or cap.get('style_by_platform', {}).get(plan.get('platform', ''))
             or cap.get('style', 'rise'))
    show = lambda w: w['w'].upper() if upper else w['w']  # noqa: E731
    margin = cap.get('margin', 100 if H > W else 160)
    maxw = W - 2 * margin
    fill = ass_color(cap.get('box', b['colors'].get('fill', b['colors']['accent'])))
    ink = ass_color(cap.get('box_text', b['colors'].get('on_fill', '#1A1410')))
    shadow = '\\bord5\\3c&H000000&\\3a&H90&\\blur10\\1c&H000000&\\1a&H55&'   # soft dark halo, readable on bright footage
    ev = []

    def emit(a, b, x, y, plain, body, extra='', clip_=''):
        ev.append(f'Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({x},{y + 6:.0f}){clip_}{shadow}{extra}}}{plain}')
        ev.append(f'Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({x},{y:.0f}){clip_}{extra}}}{body}')

    def colour(w, on=False):
        return f'{{\\c{gold}}}{show(w)}{{\\c{white}}}' if (w['gold'] or on) else show(w)

    def fits_at(px, pad=0):
        return lambda ws: text_width(' '.join(show(x) for x in ws), font_file, px) + pad <= maxw

    if style == 'pop':
        big = int(size * cap.get('pop_scale', 1.18))
        fits = fits_at(big, pad=2 * 16)   # room for the highlight box
        units, cur = [], []
        for i, w in enumerate(words):
            cur.append(w)
            nxt = words[i + 1] if i + 1 < len(words) else None
            if (nxt is None or len(cur) == 3 or w['w'][-1] in '.,?!' or nxt['seg'] != w['seg']
                    or not fits(cur + [nxt])):
                units.append(cur)
                cur = []
        hide = lambda w: f'{{\\alpha&HFF&}}{show(w)}{{\\alpha&H00&}}'  # noqa: E731
        boxed = lambda w: (f'{{\\bord16\\3c{fill}\\3a&H00&\\c{ink}}}{show(w)}'  # noqa: E731
                           f'{{\\bord0\\c{white}}}')
        for ui, u in enumerate(units):
            ustart = u[0]['s'] - 0.03
            uend = units[ui + 1][0]['s'] - 0.03 if ui + 1 < len(units) else u[-1]['e'] + 0.45
            uend = max(uend, ustart + 0.3)
            for j, w in enumerate(u):
                a = ustart if j == 0 else w['s'] - 0.02
                bb = u[j + 1]['s'] - 0.02 if j + 1 < len(u) else uend
                if bb <= a:
                    continue
                plain = ' '.join(show(x) if k <= j else hide(x) for k, x in enumerate(u))
                body = ' '.join(boxed(x) if k == j else colour(x) if k < j else hide(x) for k, x in enumerate(u))
                pop = (f'\\fs{big}\\fscx72\\fscy72\\t(0,90,\\fscx106\\fscy106)\\t(90,180,\\fscx100\\fscy100)'
                       if j == 0 else f'\\fs{big}')
                emit(a, bb, W // 2, base, plain, body, pop)
        lines = units
    else:
        lines = lines_of(words, fits_at(size))
        rise = size + 24
        clip = f'\\clip(0,{base - size - 40},{W},{base + 14})'
        for li, ln in enumerate(lines):
            start = ln[0]['s'] - 0.04
            end = ln[-1]['e'] + 0.35
            nxt_start = lines[li + 1][0]['s'] - 0.04 if li + 1 < len(lines) else None
            if nxt_start is not None:
                end = min(end, nxt_start)
            end = max(end, start + 0.35)
            plain = ' '.join(show(w) for w in ln)
            if style == 'karaoke':
                # the whole line fades in; the word being spoken lights up in the accent colour
                for wi, w in enumerate(ln):
                    a = start if wi == 0 else w['s']
                    b = ln[wi + 1]['s'] if wi + 1 < len(ln) else end
                    if b <= a:
                        continue
                    body = ' '.join(colour(x, on=(k == wi)) for k, x in enumerate(ln))
                    emit(a, b, W // 2, base, plain, body, '\\fad(90,0)' if wi == 0 else '')
                continue

            def body_at(a, b):
                # each word sits dim until it is spoken, then lights up to full (its accent colour if it has one)
                parts = []
                for w in ln:
                    lit = w['s'] - 0.02
                    if lit <= a:
                        tag = '\\1a&H00&'
                    elif lit >= b:
                        tag = '\\1a&H55&'
                    else:
                        t1 = int((lit - a) * 1000)
                        tag = f'\\1a&H55&\\t({t1},{t1 + 110},\\1a&H00&)'
                    parts.append(f'{{{tag}}}{colour(w)}')
                return ' '.join(parts)
            steps = [(start + k / FPS, start + (k + 1) / FPS, base + rise * (1 - k / REVEAL_FRAMES) ** 4)
                     for k in range(REVEAL_FRAMES)]
            steps = [x for x in steps if x[0] < end] + [(start + REVEAL_FRAMES / FPS, end, base)]
            for si, (a, bb, y) in enumerate(steps):
                a = min(a, end)
                if bb > a:
                    out_fade = ('\\fad(0,140)' if si == len(steps) - 1 and (nxt_start is None or nxt_start - end > 0.2)
                                else '')
                    emit(a, bb, W // 2, y, plain, body_at(a, bb), out_fade, clip)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{family},{size},{white},{white},&H00000000&,&H00000000&,0,0,0,0,100,100,1,0,1,0,0,2,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    out_ass.write_text(head + '\n'.join(ev) + '\n')
    json.dump([{'text': ' '.join(w['w'] for w in ln), 'start': round(ln[0]['s'], 2), 'end': round(ln[-1]['e'], 2)}
               for ln in lines], open(str(out_ass) + '.lines.json', 'w'), indent=1)
    widest = max(lines, key=lambda ln: len(' '.join(w['w'] for w in ln)))
    print(f'{len(lines)} caption units ({family}, style {style}) → {out_ass}\n   widest: "{" ".join(w["w"] for w in widest)}"')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        die(__doc__)
    main(*sys.argv[1:])
