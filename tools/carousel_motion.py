#!/usr/bin/env python3
"""Motion for Carousel Studio: generated images, video carousels and a carousel-to-Reel cut.

  carousel.py generate <project>/<slug>     GPT Image 2.5 (kie.ai) makes every missing image from its shot prompt
  carousel.py generate <project>/<slug> --clips          also animates every "cinemagraph" slide's photo with Grok (~$0.11)
  carousel.py motion   <project>/<slug> [--seconds 6] [--style push|whip|type|rack|cinemagraph]   every slide as a 4:5 MP4 (out/motion/01.mp4 …): the photo
                       pushes in, the subject cut-out moves with it, the type lands in a cascade. Instagram carousels
                       accept video slides, and they autoplay in the feed.
  carousel.py reel     <project>/<slug> [--per 2.6] [--music bed.mp3]   the same slides as ONE 9:16 Reel for the
                       Reels tab / For You feed: each slide in turn over a blurred copy of itself, a whoosh per slide,
                       a beat under it.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, ffmpeg  # noqa: E402

HF = 'hyperframes@0.8.34'
FF = ffmpeg()

BIG = '.bw__big, .mon span, .sl__big, .num, .ko__w, .lock__t'
TEXT = '.big, .cover, .bw__c, .sl__c, .ko__l, .lt__h'
POPS = '.msg, .ntf'
ITEMS = ('.k, .bw__a, .bw__c, .bw__s, .sl__a, .sl__c, .imgtop > *, .imgbot > *, .pad > *, .tc, .board, .callout, .sheet, .ch__h, '
         '.lock__d, .rc, .sp__seam, .sp__l, .sp__s, .lt__bug, .lt__p, .lt__s, .lt__tk, .msg, .ntf')
PHOTO = "['.bg:not(.bg--blur)', '.cut', '.sp']"

# Every style shares the head (selectors, items never animated twice) and the tail (scrubber, REC blink, registration).
HEAD = """
const tl = gsap.timeline({ paused: true });
const D = __DUR__;
const A = s => gsap.utils.toArray(s);
const bigs = A('__BIG__'), pops = A('__POPS__');
const items = A('__ITEMS__').filter(e => !bigs.includes(e) && !pops.includes(e) && !bigs.some(b => e.contains(b) || b.contains(e)));
gsap.set(A(__PHOTO__), { transformOrigin: '50% 45%', force3D: true });
tl.from('.shade, .tint', { opacity: 0, duration: .5, ease: 'power2.out' }, 0);
"""
TAIL = """
tl.fromTo('.scrub__bar i', { width: '0%' }, { width: '100%', duration: D * .7, ease: 'power1.inOut' }, .6);
tl.fromTo('.scrub__bar b', { right: '100%' }, { right: '-10px', duration: D * .7, ease: 'power1.inOut' }, .6);
tl.from('.rec', { opacity: 0, repeat: Math.floor(D), yoyo: true, duration: .5, ease: 'steps(1)' }, 0);
tl.fromTo('.lt__tk span', { x: 0 }, { x: -700, duration: D, ease: 'none' }, 0);
tl.set({}, {}, D);
window.__timelines = window.__timelines || {}; window.__timelines['__NAME__'] = tl;
"""
STYLES = {
    # slow push-in, the big word slides in from the right, the rest cascades
    'push': """
tl.fromTo(A(__PHOTO__), { scale: 1.14 }, { scale: 1.0, duration: D, ease: 'power1.out' }, 0);
tl.from(bigs, { x: 260, opacity: 0, filter: 'blur(16px)', duration: .9, ease: 'power4.out' }, .25);
tl.from(pops, { y: 40, opacity: 0, duration: .5, stagger: .18, ease: 'power3.out' }, .35);
tl.from(items, { y: 46, opacity: 0, duration: .6, stagger: .12, ease: 'power3.out' }, .45);
""",
    # fast: the frame whips in from the right and everything slams on the beat (FYP pace)
    'whip': """
