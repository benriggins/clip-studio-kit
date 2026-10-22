#!/usr/bin/env python3
"""Carousel Studio: brand-driven carousels (Instagram 4:5, LinkedIn documents, 1:1, 9:16) from a carousel.json.

    tools/carousel.py list                              the slide recipes and their fields
    tools/carousel.py new <project> <slug> [--format 4:5]   a starter carousel.json + images/ folder
    tools/carousel.py grab <project> <take> <time> <slug> <name>   a still from your own footage -> images/<name>.jpg
    tools/carousel.py shotlist <project>/<slug>         the Image Shot List for every slide that needs an image
    tools/carousel.py build <project>/<slug>            out/01.jpg … + carousel.pdf + contact-sheet.jpg + QA.md + ALT.md
    tools/carousel.py generate <project>/<slug>         make missing images from each slide's shot prompt (GPT Image 2.5, kie.ai)
    tools/carousel.py motion <project>/<slug>           every slide as a 4:5 video (photo push-in, type cascade): a video carousel
    tools/carousel.py reel <project>/<slug> [--music f]  the slides as one 9:16 Reel for the Reels tab / For You feed

Everything reads brand.json (colours, fonts, logo) so every brand looks like itself. Slides are HTML shot with
headless Chrome; no paid service. Copy uses *asterisks* for the one emphasis word (italic, accent colour) and \\n for
a line break. Same spirit as the video tools: real words only, nothing invented.
"""
import argparse, html, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

from PIL import Image, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, CANVAS, brand, die, ffmpeg, slug as slugify  # noqa: E402

RECIPES = {
    'cover': 'eyebrow, headline, sub, [image, pos]  . The hook. Type-only, or full-bleed photo with the type over it.',
    'statement': 'eyebrow, headline, text  . One claim and its reason.',
    'quote': 'quote, by, source  . A line worth keeping, verbatim, with where it came from.',
    'list': 'eyebrow, title, items[2-5]  . Numbered rows.',
    'compare': 'title, left{label,text}, right{label,text}  . Don\'t / Do, before / after.',
    'steps': 'eyebrow, title, steps[{t,d}] (2-5)  . An ordered process on a rail.',
    'stat': 'eyebrow, number, unit, text, note  . One number that matters, labelled honestly.',
    'photo': 'headline, kicker, lede, position top|bottom, image, pos  . A full-bleed photo carries the slide.',
    'paper': 'eyebrow, title, rows[{k,v}], close, [image]  . A paper card (worksheet / save-this) on a blurred photo.',
    'cta': 'headline, action, url, logo  . The one last action.',
    'bigword': 'kicker, word, line, sub, image, pos, [timecode, bars]  . CINEMATIC COVER: a giant serif word BEHIND the subject (auto cut-out), small heavy line above, serif line below.',
    'slate': 'image, pos, timecode, kicker, number, line, [scrub]  . Film still: letterbox bars, REC timecode, one giant accent number, an over-run video scrubber.',
    'callout': 'image, pos, kicker, headline, sub, note, at{x,y}  . Field note: a thin leader line from a detail in the photo to a two-line serif note.',
    'monument': 'image, pos, number, horizon, kicker, headline, lede  . A huge outlined number standing behind the horizon line of the photo.',
    'scoreboard': 'image, pos, kicker, headline, cells[{label,value,sub,on}], note  . A two-cell HUD over the photo (work block / reward, before / after).',
    'chat': 'contact, status, messages[{who them|me, text, time}], typing, kicker, headline, sub, [image]  . OPENER: a real-looking text thread (the client waiting), headline under it.',
    'notif': 'clock, date, notes[{app, title, text, ago, icon}], kicker, headline, sub, [image]  . OPENER: a lock screen stacking up notifications.',
    'receipt': 'store, meta, rows[{k,v}], total{k,v}, foot, kicker, headline, [image]  . OPENER: a thermal receipt itemising what the problem costs.',
    'knockout': 'kicker, word, line, sub, image, pos  . OPENER: one giant word with the photo showing through the letters.',
    'split': 'image, pos, image2, pos2, label, label2, headline, sub  . OPENER: before/after diptych, the headline on a paper strip across the seam.',
    'lowerthird': 'image, pos, bug, place, timecode, headline, sub, ticker, ticker_label  . OPENER: a live-broadcast lower third with a crawling ticker.',
    'notes': 'title, date, lines ("[x] done", "[ ] todo", "- bullet", "# heading", plain; ~~strike~~ ==highlight==), dark  . FYP: a Notes-app screenshot, text-heavy, made to be read and saved.',
    'hottake': 'kicker, myth, truth, sub, [theme]  . FYP contrarian: the common belief struck through in red, your take big under it.',
    'proof': 'kicker, headline, label, value, delta, delta_bad, bars[{label,value,show,on}], source  . FYP stats & proof: an analytics card. Real numbers only; source is required.',
    'scrapbook': 'photos[{image,caption,pos}] (1-3), stamp [big, small], note, kicker, headline  . FYP tactile: taped polaroids on kraft paper, a rubber stamp, a sticky note.',
    'collage': 'bg gold|paper|royal, layers[{image (transparent PNG), x, y, w, rot, front}], kicker, headline, sub  . FYP pop-up collage: cut-out objects in front of and behind giant type.',
    'reveal': 'image, pos, kicker, question, hint  . FYP curiosity hook: the photo blurred out under a question; the next slide shows it sharp.',
    'pano': 'pano{image, index, of, y}, tag, kicker, headline, sub, position  . FYP seamless: one wide photo runs across consecutive slides, so the swipe continues the picture.',
}
GRAIN = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E"
         "%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' seed='9'/%3E%3CfeColorMatrix values='0 0 0 0 .5 "
         "0 0 0 0 .5 0 0 0 0 .5 0 0 0 .5 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")")


# ---------- colour helpers ----------
def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(c):
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    return hexc([x + (y - x) * t for x, y in zip(rgb(a), rgb(b))])


def rgba(h, a):
    r, g, b = rgb(h)
    return f'rgba({r},{g},{b},{a})'


