#!/usr/bin/env python3
"""Carousel Studio: brand-driven carousels (Instagram 4:5, LinkedIn documents, 1:1, 9:16) from a carousel.json.

    tools/carousel.py list                              the slide recipes and their fields
    tools/carousel.py new <project> <slug> [--format 4:5]   a starter carousel.json + images/ folder
    tools/carousel.py grab <project> <take> <time> <slug> <name>   a still from your own footage -> images/<name>.jpg
    tools/carousel.py shotlist <project>/<slug>         the Image Shot List for every slide that needs an image
    tools/carousel.py build <project>/<slug>            out/01.jpg … + carousel.pdf + contact-sheet.jpg + QA.md + ALT.md

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


R = {'cover': r_cover, 'statement': r_statement, 'quote': r_quote, 'list': r_list, 'compare': r_compare, 'steps': r_steps,
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
'''


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
                    f'<footer class="foot"><span>{html.escape(series)}</span>{foot}</footer></section>')
    js = '''<script>
const q=new URLSearchParams(location.search).get('n');
if(q)document.querySelectorAll('.s').forEach(s=>{if(s.dataset.n!==q)s.remove()});
document.fonts.ready.then(()=>{const bad=[];document.querySelectorAll('.s').forEach(s=>{const n=s.dataset.n,sr=s.getBoundingClientRect();
 s.querySelectorAll('.pad').forEach(p=>{if(p.scrollHeight>p.clientHeight+2)bad.push(n+':content taller than the slide')});
 s.querySelectorAll('.imgbot,.imgtop').forEach(p=>{const r=p.getBoundingClientRect();if(r.top<sr.top+110||r.bottom>sr.bottom-110)bad.push(n+':text block runs into the margin')});
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


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('list')
    p = sp.add_parser('new'); p.add_argument('project'); p.add_argument('slug'); p.add_argument('--format', default='4:5', choices=list(CANVAS))
    p = sp.add_parser('grab'); [p.add_argument(x) for x in ('project', 'take', 'time', 'slug', 'name')]
    p = sp.add_parser('shotlist'); p.add_argument('carousel')
    p = sp.add_parser('build'); p.add_argument('carousel')
    a = ap.parse_args()
    {'list': cmd_list, 'new': cmd_new, 'grab': cmd_grab, 'shotlist': cmd_shotlist, 'build': cmd_build}[a.cmd](a)


if __name__ == '__main__':
    main()