tl.fromTo(A(__PHOTO__), { scale: 1.32, x: 260 }, { scale: 1.06, x: 0, duration: .5, ease: 'expo.out' }, 0);
tl.to(A(__PHOTO__), { scale: 1.0, duration: D - .5, ease: 'none' }, .5);
tl.from(bigs, { x: 480, skewX: -14, opacity: 0, duration: .42, ease: 'expo.out' }, .14);
tl.from(pops, { x: 200, opacity: 0, duration: .3, stagger: .08, ease: 'expo.out' }, .2);
tl.from(items, { x: 180, opacity: 0, duration: .34, stagger: .06, ease: 'expo.out' }, .26);
""",
    # messages and notifications arrive one by one, then the headline types itself on
    'type': """
tl.fromTo(A(__PHOTO__), { scale: 1.08 }, { scale: 1.0, duration: D, ease: 'none' }, 0);
pops.forEach((e, i) => tl.from(e, { y: 36, scale: .86, opacity: 0, duration: .32, ease: 'back.out(2.2)',
  transformOrigin: e.classList.contains('msg--me') ? '100% 100%' : '0% 100%' }, .3 + i * .5));
let at = .4 + pops.length * .5;
const typed = A('__TEXT__, __BIG__').filter(e => !pops.some(p => p.contains(e)));
typed.forEach(e => { const n = Math.max(6, Math.min(36, e.textContent.trim().length)), d = n * .032;
  tl.fromTo(e, { clipPath: 'inset(-30% 100% -30% 0%)' }, { clipPath: 'inset(-30% 0% -30% 0%)', duration: d, ease: 'steps(' + n + ')' }, at); at += d * .7; });
tl.from(items.filter(e => !typed.some(t => e === t || e.contains(t))), { opacity: 0, y: 24, duration: .4, stagger: .1, ease: 'power2.out' }, .2);
""",
    # rack focus: the photo pulls from soft to sharp, then the type settles in
    'rack': """
tl.fromTo(A(__PHOTO__), { scale: 1.1, filter: 'blur(26px) saturate(.9) contrast(1.05)' }, { scale: 1.0, filter: 'blur(0px) saturate(.9) contrast(1.05)', duration: 1.1, ease: 'power2.inOut' }, 0);
tl.to(A(__PHOTO__), { scale: .97, duration: D - 1.1, ease: 'none' }, 1.1);
tl.from(bigs, { opacity: 0, scale: 1.12, filter: 'blur(20px)', duration: .9, ease: 'power3.out' }, .7);
tl.from(pops, { opacity: 0, y: 30, duration: .5, stagger: .2, ease: 'power3.out' }, .8);
tl.from(items, { opacity: 0, y: 30, duration: .6, stagger: .1, ease: 'power3.out' }, .95);
""",
    # the photo is a Grok clip that moves on its own; the type just lands over it
    'cinemagraph': """