def lum(h):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else (((v / 255) + .055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in rgb(h))
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


# ---------- brand -> tokens ----------
def tokens(b):
    c = b['colors']
    bg = c['background']
    dark_ink = c.get('ink') or mix(bg, '#000000', .55)
    t = {
        'bg': bg, 'bg_deep': mix(bg, '#000000', .35), 'surface': c.get('surface', mix(bg, '#FFFFFF', .08)),
        'text': c.get('text', '#FFFFFF'), 'muted': c.get('muted', mix(c.get('text', '#FFFFFF'), bg, .3)),
        'accent': c['accent'], 'paper': c.get('paper', '#F5F1E8'), 'ink': dark_ink,
        'accent_light': c.get('gold_text') or c.get('gold') or mix(c['accent'], '#000000', .35),
    }
    t['paper_deep'] = mix(t['paper'], '#8A7A55', .18)
    t['muted_light'] = mix(dark_ink, t['paper'], .35)
    return t


def font_css(b):
    out = []
    spec = [('BrandDisplay', 'display', 'normal'), ('BrandDisplay', 'display_italic', 'italic'),
            ('BrandBody', 'body', 'normal'), ('BrandMono', 'mono', 'normal')]
    for fam, key, style in spec:
        f = b.get('fonts', {}).get(key)
        if f and (ROOT / f['file']).exists():
            out.append(f"@font-face{{font-family:'{fam}';src:url('{(ROOT / f['file']).as_uri()}');"
                       f"font-weight:100 900;font-style:{style};}}")
    return '\n'.join(out)


def font_file(b, key='display'):
    f = b.get('fonts', {}).get(key) or {}
    p = ROOT / f.get('file', '')
    return p if p.is_file() else None


# ---------- text helpers ----------
def rich(s):
    s = html.escape(str(s), quote=False)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    return s.replace('\\n', '<br/>').replace('\n', '<br/>')


def plain(s):
    return re.sub(r'\*', '', str(s)).replace('\\n', '\n')


_fonts = {}


def text_w(path, size, s):
    if not path:
        return len(s) * size * .52
    key = (str(path), size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(str(path), size)
    return _fonts[key].getlength(s) * 1.04      # variable fonts measure at their default cut; keep a margin


def fit(text, path, width, max_h, hi, lo, lh=1.08):
    """Largest font size whose wrapped text fits width x max_h."""
    for size in range(int(hi), int(lo) - 1, -2):
        n = 0
        for para in plain(text).split('\n'):
            line, cnt = '', 1
            for w in para.split():
                trial = (line + ' ' + w).strip()
                if text_w(path, size, trial) <= width or not line:
                    line = trial
                else:
                    cnt += 1
                    line = w
            n += cnt
        if n * size * lh <= max_h:
            return size
    return int(lo)


def h(text, path, width, max_h, hi, lo, cls='h', lh=1.08, tag='h2'):
    sz = fit(text, path, width, max_h, hi, lo, lh)
    return f'<{tag} class="{cls}" data-fit="{cls}" style="font-size:{sz}px;line-height:{lh}">{rich(text)}</{tag}>'


# ---------- recipes ----------
class Ctx:
    def __init__(self, b, d, car, W, H):
        self.b, self.d, self.car, self.W, self.H = b, d, car, W, H
        self.t = tokens(b)
        self.disp = font_file(b, 'display')
        self.body = font_file(b, 'body')
        self.inner = W - 192

    def img(self, name):
        p = (self.d / name).resolve()
        if not p.exists():
            die(f'image missing: {p}. Drop it in images/ (carousel.py shotlist says what to make).')
        return p.as_uri()

    def logo(self):
        st = self.b.get('style', {}).get('backdrop', {})
        for k in ('logo_on_dark', 'logo'):
            if st.get(k) and (ROOT / st[k]).exists():
                return (ROOT / st[k]).as_uri()
        return None

    def photo(self, sl, extra=''):
        pos = sl.get('pos', 'center')
        return f'<div class="bg {extra}" style="background-image:url({self.img(sl["image"])});background-position:{pos}"></div>'


def r_cover(c, sl):
    big = h(sl['headline'], c.disp, c.inner, c.H * .5, 170, 78, 'cover', 1.02, 'h1')
    k = f'<p class="k">{rich(sl["eyebrow"])}</p>' if sl.get('eyebrow') else ''
    sub = f'<p class="sub">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    if sl.get('image'):
        return (c.photo(sl) + '<div class="tint"></div><div class="shade shade--cover"></div>'
                f'<div class="imgbot">{k}{big}{sub}</div>'), 'dark img'
    return f'<div class="pad pad--c">{k}{big}{sub}</div>', 'dark'


def r_statement(c, sl):
    k = f'<p class="k">{rich(sl["eyebrow"])}</p>' if sl.get('eyebrow') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * .5, 120, 62, 'big', 1.06)
    t = f'<p class="lede">{rich(sl["text"])}</p>' if sl.get('text') else ''
    return f'<div class="pad pad--c">{k}{big}{t}</div>', sl.get('theme', 'dark')


def r_quote(c, sl):
    q = h('“' + sl['quote'] + '”', c.disp, c.inner, c.H * .5, 92, 44, 'quote', 1.12, 'blockquote')
    by = ' · '.join(x for x in (sl.get('by'), sl.get('source')) if x)
    return (f'<div class="pad pad--c"><div class="qm">“</div>{q}<p class="by"><span class="rule"></span>{rich(by)}</p></div>',
            sl.get('theme', 'dark'))


def r_list(c, sl):
    items = sl['items']
    k = f'<p class="k">{rich(sl["eyebrow"])}</p>' if sl.get('eyebrow') else ''
    ttl = h(sl['title'], c.disp, c.inner, c.H * .22, 84, 54, 'h2m')
    room = c.H - 120 - 110 - 260
    each = room / max(len(items), 1)
    sz = fit(max(items, key=len), c.body, c.inner - 130, each - 30, 56, 30, 1.2)
    rows = ''.join(f'<li><b>{i + 1:02d}</b><span data-fit="li" style="font-size:{sz}px">{rich(x)}</span></li>'
                   for i, x in enumerate(items))
    return f'<div class="pad pad--c">{k}{ttl}<ol class="rows">{rows}</ol></div>', sl.get('theme', 'dark')


def r_compare(c, sl):
    ttl = h(sl['title'], c.disp, c.inner, 190, 72, 46, 'h2m')
    room = (c.H - 120 - 110 - 230) / 2 - 40
    out = ''
    for side, cls in (('left', 'cmp'), ('right', 'cmp cmp--on')):
        d = sl[side]
        sz = fit(d['text'], c.disp, c.inner - 110, room - 80, 60, 36, 1.12)
        out += (f'<div class="{cls}"><p class="chip">{rich(d["label"])}</p>'
                f'<p class="cmp__t" data-fit="cmp" style="font-size:{sz}px">{rich(d["text"])}</p></div>')
    return f'<div class="pad">{ttl}<div class="cmps">{out}</div></div>', sl.get('theme', 'dark')


def r_steps(c, sl):
    steps = sl['steps']
    k = f'<p class="k">{rich(sl["eyebrow"])}</p>' if sl.get('eyebrow') else ''
    ttl = h(sl['title'], c.disp, c.inner, c.H * .2, 80, 52, 'h2m')
    room = (c.H - 120 - 110 - 250) / max(len(steps), 1)
    ts = fit(max((s['t'] for s in steps), key=len), c.disp, c.inner - 150, room * .5, 76, 38, 1.05)
    ds = min(40, max(26, int(room * .22)))
    rows = ''.join(f'<div class="st"><span class="dia"></span><div><p class="st__t" data-fit="st" style="font-size:{ts}px">{rich(s["t"])}</p>'
                   f'<p class="st__d" style="font-size:{ds}px">{rich(s.get("d", ""))}</p></div></div>' for s in steps)
    return f'<div class="pad pad--c">{k}{ttl}<div class="rail">{rows}</div></div>', sl.get('theme', 'dark')


def r_stat(c, sl):
    k = f'<p class="k">{rich(sl["eyebrow"])}</p>' if sl.get('eyebrow') else ''
    n = str(sl['number'])
    sz = fit(n, c.disp, c.inner, 520, 520, 200, .9)
    unit = f'<p class="unit">{rich(sl["unit"])}</p>' if sl.get('unit') else ''
    t = f'<p class="lede">{rich(sl["text"])}</p>' if sl.get('text') else ''
    note = f'<p class="note">{rich(sl["note"])}</p>' if sl.get('note') else ''
    pre = f'<p class="pre">{rich(sl["pre"])}</p>' if sl.get('pre') else ''
    return (f'<div class="pad pad--c">{k}{pre}<p class="num" data-fit="num" style="font-size:{sz}px">{html.escape(n)}</p>{unit}{t}{note}</div>',
            sl.get('theme', 'dark'))


def r_photo(c, sl):
    pos = sl.get('position', 'bottom')
    k = f'<p class="k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * .34, 118, 60, 'big', 1.04)
    lede = f'<p class="lede lede--s">{rich(sl["lede"])}</p>' if sl.get('lede') else ''
    cls = 'imgtop' if pos == 'top' else 'imgbot'
    return (c.photo(sl) + '<div class="tint"></div>' + f'<div class="shade shade--{pos}"></div>'
            f'<div class="{cls}">{k}{big}{lede}</div>'), 'dark img'


def r_paper(c, sl):
    k = f'<p class="k k--ink">{rich(sl["eyebrow"])}</p>' if sl.get('eyebrow') else ''
    ttl = h(sl['title'], c.disp, c.inner - 100, 170, 62, 40, 'h2ink')
    rows = ''.join(f'<div class="sheet__r"><b>{rich(r["k"])}</b><span>{rich(r["v"])}</span><i></i></div>' for r in sl['rows'])
    close = f'<p class="close">{rich(sl["close"])}</p>' if sl.get('close') else ''
    bg = (c.photo(sl, 'bg--blur') if sl.get('image') else '') + '<div class="shade shade--desk"></div>'
    return bg + f'<div class="pad pad--c"><div class="sheet">{k}{ttl}{rows}</div>{close}</div>', 'dark img'


def r_cta(c, sl):
    big = h(sl['headline'], c.disp, c.inner, c.H * .34, 130, 66, 'big', 1.04)
    act = f'<p class="btn">{rich(sl["action"])}<span>→</span></p>' if sl.get('action') else ''
    url = f'<p class="url">{html.escape(sl["url"])}</p>' if sl.get('url') else ''
    lg = c.logo()
    logo = f'<img class="logo" src="{lg}"/>' if sl.get('logo', True) and lg else ''
    return f'<div class="pad pad--c">{big}{act}{url}</div>{logo}', 'dark'



def cut_png(c, sl):
    """Subject cut-out for word-behind-the-subject (Apple Vision, macOS). Cached as images/<name>-cut.png."""
    src = (c.d / sl['image']).resolve()
    out = src.with_name(src.stem + '-cut.png')
    if not out.exists():
        r = subprocess.run(['uv', 'run', '-q', '--with', 'pyobjc-framework-Vision', '--with', 'pyobjc-framework-Quartz', 'python',
                            str(Path(__file__).parent / 'cutout.py'), str(src), str(out)], capture_output=True, text=True)
        if r.returncode:
            print(f'  · cut-out failed ({r.stderr.strip()[-120:]}); the word will sit in front instead')
            return None
    return out.as_uri()


def tc(sl):
    return f'<p class="tc"><span class="rec"></span>{html.escape(sl["timecode"])}</p>' if sl.get('timecode') else ''


def r_bigword(c, sl):
    pos = sl.get('pos', 'center 55%')
    cut = cut_png(c, sl) if sl.get('image') else None
    word = html.escape(sl['word'])
    size = min(400, int(c.W * 1.55 / max(3, len(sl['word']))))
    layer = f'<div class="cut" style="background-image:url({cut});background-position:{pos}"></div>' if cut else ''
    k = f'<p class="bw__a">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    line = f'<p class="bw__c">{rich(sl["line"])}</p>' if sl.get('line') else ''
    sub = f'<p class="bw__s">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    bars = '<div class="bars"></div>' if sl.get('bars', True) else ''
    return (c.photo(sl) + '<div class="tint"></div><div class="shade shade--bw"></div>'
            f'<div class="bw" style="top:{sl.get("word_top", int(c.H * .28))}px">{k}<p class="bw__big" style="font-size:{size}px">{word}</p></div>'
            f'{layer}<div class="slate__tc">{tc(sl)}</div><div class="bw__b">{line}{sub}</div>{bars}'), 'dark img'


def r_slate(c, sl):
    scrub = ''
    if sl.get('scrub', True):
        scrub = (f'<div class="scrub"><span class="scrub__play">▶</span><div class="scrub__bar"><i></i><b></b></div>'
                 f'<span class="scrub__t">{html.escape(sl.get("scrub_label", ""))}</span></div>')
    k = f'<p class="sl__a">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    num = f'<p class="sl__big">{rich(sl["number"])}</p>' if sl.get('number') else ''
    line = f'<p class="sl__c">{rich(sl["line"])}</p>' if sl.get('line') else ''
    return (c.photo(sl) + '<div class="tint"></div><div class="shade shade--bottom"></div>'
            f'<div class="slate__tc">{tc(sl)}</div><div class="imgbot">{k}{num}{line}{scrub}</div><div class="bars"></div>'), 'dark img'


def r_callout(c, sl):
    at = sl.get('at', {'x': 400, 'y': 900})
    k = f'<p class="k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * .22, 112, 60, 'big', 1.02)
    sub = f'<h2 class="co__s">{rich(sl["sub"])}</h2>' if sl.get('sub') else ''
    note = (f'<div class="callout" style="left:{at["x"]}px;top:{at["y"]}px"><svg viewBox="0 0 420 150" width="420">'
            '<circle cx="18" cy="132" r="7" fill="none" stroke="#fff" stroke-width="2.5"/>'
            f'<path d="M28,124 L150,30 L410,30" fill="none" stroke="#fff" stroke-width="2"/></svg><p>{rich(sl.get("note", ""))}</p></div>')
    return (c.photo(sl) + '<div class="tint"></div><div class="shade shade--top"></div>'
            f'<div class="imgtop">{k}{big}{sub}</div>{note}'), 'dark img'


def r_monument(c, sl):
    hz = int(sl.get('horizon', c.H * .62))
    k = f'<p class="k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * .2, 80, 52, 'big', 1.06) if sl.get('headline') else ''
    lede = f'<p class="lede lede--s">{rich(sl["lede"])}</p>' if sl.get('lede') else ''
    return (c.photo(sl) + '<div class="shade shade--bottom"></div>'
            f'<div class="mon" style="height:{hz}px"><span>{html.escape(str(sl["number"]))}</span></div>'
            f'<div class="imgtop">{k}</div><div class="imgbot">{big}{lede}</div>'), 'dark img'


def r_scoreboard(c, sl):
    k = f'<p class="k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * .2, 80, 52, 'big', 1.06) if sl.get('headline') else ''
    cells = ''.join(f'<div class="board__c{" board__c--on" if x.get("on") else ""}"><span class="board__l">{rich(x["label"])}</span>'
                    f'<b>{html.escape(str(x["value"]))}</b><span class="board__s">{rich(x.get("sub", ""))}</span></div>' for x in sl['cells'])
    note = f'<p class="note">{rich(sl["note"])}</p>' if sl.get('note') else ''
    return (c.photo(sl) + '<div class="tint"></div><div class="shade shade--bottom"></div>'
            f'<div class="imgbot">{k}{big}<div class="board">{cells}</div>{note}</div>'), 'dark img'


def heading(c, sl, hi=96, lo=54, room=.2):
    k = f'<p class="k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * room, hi, lo, 'big', 1.04) if sl.get('headline') else ''
    sub = f'<p class="note">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    return k + big + sub


def backdrop(c, sl, blur=True):
    if not sl.get('image'):
        return '<div class="shade shade--desk"></div>'
    return c.photo(sl, 'bg--blur' if blur else '') + '<div class="tint"></div><div class="shade shade--desk"></div>'


def r_chat(c, sl):
    who = sl.get('contact', 'Client')
    head = (f'<div class="ch__h"><span class="ch__av">{html.escape(who[:1])}</span><b>{html.escape(who)}</b>'
            f'<span>{html.escape(sl.get("status", "iMessage"))}</span></div>')
    msgs = ''.join(f'<div class="msg msg--{m.get("who", "them")}"><p>{rich(m["text"])}</p>'
                   f'{"<span>" + html.escape(m["time"]) + "</span>" if m.get("time") else ""}</div>' for m in sl['messages'])
    if sl.get('typing'):
        msgs += '<div class="msg msg--them msg--typing"><p><i></i><i></i><i></i></p></div>'
    return backdrop(c, sl) + f'<div class="chat">{head}{msgs}</div><div class="imgbot">{heading(c, sl)}</div>', 'dark img'


def r_notif(c, sl):
    cards = ''.join(f'<div class="ntf"><span class="ntf__i">{html.escape(n.get("icon", n["app"][:1]))}</span><div><p class="ntf__a">'
                    f'{html.escape(n["app"])}<span>{html.escape(n.get("ago", "now"))}</span></p><p class="ntf__t">{rich(n["title"])}</p>'
                    f'<p class="ntf__x">{rich(n.get("text", ""))}</p></div></div>' for n in sl['notes'])
    clock = (f'<div class="lock"><p class="lock__d">{html.escape(sl.get("date", "Tuesday, October 21"))}</p>'
             f'<p class="lock__t">{html.escape(sl.get("clock", "4:52"))}</p></div>')
    return backdrop(c, sl) + f'{clock}<div class="ntfs">{cards}</div><div class="imgbot">{heading(c, sl, 80, 48, .14)}</div>', 'dark img'


def r_receipt(c, sl):
    rows = ''.join(f'<p class="rc__r"><span>{rich(r["k"])}</span><b>{html.escape(str(r["v"]))}</b></p>' for r in sl['rows'])
    tot = sl.get('total') or {}
    total = f'<p class="rc__r rc__tot"><span>{rich(tot.get("k", "Total"))}</span><b>{html.escape(str(tot.get("v", "")))}</b></p>' if tot else ''
    rc = (f'<div class="rc"><p class="rc__s">{rich(sl.get("store", ""))}</p><p class="rc__m">{html.escape(sl.get("meta", ""))}</p>'
          f'<p class="rc__d"></p>{rows}<p class="rc__d"></p>{total}<p class="rc__f">{rich(sl.get("foot", ""))}</p></div>')
    return backdrop(c, sl) + f'<div class="imgtop">{heading(c, sl, 92, 54, .16)}</div>{rc}', 'dark img'


def r_knockout(c, sl):
    word = sl['word']
    size = min(560, int(c.W * 1.62 / max(2, len(word))))
    k = f'<p class="ko__k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    line = f'<p class="ko__l">{rich(sl["line"])}</p>' if sl.get('line') else ''
    sub = f'<p class="sub">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    img = c.img(sl['image'])
    return (f'<div class="pad pad--c ko">{k}<p class="ko__w" style="font-size:{size}px;background-image:url({img});'
            f'background-position:{sl.get("pos", "center")}">{html.escape(word)}</p>{line}{sub}</div>'), 'dark'


def r_split(c, sl):
    top = f'<div class="sp sp--a" style="background-image:url({c.img(sl["image"])});background-position:{sl.get("pos", "center")}"></div>'
    if sl.get('image2'):
        bot = (f'<div class="sp sp--b" style="background-image:url({c.img(sl["image2"])});'
               f'background-position:{sl.get("pos2", "center")}"></div>')
    else:
        bot = '<div class="sp sp--b sp--ink"></div>'
    lab = ''.join(f'<p class="sp__l sp__l--{i}">{html.escape(sl[k])}</p>' for i, k in (('a', 'label'), ('b', 'label2')) if sl.get(k))
    big = h(sl['headline'], c.disp, c.inner - 80, 260, 104, 56, 'big', 1.02)
    sub = f'<p class="sp__s">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    return top + bot + lab + f'<div class="sp__seam">{big}</div>{sub}', 'dark img'


def r_lowerthird(c, sl):
    tick = ''
    if sl.get('ticker'):
        t = html.escape(sl['ticker'])
        tick = f'<div class="lt__tk"><b>{html.escape(sl.get("ticker_label", "Update"))}</b><span>{t} &nbsp;•&nbsp; {t} &nbsp;•&nbsp; {t}</span></div>'
    bug = f'<p class="lt__bug"><span class="rec"></span>{html.escape(sl.get("bug", "Live"))}<i>{html.escape(sl.get("place", ""))}</i></p>'
    big = h(sl['headline'], c.body, c.inner - 190, 220, 70, 44, 'lt__h', 1.05, 'p')   # measured at regular, set at 800
    sub = f'<p class="lt__s">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    return (c.photo(sl) + '<div class="shade shade--bottom"></div>'
            f'<div class="slate__tc">{tc(sl)}</div><div class="lt">{bug}<div class="lt__p">{big}</div>{sub}</div>{tick}'), 'dark img'


