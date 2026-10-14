#!/usr/bin/env python3
"""Word-timed captions for an edit plan: the speaker's real words, line by line, rising into place.

usage: captions.py <edit-plan.json> [out.ass]       (default: next to the plan, captions.ass)

Styles (my-studio/brand.json → captions.style): "rise" (each line rises into place), "karaoke" (the whole line, with
the spoken word lit in the accent colour), "pop" (1-3 big words at a time, popping in).
Timing comes from the source transcript's word timestamps mapped onto the cut's clock (each segment's words,
offset by where that segment sits in the cut). Style comes from my-studio/brand.json: caption font, text colour,
accent colour on the plan's "accents" phrases, soft shadow (never a hard outline). verify.py re-transcribes the
render afterwards and flags drift.
"""
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


def lines_of(words):
    lines, cur = [], []
    txt = lambda ln: ' '.join(x['w'] for x in ln)  # noqa: E731
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (nxt is None or nxt['seg'] != w['seg'] or w['w'][-1] in '.?!'
                or len(txt(cur)) + 1 + len(nxt['w']) > MAX_CHARS):
            lines.append(cur)
            cur = []
    for i in range(len(lines) - 1):       # never end a line on a weak word mid-thought
        while (len(lines[i]) > 1 and norm(lines[i][-1]['w']) in WEAK and lines[i][-1]['w'][-1] not in '.,?!'
               and lines[i + 1][0]['seg'] == lines[i][-1]['seg']):
            lines[i + 1].insert(0, lines[i].pop())
    out = []                               # fold a lone short word into its neighbour
    for ln in lines:
        if (out and len(ln) == 1 and len(ln[0]['w']) <= 7 and out[-1][-1]['seg'] == ln[0]['seg']
                and len(txt(out[-1])) + 1 + len(ln[0]['w']) <= MAX_CHARS + 3):
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
    style = cap.get('style', 'rise')
    show = lambda w: w['w'].upper() if upper else w['w']  # noqa: E731
    shadow = '\\blur8\\1c&H000000&\\1a&H70&'
    ev = []

    def emit(a, b, x, y, plain, body, extra='', clip_=''):
        ev.append(f'Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({x},{y + 6:.0f}){clip_}{shadow}{extra}}}{plain}')
        ev.append(f'Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({x},{y:.0f}){clip_}{extra}}}{body}')

    def colour(w, on=False):
        return f'{{\\c{gold}}}{show(w)}{{\\c{white}}}' if (w['gold'] or on) else show(w)

    if style == 'pop':
        # 1-3 words at a time, bigger, popping in from 70% scale over 120 ms
        units, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) == 3 or w['w'][-1] in '.,?!' or (len(cur) == 2 and len(' '.join(x['w'] for x in cur)) > 12):
                units.append(cur)
                cur = []
        if cur:
            units.append(cur)
        big = int(size * 1.2)
        for ui, u in enumerate(units):
            a = u[0]['s'] - 0.03
            b = units[ui + 1][0]['s'] - 0.03 if ui + 1 < len(units) else u[-1]['e'] + 0.4
            b = max(b, a + 0.25)
            pop = f'\\fs{big}\\fscx70\\fscy70\\t(0,120,\\fscx100\\fscy100)'
            emit(a, b, W // 2, base, ' '.join(show(w) for w in u), ' '.join(colour(w) for w in u), pop)
        lines = units
    else:
        lines = lines_of(words)
        rise = size + 24
        clip = f'\\clip(0,{base - size - 40},{W},{base + 14})'
        for li, ln in enumerate(lines):
            start = ln[0]['s'] - 0.04
            end = ln[-1]['e'] + 0.35
            if li + 1 < len(lines):
                end = min(end, lines[li + 1][0]['s'] - 0.04)
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
            body = ' '.join(colour(w) for w in ln)
            steps = [(start + k / FPS, start + (k + 1) / FPS, base + rise * (1 - k / REVEAL_FRAMES) ** 4)
                     for k in range(REVEAL_FRAMES)]
            steps = [x for x in steps if x[0] < end] + [(start + REVEAL_FRAMES / FPS, end, base)]
            for a, bb, y in steps:
                a = min(a, end)
                if bb > a:
                    emit(a, bb, W // 2, y, plain, body, '', clip)
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