tl.fromTo(A(__PHOTO__), { scale: 1.06 }, { scale: 1.0, duration: D, ease: 'none' }, 0);
tl.from(bigs, { y: 60, opacity: 0, filter: 'blur(12px)', duration: 1, ease: 'power3.out' }, .5);
tl.from(pops, { y: 40, opacity: 0, duration: .5, stagger: .25, ease: 'power3.out' }, .5);
tl.from(items, { y: 40, opacity: 0, duration: .7, stagger: .14, ease: 'power3.out' }, .8);
""",
}
CLIP_PROMPT = ('Subtle cinematic motion only: a slow camera push-in, natural ambient movement such as light flicker, drifting dust, '
               'screen glow, breathing. The framing, every person and every object stay exactly the same. No new objects, no text, no cuts.')


def anim(style, seconds, name):
    js = HEAD + STYLES[style] + TAIL
    for k, v in (('__BIG__', BIG), ('__TEXT__', TEXT), ('__POPS__', POPS), ('__ITEMS__', ITEMS), ('__PHOTO__', PHOTO),
                 ('__DUR__', str(seconds)), ('__NAME__', name)):
        js = js.replace(k, v)
    return js


def fit_width(path, w):
    from PIL import Image
    im = Image.open(path)
    if im.width < w:      # 1K generations come out ~1008 px wide; lift to the slide width
        im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(path)


def style_of(car, sl, forced=None):
    return forced or sl.get('motion') or car.get('motion') or 'push'


def clip_path(d, sl):
    return d / Path(sl['image']).with_name(Path(sl['image']).stem + '-clip.mp4')


def generate(d, car, kie, clips=False):
    made = 0
    for i, sl in enumerate(car['slides'], 1):
        shot, img = sl.get('shot') or {}, sl.get('image')
        if not img or (d / img).exists() or not shot.get('prompt'):
            continue
        (d / img).parent.mkdir(parents=True, exist_ok=True)
        for aspect in ('3:4', '2:3'):   # GPT Image 2.5 has no 4:5; 3:4 crops cleanly
            try:
                kie.image(shot['prompt'], str(d / img), aspect=aspect)
                fit_width(d / img, 1080)
                made += 1
                print(f'  slide {i}: {img} ({aspect})')
                break
            except SystemExit as e:
                print(f'  slide {i}: {aspect} refused ({str(e)[:80]}), trying the next ratio')
    print(f'{made} image(s) generated')
    if not clips:
        return
    for i, sl in enumerate(car['slides'], 1):
        if style_of(car, sl) != 'cinemagraph' or not sl.get('image') or clip_path(d, sl).exists():
            continue
        prompt = (sl.get('shot') or {}).get('motion') or CLIP_PROMPT
        for aspect in ('2:3', '9:16'):
            try:
                kie.video(prompt, str(clip_path(d, sl)), first_frame=str(d / sl['image']), seconds=6, aspect=aspect)
                print(f'  slide {i}: {clip_path(d, sl).name} (Grok, {aspect})')
                break
            except SystemExit as e:
                print(f'  slide {i}: clip {aspect} refused ({str(e)[:80]})')


def localise(page, comp):
    """Copy every file:// asset into the composition so the render never depends on paths outside it."""
    (comp / 'assets').mkdir(parents=True, exist_ok=True)
    seen = {}

    def sub(m):
        src = Path(m.group(1).replace('%20', ' ').replace('%5B', '[').replace('%5D', ']'))
        if src not in seen and src.exists():
            dst = comp / 'assets' / f'{len(seen)}{src.suffix}'
            shutil.copy(src, dst)
            seen[src] = f'assets/{dst.name}'
        return seen.get(src, m.group(0))
    return re.sub(r'file://([^)"\'\s]+)', sub, page)