# ---------- FYP / Explore aesthetics ----------
def nrich(s):
    s = rich(s)
    s = re.sub(r'~~(.+?)~~', r'<s>\1</s>', s)
    return re.sub(r'==(.+?)==', r'<mark>\1</mark>', s)


def r_notes(c, sl):
    rows = ''
    for ln in sl['lines']:
        if ln.startswith(('[x] ', '[ ] ')):
            on = ln.startswith('[x]')
            rows += f'<p class="nt__l nt__ck{" nt__ck--on" if on else ""}"><i></i><span>{nrich(ln[4:])}</span></p>'
        elif ln.startswith('- '):
            rows += f'<p class="nt__l nt__b"><span>{nrich(ln[2:])}</span></p>'
        elif ln.startswith('# '):
            rows += f'<p class="nt__l nt__h">{nrich(ln[2:])}</p>'
        else:
            rows += f'<p class="nt__l">{nrich(ln)}</p>'
    dark = sl.get('dark')
    return (f'<div class="nt{" nt--dark" if dark else ""}"><div class="nt__bar"><span>‹ Notes</span><span>⌁ &nbsp;⋯</span></div>'
            f'<p class="nt__date">{html.escape(sl.get("date", "October 22, 2026 at 9:41 AM"))}</p>'
            f'<p class="nt__title">{nrich(sl["title"])}</p>{rows}</div>'), ('dark img' if dark else 'light img')


def r_hottake(c, sl):
    k = f'<p class="ht__k">{rich(sl.get("kicker", "Unpopular opinion"))}</p>'
    myth = f'<p class="ht__m">{rich(sl["myth"])}</p>'
    truth = h(sl['truth'], c.disp, c.inner, c.H * .36, 130, 64, 'ht__t big', 1.02)
    sub = f'<p class="sub">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    return f'<div class="pad pad--c">{k}{myth}{truth}{sub}</div>', sl.get('theme', 'light')


def r_proof(c, sl):
    bars = sl.get('bars', [])
    top = max((float(b['value']) for b in bars), default=1) or 1
    cols = ''.join(f'<div class="pf__bar{" pf__bar--on" if b.get("on") else ""}"><b>{html.escape(str(b.get("show", b["value"])))}</b>'
                   f'<i style="height:{max(4, float(b["value"]) / top * 100):.1f}%"></i><span>{html.escape(b["label"])}</span></div>' for b in bars)
    delta = sl.get('delta')
    pill = f'<span class="pf__d{" pf__d--bad" if sl.get("delta_bad") else ""}">{html.escape(delta)}</span>' if delta else ''
    card = (f'<div class="pf__card"><p class="pf__lab">{html.escape(sl.get("label", ""))}{pill}</p>'
            f'<p class="pf__v">{html.escape(str(sl.get("value", "")))}</p><div class="pf__chart">{cols}</div>'
            f'<p class="pf__src">{rich(sl.get("source", ""))}</p></div>')
    return f'<div class="pad pad--c">{heading(c, sl, 84, 50, .18)}{card}</div>', sl.get('theme', 'dark')


SB_SPOTS = {1: [(12, 7, 780, -3)], 2: [(6, 7, 560, -6), (44, 19, 520, 5)], 3: [(3, 13, 440, -8), (31, 21, 440, 3), (56, 11, 430, 8)]}


def r_scrapbook(c, sl):
    photos = sl.get('photos', [])[:3]
    pols = ''
    for n, ((x, y, w, rot), p) in enumerate(zip(SB_SPOTS.get(len(photos), []), photos)):
        cap = f'<p>{rich(p["caption"])}</p>' if p.get('caption') else ''
        pols += (f'<div class="pol" style="left:{x}%;top:{y}%;width:{w}px;transform:rotate({rot}deg);z-index:{5 - n}"><span class="tape"></span>'
                 f'<div class="pol__i" style="background-image:url({c.img(p["image"])});background-position:{p.get("pos", "center")}"></div>{cap}</div>')
    st = sl.get('stamp')
    stamp = ''
    if st:
        a, b = (st if isinstance(st, list) else [st, ''])[:2]
        stamp = f'<div class="sb__stamp"><b>{html.escape(a)}</b><span>{html.escape(b)}</span></div>'
    note = f'<div class="sb__note">{rich(sl["note"])}</div>' if sl.get('note') else ''
    k = f'<p class="sb__k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner - (330 if note else 0), c.H * .2, 104, 56, 'big', 1.02)
    return (f'<div class="sb"></div>{pols}{stamp}{note}<div class="sb__t{" sb__t--n" if note else ""}">{k}{big}</div>'), 'light'


def r_collage(c, sl):
    lay = ''
    for L in sl.get('layers', []):
        z = 5 if L.get('front') else 2
        lay += (f'<img class="cl__l" src="{c.img(L["image"])}" style="left:{L.get("x", 0)}px;top:{L.get("y", 0)}px;width:{L.get("w", 420)}px;'
                f'transform:rotate({L.get("rot", 0)}deg);z-index:{z}"/>')
    k = f'<p class="cl__k">{rich(sl["kicker"])}</p>' if sl.get('kicker') else ''
    big = h(sl['headline'], c.disp, c.inner, c.H * .4, 170, 80, 'cl__h', .96, 'h1')
    sub = f'<p class="sub">{rich(sl["sub"])}</p>' if sl.get('sub') else ''
    bg = sl.get('bg', 'gold')
    return f'<div class="cl cl--{bg}"></div>{lay}<div class="cl__t">{k}{big}{sub}</div>', ('dark img' if bg == 'royal' else 'light img')


def r_reveal(c, sl):
    q = h(sl['question'], c.disp, c.inner - 120, c.H * .3, 110, 56, 'big', 1.02)
    return (c.photo(sl, 'bg--blur bg--reveal') + '<div class="tint"></div>'
            f'<div class="rv"><p class="rv__k">{rich(sl.get("kicker", "Guess"))}</p>{q}'
            f'<p class="rv__h">{rich(sl.get("hint", "Swipe to see"))}<span>→</span></p></div>'), 'dark img'


def pano_layer(c, sl):
    from PIL import Image as _I
    p = sl['pano']
    src = (c.d / p['image']).resolve()
    if not src.exists():
        die(f'image missing: {src}')
    iw, ih = _I.open(src).size
    of, ix = int(p.get('of', 2)), int(p.get('index', 0))
    k = max(of * c.W / iw, c.H / ih)
    bw, bh = iw * k, ih * k
    x = -(ix * c.W) - (bw - of * c.W) / 2
    y = -(bh - c.H) * float(p.get('y', .5))
    return (f'<div class="bg" style="background-image:url({src.as_uri()});background-size:{bw:.0f}px {bh:.0f}px;'
            f'background-position:{x:.0f}px {y:.0f}px"></div>')


def r_pano(c, sl):
    pos = sl.get('position', 'bottom')
    tag = f'<p class="pn__tag pn__tag--{pos}">{html.escape(sl["tag"])}</p>' if sl.get('tag') else ''
    cls = 'imgtop' if pos == 'top' else 'imgbot'
    return (pano_layer(c, sl) + f'<div class="shade shade--{pos}"></div>{tag}'
            f'<div class="{cls}">{heading(c, sl, 100, 54, .26)}</div>'), 'dark img'


FYP_CSS = """
.s--light.s--img .top,.s--light.s--img .foot { color:rgba(0,0,0,.42); } .s--light.s--img .fr { border-color:rgba(0,0,0,.08); }
.nt { position:absolute; inset:0; z-index:1; background:#fff; color:#1c1c1e; padding:150px 80px 0; font-family:system-ui,-apple-system,sans-serif; }
.nt--dark { background:#1c1c1e; color:#f2f2f7; } .nt ~ .grain, .nt ~ .fr, .nt ~ .top { display:none; }
.nt__bar { position:absolute; left:56px; right:56px; top:96px; display:flex; justify-content:space-between; font:500 36px/1 system-ui; color:#e0a100; }
.nt__date { margin:60px 0 0; text-align:center; font:400 28px/1 system-ui; color:#8e8e93; }
.nt__title { margin:44px 0 34px; font:700 84px/1.08 system-ui; letter-spacing:-.01em; }
.nt__l { margin:0 0 26px; font:400 50px/1.3 system-ui; } .nt__h { font-weight:700; font-size:58px; margin-top:52px; }
.nt__b { display:flex; gap:22px; } .nt__b::before { content:"•"; color:#8e8e93; }
.nt__ck { display:flex; gap:24px; align-items:flex-start; } .nt__ck i { flex:none; width:48px; height:48px; margin-top:9px; border-radius:50%; border:2.5px solid #c7c7cc; }
.nt__ck--on i { border-color:#e0a100; background:#e0a100 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M6 12.5l4 4 8-9' fill='none' stroke='white' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E") center/70% no-repeat; }
.nt__ck--on span { color:#8e8e93; }
.nt mark { background:linear-gradient(180deg,transparent 12%,#ffe066 12%,#ffe066 88%,transparent 88%); color:inherit; padding:0 4px; }
.nt--dark mark { background:linear-gradient(180deg,transparent 12%,#8a6d00 12%,#8a6d00 88%,transparent 88%); }
.nt s { text-decoration-color:#e5484d; text-decoration-thickness:4px; color:#8e8e93; } .nt em { font-style:normal; font-weight:700; color:inherit; }
.s--light .pad .big, .s--light .pad .cover { color:var(--ink); }
.ht__k { align-self:flex-start; margin:0 0 54px; padding:14px 24px; border-radius:999px; background:var(--ink); color:#fff; font:700 24px/1 var(--sans); letter-spacing:.16em; text-transform:uppercase; }
.ht__m { margin:0 0 40px; font:500 64px/1.12 var(--serif); letter-spacing:-.02em; color:var(--mut); text-decoration:line-through; text-decoration-color:#d2442f; text-decoration-thickness:10px; text-decoration-skip-ink:none; }
.s--dark .ht__k { background:var(--ac); color:var(--bgd); }
.pf__card { margin-top:46px; padding:40px 44px 32px; border-radius:30px; background:#fff; color:#151018; box-shadow:0 40px 90px rgba(0,0,0,.45); font-family:var(--sans); }
.pf__lab { margin:0; display:flex; justify-content:space-between; align-items:center; font:600 26px/1 var(--sans); color:#6e6878; }
.pf__d { padding:10px 18px; border-radius:999px; background:#e3f5e8; color:#177a3c; font:700 24px/1 var(--sans); }
.pf__d--bad { background:#fde8e6; color:#b42318; }
.pf__v { margin:14px 0 0; font:800 132px/1 var(--sans); letter-spacing:-.04em; font-variant-numeric:tabular-nums; }
.pf__chart { display:flex; align-items:flex-end; gap:22px; height:360px; margin-top:34px; padding-top:44px; border-bottom:2px solid #e7e3ee; }
.pf__bar { flex:1; height:100%; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; position:relative; }
.pf__bar i { display:block; width:100%; border-radius:12px 12px 0 0; background:#d9d3e4; } .pf__bar--on i { background:var(--ac); }
.pf__bar b { font:700 26px/1 var(--sans); margin-bottom:12px; color:#3c3546; } .pf__bar--on b { color:#151018; }
.pf__bar span { position:absolute; bottom:-46px; font:600 22px/1 var(--sans); color:#6e6878; white-space:nowrap; }
.pf__src { margin:68px 0 0; font:500 20px/1.3 var(--mono); letter-spacing:.06em; color:#8a8494; }
.sb { position:absolute; inset:0; z-index:0; background:radial-gradient(60% 40% at 30% 20%, rgba(255,255,255,.35), transparent 70%),
  repeating-linear-gradient(93deg, rgba(120,90,50,.035) 0 2px, transparent 2px 7px), linear-gradient(170deg,#e8dcc4,#d9c8a6); }
.pol { position:absolute; z-index:2; padding:20px 20px 0; background:#fbfaf6; box-shadow:0 26px 50px rgba(60,40,10,.35), 0 2px 4px rgba(0,0,0,.15); }
.pol__i { width:100%; aspect-ratio:1; background-size:cover; filter:saturate(.85) contrast(1.05) sepia(.08); }
.pol p { margin:0; padding:16px 6px 22px; font:italic 400 36px/1.1 var(--serif); color:#2a2420; text-align:center; } .pol p em { color:#b23a2e; }
.pol:not(:has(p)) { padding-bottom:64px; }
.tape { position:absolute; left:50%; top:-26px; width:190px; height:54px; margin-left:-95px; transform:rotate(-4deg); z-index:3;
  background:rgba(236,226,196,.82); box-shadow:0 2px 6px rgba(0,0,0,.12); clip-path:polygon(3% 0,97% 4%,100% 100%,0 96%); }
.sb__stamp { position:absolute; right:84px; top:55%; z-index:6; width:250px; height:250px; border-radius:50%; border:7px solid #b23a2e;
  box-shadow:inset 0 0 0 9px rgba(0,0,0,0), inset 0 0 0 12px #b23a2e; display:flex; flex-direction:column; align-items:center; justify-content:center;
  transform:rotate(-14deg); color:#b23a2e; opacity:.86; mix-blend-mode:multiply; text-align:center; }
.sb__stamp b { font:800 64px/1 var(--sans); letter-spacing:-.02em; } .sb__stamp span { margin-top:8px; font:700 20px/1.1 var(--mono); letter-spacing:.16em; text-transform:uppercase; }
.sb__note { position:absolute; right:80px; bottom:150px; z-index:4; width:290px; padding:30px 28px 38px; background:#ffe680; transform:rotate(4deg);
  box-shadow:0 18px 30px rgba(60,40,10,.3); font:italic 400 38px/1.15 var(--serif); color:#2a2420; } .sb__note em { color:#b23a2e; }
.sb__t { position:absolute; left:96px; right:96px; bottom:150px; z-index:3; color:#1f1a16; } .sb__t--n { right:420px; }
.sb__t .big { color:#1f1a16; } .sb__t em { color:#1f1a16; background:linear-gradient(180deg,transparent 58%,rgba(255,214,64,.85) 58%,rgba(255,214,64,.85) 92%,transparent 92%); }
.sb__k { margin:0 0 18px; font:700 22px/1 var(--mono); letter-spacing:.22em; text-transform:uppercase; color:#8a5a2b; }
.cl { position:absolute; inset:0; z-index:0; } .cl--gold { background:radial-gradient(70% 50% at 50% 40%, #ead29a, #d4b470 70%, #b8964f); }
.cl--paper { background:linear-gradient(170deg,var(--paper),var(--paperd)); } .cl--royal { background:radial-gradient(70% 50% at 50% 40%, #4b1e8a, #1c0838); }
.cl__l { position:absolute; filter:drop-shadow(5px 0 0 #fff) drop-shadow(-5px 0 0 #fff) drop-shadow(0 5px 0 #fff) drop-shadow(0 -5px 0 #fff) drop-shadow(0 34px 34px rgba(30,10,50,.38)); }
.cl__t { position:absolute; left:96px; right:96px; top:50%; transform:translateY(-50%); z-index:4; text-align:center; }
.cl__h { color:var(--ink); letter-spacing:-.045em; } .cl__h em { color:#fff; } .cl--royal ~ .cl__t .cl__h { color:#fff; } .cl--royal ~ .cl__t .cl__h em { color:var(--ac); }
.cl__k { display:inline-block; margin:0 0 30px; padding:14px 22px; background:var(--ink); color:#fff; font:700 24px/1 var(--mono); letter-spacing:.2em; text-transform:uppercase; transform:rotate(-2deg); }
.cl--paper ~ .cl__t .cl__h em { color:var(--acl); }
.bg--reveal { filter:blur(46px) saturate(1.2) brightness(.8); transform:scale(1.25); }
.rv { position:absolute; left:80px; right:80px; top:50%; transform:translateY(-50%); z-index:3; text-align:center; padding:60px 50px;
  border-radius:40px; background:rgba(255,255,255,.12); border:1.5px solid rgba(255,255,255,.3); backdrop-filter:blur(20px); }
.rv__k { margin:0 0 26px; font:700 24px/1 var(--mono); letter-spacing:.26em; text-transform:uppercase; color:var(--ac); }
.rv__h { display:inline-flex; gap:16px; margin:40px 0 0; padding:20px 32px; border-radius:999px; background:#fff; color:var(--bgd); font:700 30px/1 var(--sans); }
.pn__tag { position:absolute; left:0; right:0; z-index:2; margin:0; text-align:center; font-family:var(--serif); font-size:300px; font-weight:600; line-height:1;
  letter-spacing:-.05em; color:transparent; -webkit-text-stroke:3px rgba(255,255,255,.9); }
.pn__tag--bottom { top:150px; } .pn__tag--top { bottom:180px; }
"""