def dur(path):
    r = subprocess.run([shutil.which('ffprobe') or 'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def as_video(sec, clip, seconds):
    """Swap the slide's still photo for its Grok clip, slowed to fill the slide (slow motion reads as film)."""
    m = re.search(r'<div class="bg[^"]*" style="background-image:url\(([^)]+)\);background-position:([^"]+)"></div>', sec)
    if not m:
        return sec
    rate = max(.5, min(1.0, round(dur(clip) / seconds, 3)))
    vid = (f'<video id="bgclip" class="bg" src="{clip.as_uri()}" muted playsinline data-start="0" data-duration="{seconds}" '
           f'data-playback-rate="{rate}" style="width:100%;height:100%;object-fit:cover;object-position:{m.group(2)}"></video>')
    sec = sec.replace(m.group(0), vid)
    return re.sub(r'<div class="cut"[^>]*></div>', '', sec)   # a still cut-out would ghost over a moving subject


def motion(d, page_html, car, W, H, seconds, forced=None):
    out = d / 'out' / 'motion'
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('*.mp4'):
        old.unlink()
    gsap = ROOT / 'graphics' / 'node_modules' / 'gsap' / 'dist' / 'gsap.min.js'
    head, body = page_html.split('<body>', 1)
    sections = re.findall(r'<section class="s .*?</section>', body, re.S)
    for i, sl in enumerate(car['slides'], 1):
        style = style_of(car, sl, forced)
        comp = d / 'motion' / f'{i:02d}'
        if comp.exists():
            shutil.rmtree(comp)
        comp.mkdir(parents=True)
        shutil.copy(gsap, comp / 'gsap.min.js')
        name = f'slide{i:02d}'
        sec = sections[i - 1]
        if style == 'cinemagraph':
            if sl.get('image') and clip_path(d, sl).exists():
                sec = as_video(sec, clip_path(d, sl), seconds)
            else:
                print(f'  slide {i}: no Grok clip yet (carousel.py generate --clips), using push')
                style = 'push'
        html = (head.replace('<head>', '<head><script src="gsap.min.js"></script>') +
                f'<body><div id="root" data-composition-id="{name}" data-start="0" data-duration="{seconds}" '
                f'data-width="{W}" data-height="{H}" style="width:{W}px;height:{H}px;overflow:hidden">{sec}</div>'
                f'<script>{anim(style, seconds, name)}</script></body></html>')
        (comp / 'index.html').write_text(localise(html, comp))
        r = subprocess.run([shutil.which('npx'), '--yes', HF, 'render', '.', '--fps', '30', '--format', 'mp4', '--quality', 'high',
                            '--workers', '2', '-o', str(out / f'{i:02d}.mp4'), '--quiet'], cwd=comp, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'slide {i} motion render failed:\n{(r.stdout + r.stderr)[-1500:]}')
        print(f'  slide {i} ({style}) → out/motion/{i:02d}.mp4')
    return out


def reel(d, n, per, music):
    clips = sorted((d / 'out' / 'motion').glob('*.mp4'))
    if not clips:
        sys.exit('run carousel.py motion first')
    out = d / 'out' / 'reel.mp4'
    ins, fc = [], []
    for k, c in enumerate(clips):
        ins += ['-i', str(c)]
        # the 4:5 slide floats over a blurred, darkened copy of itself in 9:16
        fc.append(f'[{k}:v]trim=0:{per},setpts=PTS-STARTPTS,split[a{k}][b{k}];'
                  f'[a{k}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2,eq=brightness=-.18[bg{k}];'
                  f'[b{k}]scale=1080:-2[fg{k}];[bg{k}][fg{k}]overlay=0:(H-h)/2,fps=30[v{k}]')
    fc.append(''.join(f'[v{k}]' for k in range(len(clips))) + f'concat=n={len(clips)}:v=1:a=0[v]')
    tmp = d / 'out' / 'reel-silent.mp4'
    subprocess.run([FF, '-y', '-v', 'error', *ins, '-filter_complex', ';'.join(fc), '-map', '[v]', '-c:v', 'libx264', '-crf', '17',
                    '-pix_fmt', 'yuv420p', str(tmp)], check=True)
    sfx = [{'file': 'whoosh-short', 'at': max(0, k * per - .1), 'db': -20} for k in range(1, len(clips))]
    sfx += [{'file': 'impact-bass-1', 'at': 0.0, 'db': -16}, {'file': 'chime', 'at': len(clips) * per - .6, 'db': -20}]
    (d / 'out' / 'reel-sfx.json').write_text(json.dumps(sfx))
    # silent bed so mixdown has a voice track to sit on
    sil = d / 'out' / 'reel-sil.wav'
    subprocess.run([FF, '-y', '-v', 'error', '-f', 'lavfi', '-i', f'anullsrc=r=48000:cl=stereo', '-t', f'{len(clips) * per:.2f}', str(sil)], check=True)
    vid = d / 'out' / 'reel-base.mov'
    subprocess.run([FF, '-y', '-v', 'error', '-i', str(tmp), '-i', str(sil), '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le',
                    '-shortest', str(vid)], check=True)
    mix = d / 'out' / 'reel-mix.wav'
    subprocess.run([sys.executable, str(Path(__file__).parent / 'mixdown.py'), str(vid), str(music) if music else 'none',
                    str(d / 'out' / 'reel-sfx.json'), str(mix), '--music-db', '-6', '--duck', '1'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([FF, '-y', '-v', 'error', '-i', str(tmp), '-i', str(mix), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', 'loudnorm=I=-14:TP=-1.5', '-c:a', 'aac', '-b:a', '256k', '-shortest', str(out)], check=True)
    for f in (tmp, sil, vid, mix):
        f.unlink(missing_ok=True)
    print(f'reel → {out}')