LAB_CSS = """
.chat { position:absolute; left:96px; right:96px; top:150px; z-index:3; font-family:system-ui,-apple-system,sans-serif; }
.ch__h { display:flex; align-items:center; gap:18px; padding-bottom:26px; margin-bottom:22px; border-bottom:1px solid rgba(255,255,255,.18); color:#fff; }
.ch__av { width:64px; height:64px; border-radius:50%; display:grid; place-items:center; font:600 30px/1 system-ui; background:linear-gradient(180deg,#9aa0ad,#6c7280); }
.ch__h b { font:600 32px/1 system-ui; } .ch__h span:last-child { margin-left:auto; font:400 24px/1 system-ui; color:rgba(255,255,255,.55); }
.msg { display:flex; flex-direction:column; margin:14px 0; } .msg p { margin:0; max-width:74%; padding:22px 30px; border-radius:40px; font:400 36px/1.28 system-ui,-apple-system,sans-serif; }
.msg--them { align-items:flex-start; } .msg--them p { background:rgba(58,58,64,.94); color:#fff; border-bottom-left-radius:12px; }
.msg--me { align-items:flex-end; } .msg--me p { background:linear-gradient(180deg,#3a8dff,#0a6cf1); color:#fff; border-bottom-right-radius:12px; }
.msg span { margin:8px 14px 0; font:500 20px/1 system-ui; color:rgba(255,255,255,.5); }
.msg em { color:inherit; font-style:normal; font-weight:700; }
.msg--typing p { display:flex; gap:10px; padding:28px 32px; } .msg--typing i { width:16px; height:16px; border-radius:50%; background:rgba(255,255,255,.55); }
.lock { position:absolute; left:0; right:0; top:104px; z-index:3; text-align:center; color:#fff; font-family:system-ui,-apple-system,sans-serif; }
.lock__d { margin:0; font:600 30px/1 system-ui; opacity:.9; } .lock__t { margin:6px 0 0; font:600 176px/1 system-ui; letter-spacing:-.03em; }
.ntfs { position:absolute; left:64px; right:64px; top:345px; z-index:3; display:flex; flex-direction:column; gap:16px; }
.ntf { display:flex; gap:22px; padding:20px 26px; border-radius:34px; background:rgba(245,245,250,.2); backdrop-filter:blur(30px) saturate(1.5); -webkit-backdrop-filter:blur(30px) saturate(1.5); color:#fff; font-family:system-ui,-apple-system,sans-serif; box-shadow:0 10px 40px rgba(0,0,0,.25); }
.ntf > div { flex:1; min-width:0; }
.ntf__i { flex:none; width:62px; height:62px; border-radius:15px; display:grid; place-items:center; background:var(--ac); color:var(--bgd); font:700 30px/1 system-ui; }
.ntf__a { margin:0; display:flex; justify-content:space-between; font:500 22px/1 system-ui; text-transform:uppercase; letter-spacing:.04em; color:rgba(255,255,255,.7); }
.ntf__t { margin:8px 0 0; font:600 30px/1.2 system-ui; } .ntf__x { margin:4px 0 0; font:400 28px/1.25 system-ui; color:rgba(255,255,255,.88); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ntf em { color:inherit; font-style:normal; }
.rc { position:absolute; left:50%; top:430px; z-index:3; width:720px; margin-left:-360px; padding:44px 46px 70px; transform:rotate(-2.2deg);
  background:linear-gradient(180deg,#fbfaf6,#efece2); color:#1d1b18; font-family:var(--mono); box-shadow:0 50px 80px rgba(0,0,0,.55);
  -webkit-mask:linear-gradient(#000,#000) top/100% calc(100% - 22px) no-repeat, conic-gradient(from -45deg at bottom,#0000,#000 1deg 89deg,#0000 90deg) bottom/36px 22px repeat-x; }
.rc__s { margin:0; text-align:center; font:700 34px/1.1 var(--mono); letter-spacing:.1em; text-transform:uppercase; }
.rc__m { margin:12px 0 0; text-align:center; font:500 20px/1 var(--mono); letter-spacing:.12em; color:#6b665c; text-transform:uppercase; }
.rc__d { margin:22px 0; border-top:3px dashed #8d877a; }
.rc__r { margin:12px 0 0; display:flex; justify-content:space-between; gap:20px; font:500 31px/1.3 var(--mono); }
.rc__r b { font-weight:700; white-space:nowrap; } .rc__r em { font-style:normal; }
.rc__tot { font-size:40px; font-weight:700; } .rc__tot b { color:#9a1b1b; }
.rc__f { margin:30px 0 0; text-align:center; font:500 21px/1.35 var(--mono); letter-spacing:.06em; color:#6b665c; text-transform:uppercase; } .rc__f em { font-style:normal; color:#1d1b18; }
.ko { align-items:center; text-align:center; }
.ko__k { margin:0 0 -10px; font:800 74px/1 var(--sans); letter-spacing:-.035em; color:var(--tx); }
.ko__w { margin:0; font-family:var(--serif); font-weight:900; line-height:.86; letter-spacing:-.06em; font-variation-settings:"opsz" 144, "SOFT" 0, "WONK" 0;
  background-size:cover; -webkit-background-clip:text; background-clip:text; color:transparent; filter:saturate(1.25) contrast(1.1) brightness(1.3); -webkit-text-stroke:2px rgba(255,255,255,.55); white-space:nowrap; }
.ko__l { margin:18px 0 0; font:500 92px/1 var(--serif); letter-spacing:-.03em; color:var(--tx); }
.sp { position:absolute; left:0; right:0; background-size:cover; z-index:0; filter:saturate(.9) contrast(1.05); }
.sp--a { top:0; height:52%; } .sp--b { bottom:0; height:48%; filter:grayscale(.15) saturate(.85) contrast(1.05); }
.sp--ink { background:linear-gradient(180deg,var(--bg),var(--bgd)); }
.sp__l { position:absolute; left:96px; z-index:2; margin:0; padding:10px 16px; font:700 20px/1 var(--mono); letter-spacing:.22em; text-transform:uppercase; color:#fff; background:rgba(0,0,0,.55); }
.sp__l--a { top:120px; } .sp__l--b { bottom:150px; }
.sp__seam { position:absolute; left:56px; right:56px; top:52%; transform:translateY(-50%); z-index:3; padding:34px 40px; background:var(--paper); color:var(--ink); box-shadow:0 30px 70px rgba(0,0,0,.5); }
.sp__seam .big { color:var(--ink); } .sp__seam em { color:var(--acl); }
.sp__s { position:absolute; left:96px; right:96px; bottom:210px; z-index:3; margin:0; font:500 46px/1.15 var(--serif); color:#fff; text-align:right; text-shadow:0 2px 20px rgba(0,0,0,.8); }
.lt { position:absolute; left:64px; right:64px; bottom:200px; z-index:3; }
.lt__bug { display:inline-flex; align-items:center; gap:14px; margin:0; padding:14px 22px; background:var(--ac); color:var(--bgd); font:800 24px/1 var(--sans); letter-spacing:.2em; text-transform:uppercase; }
.lt__bug .rec { background:var(--bgd); box-shadow:none; } .lt__bug i { font-style:normal; font-weight:600; letter-spacing:.08em; text-transform:none; padding-left:14px; border-left:2px solid rgba(0,0,0,.3); }
.lt__p { background:#fff; padding:26px 32px; } .lt__h { margin:0; font-family:var(--sans); font-weight:800; letter-spacing:-.02em; color:var(--ink); }
.lt__h em { font-family:var(--serif); font-style:italic; font-weight:500; color:var(--acl); }
.lt__s { margin:0; padding:18px 32px; background:rgba(10,6,20,.88); font:500 30px/1.25 var(--sans); color:#fff; }
.lt__tk { position:absolute; left:0; right:0; bottom:110px; z-index:3; display:flex; height:58px; overflow:hidden; background:rgba(0,0,0,.85); font:600 25px/58px var(--sans); color:#fff; white-space:nowrap; }
.lt__tk b { position:relative; z-index:2; flex:none; padding:0 24px; background:var(--ac); color:var(--bgd); text-transform:uppercase; letter-spacing:.14em; }
.lt__tk span { padding-left:28px; }
"""


CINEMA_CSS = """
.bars::before,.bars::after { content:""; position:absolute; left:0; right:0; height:96px; background:#000; z-index:7; }
.bars::before { top:0; } .bars::after { bottom:0; }
.tc { margin:0; display:inline-flex; align-items:center; gap:12px; font:700 21px/1 var(--sans); letter-spacing:.24em; text-transform:uppercase; color:#fff; font-variant-numeric:tabular-nums; }
.rec { width:12px; height:12px; border-radius:50%; background:var(--ac); box-shadow:0 0 14px var(--ac); }
.slate__tc { position:absolute; left:96px; top:118px; z-index:8; }
.shade--bw { background:linear-gradient(180deg, rgba(0,0,0,.78), rgba(0,0,0,.2) 30%, rgba(0,0,0,0) 50%, rgba(0,0,0,.5) 70%, rgba(0,0,0,.94) 88%); }
.bw { position:absolute; left:0; right:0; z-index:2; text-align:center; }
.bw__a { margin:0; font:800 92px/1 var(--sans); letter-spacing:-.035em; color:#fff; }
.bw__big { margin:-60px 0 0; font-family:var(--serif); font-weight:500; line-height:.9; letter-spacing:-.055em; color:var(--paper); font-variation-settings:"opsz" 144; text-shadow:0 20px 60px rgba(0,0,0,.35); white-space:nowrap; }
.cut { position:absolute; inset:0; background-size:cover; z-index:3; filter:saturate(.9) contrast(1.05); }
.bw__b { position:absolute; left:96px; right:96px; bottom:140px; z-index:4; text-align:center; }
.bw__c { margin:0; font:500 108px/1 var(--serif); letter-spacing:-.03em; color:#fff; }
.bw__s { margin:30px 0 0; font:700 22px/1 var(--sans); letter-spacing:.24em; text-transform:uppercase; color:var(--ac); }
.sl__a { margin:0; font:800 58px/1 var(--sans); letter-spacing:-.03em; color:#fff; }
.sl__big { margin:6px 0 0 -8px; font-family:var(--serif); font-size:270px; font-weight:500; line-height:.88; letter-spacing:-.055em; color:var(--ac); }
.sl__c { margin:10px 0 0; font:500 80px/1.02 var(--serif); letter-spacing:-.025em; color:#fff; }
.scrub { display:flex; align-items:center; gap:22px; margin-top:40px; font:700 22px/1 var(--sans); letter-spacing:.14em; color:rgba(255,255,255,.85); font-variant-numeric:tabular-nums; }
.scrub__play { font-size:22px; color:var(--ac); }
.scrub__bar { position:relative; flex:1; height:6px; background:rgba(255,255,255,.25); }
.scrub__bar i { position:absolute; left:0; top:0; bottom:0; width:100%; background:var(--ac); }
.scrub__bar b { position:absolute; right:-10px; top:-9px; width:24px; height:24px; border-radius:50%; background:#fff; box-shadow:0 0 18px var(--ac); }
.co__s { margin-top:22px; font-size:62px; line-height:1.1; color:#fff; }
.callout { position:absolute; z-index:3; } .callout svg { display:block; }
.callout p { position:absolute; left:160px; top:-66px; margin:0; white-space:nowrap; font:500 46px/1.05 var(--serif); color:#fff; text-shadow:0 2px 22px rgba(0,0,0,.9); }
.callout em { color:#fff; }
.mon { position:absolute; left:0; right:0; top:0; overflow:hidden; z-index:1; text-align:center; }
.mon span { position:absolute; left:0; right:0; bottom:-78px; font-family:var(--serif); font-size:640px; font-weight:500; line-height:1; letter-spacing:-.06em; color:transparent; -webkit-text-stroke:3px rgba(255,255,255,.85); background:linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,.18)); -webkit-background-clip:text; background-clip:text; }
.board { display:grid; grid-template-columns:1fr 1fr; margin-top:40px; border:2px solid var(--ac); background:rgba(0,0,0,.72); }
.board__c { display:flex; flex-direction:column; gap:10px; padding:24px 28px; } .board__c + .board__c { border-left:2px solid var(--ac); }
.board__c--on { background:linear-gradient(180deg, rgba(255,255,255,.14), rgba(255,255,255,.03)); }
.board__l { font:700 19px/1 var(--sans); letter-spacing:.28em; text-transform:uppercase; color:rgba(255,255,255,.7); }
.board b { font:800 62px/1.05 var(--sans); color:#fff; font-variant-numeric:tabular-nums; white-space:nowrap; letter-spacing:-.02em; } .board__c--on b { color:var(--ac); }
.board__s { font:600 22px/1.3 var(--sans); color:rgba(255,255,255,.82); }
.s--img > .pad { padding-left:96px; padding-right:96px; }
"""


R = {'notes': r_notes, 'hottake': r_hottake, 'proof': r_proof, 'scrapbook': r_scrapbook, 'collage': r_collage, 'reveal': r_reveal,
     'pano': r_pano, 'chat': r_chat, 'notif': r_notif, 'receipt': r_receipt, 'knockout': r_knockout, 'split': r_split, 'lowerthird': r_lowerthird,
     'bigword': r_bigword, 'slate': r_slate, 'callout': r_callout, 'monument': r_monument, 'scoreboard': r_scoreboard, 'cover': r_cover, 'statement': r_statement, 'quote': r_quote, 'list': r_list, 'compare': r_compare, 'steps': r_steps,
     'stat': r_stat, 'photo': r_photo, 'paper': r_paper, 'cta': r_cta}


def css(c):
    t = c.t
    return f'''
{font_css(c.b)}
:root {{ --bg:{t['bg']}; --bgd:{t['bg_deep']}; --surf:{t['surface']}; --tx:{t['text']}; --mu:{t['muted']}; --ac:{t['accent']};
  --paper:{t['paper']}; --paperd:{t['paper_deep']}; --ink:{t['ink']}; --acl:{t['accent_light']}; --mul:{t['muted_light']};
  --serif:'BrandDisplay',Georgia,serif; --sans:'BrandBody',system-ui,sans-serif; --mono:'BrandMono',ui-monospace,monospace; }}
* {{ box-sizing:border-box; }} html,body {{ margin:0; background:#000; }}
.s {{ position:relative; width:{c.W}px; height:{c.H}px; overflow:hidden; display:flex; flex-direction:column; padding:120px 96px 110px; font-family:var(--sans); }}
.s--dark {{ background:radial-gradient(90% 60% at 50% 30%, {rgba(t['accent'], .10)}, transparent 62%), linear-gradient(180deg,{t['bg']},{t['bg_deep']}); color:var(--tx); --acc:var(--ac); --rule:{rgba(t['accent'], .45)}; --mut:var(--mu); }}
.s--light {{ background:radial-gradient(70% 45% at 18% 8%, rgba(255,255,255,.7), transparent 70%), linear-gradient(165deg,{t['paper']},{t['paper_deep']}); color:var(--ink); --acc:var(--acl); --rule:{rgba(t['accent_light'], .5)}; --mut:var(--mul); }}
.grain {{ position:absolute; inset:0; background-image:{GRAIN}; background-size:240px; mix-blend-mode:soft-light; opacity:.7; pointer-events:none; z-index:8; }}
.s--light .grain {{ mix-blend-mode:multiply; opacity:.3; }}
.fr {{ position:absolute; inset:30px; border:1.5px solid var(--rule); pointer-events:none; z-index:9; }}
.top,.foot {{ position:absolute; left:96px; right:96px; display:flex; justify-content:space-between; font:600 19px/1 var(--mono); letter-spacing:.24em; text-transform:uppercase; color:var(--acc); z-index:10; }}
.top {{ top:62px; }} .foot {{ bottom:58px; }}
.s--img .top,.s--img .foot {{ color:rgba(255,255,255,.82); }} .s--img .fr {{ border-color:rgba(255,255,255,.28); }}
.k {{ font:600 22px/1.2 var(--mono); letter-spacing:.28em; text-transform:uppercase; color:var(--acc); margin:0 0 30px; }}
h1,h2,blockquote {{ margin:0; font-family:var(--serif); font-weight:500; letter-spacing:-.025em; color:inherit; font-variation-settings:"opsz" 144; }}
em {{ font-style:italic; font-weight:400; color:var(--acc); }}
.pad {{ position:relative; z-index:3; flex:1; display:flex; flex-direction:column; justify-content:flex-start; padding-top:40px; }}
.pad--c {{ justify-content:center; padding-top:0; }}
.lede {{ font-size:40px; line-height:1.36; color:var(--mut); margin:34px 0 0; max-width:880px; }}
.lede--s {{ font-size:34px; }} .s--img .lede {{ color:rgba(255,255,255,.86); }}
.sub {{ margin:34px 0 0; font:600 24px/1.2 var(--mono); letter-spacing:.2em; text-transform:uppercase; color:var(--acc); }}
.note {{ font:600 22px/1.45 var(--mono); letter-spacing:.14em; text-transform:uppercase; color:var(--acc); margin:36px 0 0; }}
.s--img {{ padding:0; color:#fff; --acc:{t['accent']}; }} .s--img em {{ color:var(--acc); }}
.bg {{ position:absolute; inset:0; background-size:cover; filter:saturate(.9) contrast(1.05); z-index:0; }}
.bg--blur {{ filter:blur(9px) saturate(.9) brightness(.7); transform:scale(1.08); }}
.tint {{ position:absolute; inset:0; z-index:1; background:{rgba(t['bg'], .22)}; mix-blend-mode:multiply; }}
.shade {{ position:absolute; inset:0; z-index:1; }}
.shade--cover,.shade--bottom {{ background:linear-gradient(180deg, {rgba(t['bg_deep'], .55)}, {rgba(t['bg_deep'], 0)} 20%, {rgba(t['bg_deep'], 0)} 38%, {rgba(t['bg_deep'], .86)} 64%, {t['bg_deep']} 88%); }}
.shade--top {{ background:linear-gradient(180deg, {t['bg_deep']}, {rgba(t['bg_deep'], .8)} 30%, {rgba(t['bg_deep'], 0)} 58%, {rgba(t['bg_deep'], .5)}); }}
.shade--desk {{ background:radial-gradient(70% 50% at 50% 45%, {rgba(t['bg_deep'], .2)}, {rgba(t['bg_deep'], .8)}); }}
.imgtop {{ position:absolute; left:96px; right:96px; top:150px; z-index:3; }}
.imgbot {{ position:absolute; left:96px; right:96px; bottom:140px; z-index:3; }}
.cover {{ color:#fff; letter-spacing:-.035em; }} .pad .cover,.pad .big {{ color:var(--tx); }}
.big {{ color:inherit; }} .h2m {{ color:inherit; }}
.qm {{ font:500 280px/.7 var(--serif); color:var(--acc); height:150px; margin-bottom:26px; }}
.by {{ display:flex; align-items:center; gap:22px; margin:44px 0 0; font:600 22px/1.3 var(--mono); letter-spacing:.16em; text-transform:uppercase; color:var(--acc); }}
.rule {{ width:70px; height:3px; background:var(--acc); flex:none; }}
.rows {{ list-style:none; margin:54px 0 0; padding:0; }}
.rows li {{ display:flex; align-items:baseline; gap:34px; padding:26px 0; border-top:1.5px solid var(--rule); }}
.rows li:last-child {{ border-bottom:1.5px solid var(--rule); }}
.rows b {{ font:500 60px/1 var(--serif); color:var(--acc); width:96px; flex:none; }}
.rows span {{ line-height:1.2; }}
.cmps {{ display:flex; flex-direction:column; gap:30px; margin-top:44px; flex:1; }}
.cmp {{ flex:1; padding:34px 44px; border:1.5px solid var(--rule); background:{rgba(t['surface'], .5)}; display:flex; flex-direction:column; justify-content:center; gap:22px; }}
.s--light .cmp {{ background:rgba(255,255,255,.4); }}
.cmp--on {{ border-color:var(--acc); background:linear-gradient(180deg,{rgba(t['accent'], .20)},{rgba(t['accent'], .05)}); }}
.chip {{ margin:0; align-self:flex-start; padding:9px 18px; font:700 20px/1 var(--mono); letter-spacing:.24em; text-transform:uppercase; border:1.5px solid var(--rule); color:var(--mut); }}
.cmp--on .chip {{ background:var(--acc); color:{t['bg_deep']}; border-color:var(--acc); }}
.cmp__t {{ margin:0; font-family:var(--serif); font-weight:500; letter-spacing:-.02em; }}
.rail {{ position:relative; margin-top:50px; padding-left:8px; display:flex; flex-direction:column; gap:30px; }}
.rail::before {{ content:""; position:absolute; left:33px; top:30px; bottom:30px; width:3px; background:linear-gradient(180deg,var(--acc),{rgba(t['accent'], .2)}); }}
.st {{ position:relative; display:flex; gap:40px; align-items:flex-start; }}
.dia {{ flex:none; width:52px; height:52px; margin-top:6px; position:relative; }}
.dia::after {{ content:""; position:absolute; left:10px; top:10px; width:30px; height:30px; transform:rotate(45deg); border:3px solid var(--acc); background:var(--bg); }}
.s--light .dia::after {{ background:var(--paper); }}
.st__t {{ margin:0; font-family:var(--serif); font-weight:500; letter-spacing:-.02em; line-height:1.05; }}
.st__d {{ margin:10px 0 0; color:var(--mut); line-height:1.3; }}
.num {{ margin:10px 0 0 -10px; font-family:var(--serif); font-weight:500; letter-spacing:-.05em; color:var(--acc); line-height:.9; font-variation-settings:"opsz" 144; }}
.pre {{ margin:0; font:italic 400 64px/1 var(--serif); color:var(--mut); }}
.unit {{ margin:6px 0 0; font:italic 400 76px/1.05 var(--serif); letter-spacing:-.02em; }}
.sheet {{ position:relative; width:100%; background:radial-gradient(80% 60% at 20% 0%, rgba(255,255,255,.85), transparent 70%), linear-gradient(170deg,{t['paper']},{t['paper_deep']}); color:var(--ink); padding:46px 52px 30px; transform:rotate(-1.2deg); box-shadow:0 50px 90px rgba(0,0,0,.6); --acc:var(--acl); }}
.sheet > * {{ position:relative; z-index:1; }}
.sheet::after {{ content:""; position:absolute; inset:0; z-index:0; background:{t['paper_deep']}; transform:rotate(3deg) translate(14px,10px); box-shadow:0 30px 60px rgba(0,0,0,.45); }}
.k--ink {{ color:var(--acl); }} .h2ink {{ color:var(--ink); margin-bottom:12px; }} .h2ink em {{ color:var(--acl); }}
.sheet__r {{ border-top:2.5px solid var(--acl); padding:20px 0 12px; display:grid; grid-template-columns:150px 1fr; column-gap:18px; }}
.sheet__r b {{ font:700 26px/1.3 var(--mono); letter-spacing:.14em; text-transform:uppercase; color:var(--acl); }}
.sheet__r span {{ font:400 34px/1.22 var(--serif); }} .sheet__r i {{ grid-column:2; height:38px; border-bottom:1.5px solid rgba(0,0,0,.25); }}
.close {{ margin:54px 0 0; font:500 50px/1.1 var(--serif); text-align:center; color:#fff; }} .close em {{ color:var(--ac); }}
.btn {{ align-self:flex-start; margin:56px 0 0; display:inline-flex; align-items:center; gap:22px; padding:26px 38px; background:var(--ac); color:{t['bg_deep']}; font:700 34px/1 var(--sans); }}
.btn span {{ font-size:40px; }}
.url {{ margin:30px 0 0; font:600 26px/1 var(--mono); letter-spacing:.16em; color:var(--acc); }}
.logo {{ position:absolute; left:96px; bottom:120px; height:56px; z-index:5; }}
''' + CINEMA_CSS + LAB_CSS + FYP_CSS


def build_html(d, car, b):
    W, H = CANVAS[car.get('format', '4:5')]
    c = Ctx(b, d, car, W, H)
    slides, total = car['slides'], len(car['slides'])
    series = car.get('series', b['name'])
    secs = []
    for i, sl in enumerate(slides, 1):
        r = sl.get('recipe')
        if r not in R:
            die(f'slide {i}: unknown recipe "{r}". carousel.py list shows them.')
        body, theme = R[r](c, sl)
        if sl.get('theme') in ('dark', 'light') and 'img' not in theme:
            theme = sl['theme']
        cls = 's--img' if 'img' in theme else ''
        th = 'light' if theme.split()[0] == 'light' else 'dark'
        foot = f'<span>{html.escape(car.get("signoff", b["name"]))}</span>' if i == total else '<span class="sw">Swipe →</span>'
        secs.append(f'<section class="s s--{th} {cls}" data-n="{i}">{body}<div class="grain"></div><div class="fr"></div>'
                    f'<header class="top"><span></span><span>{i:02d} / {total:02d}</span></header>'
                    f'<footer class="foot"><span>{html.escape(series) if i < total else ""}</span>{foot}</footer></section>')
    js = '''<script>
const q=new URLSearchParams(location.search).get('n');
if(q)document.querySelectorAll('.s').forEach(s=>{if(s.dataset.n!==q)s.remove()});
document.fonts.ready.then(()=>{const bad=[];document.querySelectorAll('.s').forEach(s=>{const n=s.dataset.n,sr=s.getBoundingClientRect();
 s.querySelectorAll('.pad').forEach(p=>{if(p.scrollHeight>p.clientHeight+2)bad.push(n+':content taller than the slide')});
 s.querySelectorAll('.imgbot,.imgtop').forEach(p=>{const r=p.getBoundingClientRect();if(r.top<sr.top+110||r.bottom>sr.bottom-110)bad.push(n+':text block runs into the margin')});
 s.querySelectorAll('.imgbot,.imgtop,.pad,h1,h2,.big').forEach(p=>{const r=p.getBoundingClientRect();if(r.width&&(r.left<sr.left+40||r.right>sr.right-40))bad.push(n+':text outside the profile-grid safe zone')});
 s.querySelectorAll('[data-fit]').forEach(e=>{if(e.scrollWidth>e.clientWidth+2)bad.push(n+':a line is wider than the slide ('+e.textContent.trim().slice(0,30)+')')})});
 document.documentElement.dataset.problems=bad.join('|');});
</script>'''
    return f'<!doctype html><html><head><meta charset="utf-8"/><style>{css(c)}</style></head><body>{"".join(secs)}{js}</body></html>', W, H, c


# ---------- chrome ----------
def chrome():
    cands = [os.environ.get('CLIP_CHROME'),
             '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
             '/Applications/Chromium.app/Contents/MacOS/Chromium',
             '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
             shutil.which('google-chrome'), shutil.which('chromium'), shutil.which('chrome'),
             r'C:\Program Files\Google\Chrome\Application\chrome.exe',
             r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe']
    for p in cands:
        if p and Path(p).exists():
            return p
    die('No Chrome found for rendering slides. Install Google Chrome (free), or set CLIP_CHROME to a Chromium path.')


def run_chrome(args, url, timeout=120):
    with tempfile.TemporaryDirectory() as prof:
        return subprocess.run([chrome(), '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars', '--no-first-run',
                               f'--user-data-dir={prof}', '--allow-file-access-from-files', '--force-device-scale-factor=1',
                               '--virtual-time-budget=6000', *args, url], capture_output=True, text=True, timeout=timeout)


def resolve(arg):
    p = Path(arg).expanduser()
    if (p / 'carousel.json').exists():
        return p.resolve()
    q = ROOT / 'projects' / arg
    if '/' in arg and (ROOT / 'projects' / arg.split('/')[0] / 'carousels' / arg.split('/', 1)[1] / 'carousel.json').exists():
        return ROOT / 'projects' / arg.split('/')[0] / 'carousels' / arg.split('/', 1)[1]
    die(f'no carousel.json at {arg} (use <project>/<slug> or a folder path)')


# ---------- commands ----------
def cmd_list(_):
    print('Slide recipes (fields in [] are optional). Use *word* for the emphasis word and \\n for a line break.\n')
    for k, v in RECIPES.items():
        print(f'  {k:10s} {v}')
    print('\nEvery slide may also carry: theme (dark|light), alt (alt text), image + pos for photo recipes.')


STARTER = {
    'title': 'Working title', 'series': '', 'format': '4:5', 'signoff': '',
    'source': 'Where this comes from (video take + timecode, or write-up). Quote verbatim.',
    'caption': 'Post caption: extends the post, does not transcribe it. End on the one action.',
    'slides': [
        {'recipe': 'cover', 'eyebrow': 'The hook', 'headline': 'A promise in\n3 to 10 *words*', 'sub': 'What it pays off →',
         'alt': 'Cover slide: …'},
        {'recipe': 'statement', 'eyebrow': 'The claim', 'headline': 'One claim, one *reason*.', 'text': 'The reason to believe it.', 'alt': ''},
        {'recipe': 'cta', 'headline': 'One last *action*.', 'action': 'Do the thing', 'url': '', 'alt': ''},
    ]}


def cmd_new(a):
    d = ROOT / 'projects' / a.project / 'carousels' / slugify(a.slug)
    (d / 'images').mkdir(parents=True, exist_ok=True)
    f = d / 'carousel.json'
    if f.exists():
        die(f'{f} already exists')
    b = brand()
    s = json.loads(json.dumps(STARTER))
    s['format'], s['series'], s['signoff'] = a.format, b['name'], b['name']
    f.write_text(json.dumps(s, indent=2, ensure_ascii=False))
    print(f'→ {f}\n  drop image files in {d / "images"}')


def cmd_grab(a):
    pj = ROOT / 'projects' / a.project
    takes = json.loads((pj / 'takes.json').read_text())
    tk = takes.get(a.take) or die(f'take {a.take} not in {pj / "takes.json"}')
    d = pj / 'carousels' / slugify(a.slug) / 'images'
    d.mkdir(parents=True, exist_ok=True)
    out = d / f'{a.name}.jpg'
    r = subprocess.run([ffmpeg(), '-y', '-v', 'error', '-ss', str(a.time), '-i', tk['file'], '-frames:v', '1', '-q:v', '2', str(out)],
                       capture_output=True, text=True)
    if r.returncode:
        die(r.stderr[-300:])
    w, hh = Image.open(out).size
    print(f'→ {out}  ({w}x{hh}, your own footage)')


def cmd_shotlist(a):
    d = resolve(a.carousel)
    car = json.loads((d / 'carousel.json').read_text())
    L = [f'# Image Shot List: {car.get("title", d.name)}\n',
         'You generate or find these; Claude Code does everything else. Drop each file at the path shown, then say "images in".\n']
    for i, sl in enumerate(car['slides'], 1):
        if sl.get('image') or sl.get('shot'):
            s = sl.get('shot', {})
            L.append(f'## Slide {i} · {sl["recipe"]} · file to drop: `{d / (sl.get("image") or f"images/s{i:02d}.jpg")}`')
            L.append(f'- **Why this image:** {s.get("why", "what it shows that words can\'t")}')
            L.append(f'- **Source:** {s.get("source", "GENERATE (ChatGPT / Grok / Gemini) | FIND (licensed photo) | CAPTURE (your own screen or photo)")}')
            L.append(f'- **Realism plan:** {s.get("realism", "materials, light, setting, what makes it believable; AI tells to avoid")}')
            L.append(f'- **Prompt:** {s.get("prompt", "<paste-ready prompt> … vertical 4:5, no text in image")}')
            L.append(f'- **Framing:** keep the {"top" if sl.get("position") == "top" else "bottom"} third clear for the headline; subject centred.')
            L.append(f'- **Avoid:** {s.get("avoid", "robots, glowing brains, fake UI, any text or logos")}\n')
    if len(L) == 2:
        L.append('No slide in this carousel needs an image.')
    (d / 'SHOT-LIST.md').write_text('\n'.join(L))
    print(f'→ {d / "SHOT-LIST.md"}')


def cmd_build(a):
    d = resolve(a.carousel)
    car = json.loads((d / 'carousel.json').read_text())
    b = brand()
    page, W, H, c = build_html(d, car, b)
    src = d / 'carousel.html'
    src.write_text(page)
    out = d / 'out'
    out.mkdir(exist_ok=True)
    for old in out.glob('*.jpg'):
        old.unlink()
    n = len(car['slides'])
    qa = []
    # 1) layout problems, read back from the page itself
    r = run_chrome(['--dump-dom'], src.as_uri())
    m = re.search(r'data-problems="([^"]*)"', r.stdout or '')
    problems = [html.unescape(x) for x in (m.group(1).split('|') if m and m.group(1) else [])]
    qa += [f'✗ slide {p}' for p in problems]
    # 2) one screenshot per slide
    for i in range(1, n + 1):
        png = out / f'{i:02d}.png'
        run_chrome([f'--window-size={W},{H + 140}', f'--screenshot={png}'], src.as_uri() + f'?n={i}')
        if not png.exists():
            die(f'Chrome did not render slide {i}')
        im = Image.open(png).convert('RGB')
        if im.size != (W, H):
            im = im.crop((0, 0, W, H))
        im.save(out / f'{i:02d}.jpg', quality=95)
        png.unlink()
    imgs = [Image.open(out / f'{i:02d}.jpg') for i in range(1, n + 1)]
    imgs[0].save(out / 'carousel.pdf', save_all=True, append_images=imgs[1:], resolution=96)
    # contact sheet
    th = 360
    tw = round(th * W / H)
    sheet = Image.new('RGB', (min(n, 5) * (tw + 12) + 12, ((n - 1) // 5 + 1) * (th + 12) + 12), '#111')
    for i, im in enumerate(imgs):
        sheet.paste(im.resize((tw, th)), (12 + (i % 5) * (tw + 12), 12 + (i // 5) * (th + 12)))
    sheet.save(out / 'contact-sheet.jpg', quality=90)
    # 3) contrast and image checks
    t = c.t
    for fam, bgc, fgc, lab in (('dark', t['bg'], t['text'], 'dark text'), ('dark', t['bg'], t['accent'], 'dark accent'),
                               ('light', t['paper'], t['ink'], 'light text'), ('light', t['paper'], t['accent_light'], 'light accent')):
        ratio = contrast(bgc, fgc)
        if ratio < 4.5:
            qa.append(f'✗ contrast {lab}: {ratio:.1f}:1 (needs 4.5:1). Adjust brand.json colours.')
    for i, sl in enumerate(car['slides'], 1):
        if sl.get('image'):
            w, hh = Image.open(d / sl['image']).size
            if w < W:
                qa.append(f'✗ slide {i}: image is {w}px wide, needs at least {W}')
        if not sl.get('alt'):
            qa.append(f'· slide {i}: no alt text yet')
    (d / 'ALT.md').write_text('\n'.join(f'{i}. {sl.get("alt", "")}' for i, sl in enumerate(car['slides'], 1)))
    bad = [x for x in qa if x.startswith('✗')]
    (d / 'QA.md').write_text('# QA\n\n' + ('\n'.join(qa) if qa else 'All automatic checks passed.') +
                             '\n\nStill by eye: phone-size preview of every slide, spelling, verbatim quotes, every number traceable, '
                             'no claim the slides don\'t prove.\n')
    print(f'{n} slides ({W}x{H}) → {out}\n  carousel.pdf (LinkedIn document), contact-sheet.jpg, ALT.md, QA.md')
    for x in qa:
        print('  ' + x)
    if bad:
        sys.exit(1)


def cmd_generate(a):
    import kie
    import carousel_motion as cm
    d = resolve(a.carousel)
    cm.generate(d, json.loads((d / 'carousel.json').read_text()), kie, a.clips)


def cmd_motion(a):
    import carousel_motion as cm
    d = resolve(a.carousel)
    car = json.loads((d / 'carousel.json').read_text())
    page, W, H, _ = build_html(d, car, brand())
    cm.motion(d, page, car, W, H, a.seconds, a.style)


def cmd_reel(a):
    import carousel_motion as cm
    d = resolve(a.carousel)
    cm.reel(d, len(json.loads((d / 'carousel.json').read_text())['slides']), a.per, a.music)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('list')
    p = sp.add_parser('new'); p.add_argument('project'); p.add_argument('slug'); p.add_argument('--format', default='3:4', choices=list(CANVAS))
    p = sp.add_parser('grab'); [p.add_argument(x) for x in ('project', 'take', 'time', 'slug', 'name')]
    p = sp.add_parser('shotlist'); p.add_argument('carousel')
    p = sp.add_parser('build'); p.add_argument('carousel')
    p = sp.add_parser('generate'); p.add_argument('carousel'); p.add_argument('--clips', action='store_true', help='also animate cinemagraph slides with Grok (~$0.11 each)')
    p = sp.add_parser('motion'); p.add_argument('carousel'); p.add_argument('--seconds', type=float, default=6.0)
    p.add_argument('--style', choices=['push', 'whip', 'type', 'rack', 'cinemagraph'], help='one motion style for every slide (else each slide\'s "motion", else push)')
    p = sp.add_parser('reel'); p.add_argument('carousel'); p.add_argument('--per', type=float, default=2.6); p.add_argument('--music')
    a = ap.parse_args()
    {'list': cmd_list, 'new': cmd_new, 'grab': cmd_grab, 'shotlist': cmd_shotlist, 'build': cmd_build, 'generate': cmd_generate,
     'motion': cmd_motion, 'reel': cmd_reel}[a.cmd](a)


if __name__ == '__main__':
    main()
