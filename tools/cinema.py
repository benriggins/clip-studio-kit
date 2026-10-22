#!/usr/bin/env python3
"""ONE COMMAND: ChatGPT CLIP_PLAN (with a "cinema" block, see chatgpt-project/10) -> finished business-cinema reel.

usage: tools/cinema.py <projects/P/chatgpt/plan.json> [--only CLIP_ID] [--speed 1.10] [--music-db -3.5]

Per clip: plan.py (exact words, silence-snapped cuts) -> graded footage + portrait-safe wide/tight crops ->
B-roll (GPT Image 2.5 still -> Grok Imagine 1.5 -> trim/grade/push) -> glass UI + big words (sovpack) -> big words
BEHIND his head (depth.py) -> sound cues + UI pops (mixdown.py) -> cinema captions -> render -> speed-up ->
music bed under the voice -> -14 LUFS master -> exports/<clip>-final.mp4 + a contact sheet.
Everything generated is cached by file name, so a re-run only redoes what changed.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

T = Path(__file__).resolve().parent
ROOT = T.parent
sys.path.insert(0, str(T))
from _common import norm, probe  # noqa: E402
from captions import cut_words  # noqa: E402
import motionpack  # noqa: E402
import platform  # noqa: E402

PY = str(ROOT / '.venv' / 'bin' / 'python')
from _common import ffmpeg  # noqa: E402
FF = ffmpeg()
SYS_PY = PY
CUE = {'hit': ('impact-bass-1', -15), 'ping': ('ping', -20), 'whoosh': ('whoosh-cinematic', -18), 'tap': ('click-soft', -21),
       'chime': ('chime', -20), 'pop': ('pop', -22), 'notification': ('notification', -21), 'riser': ('riser', -24)}


def run(cmd, **kw):
    subprocess.run([str(c) for c in cmd], check=True, **kw)


class Words:
    def __init__(self, plan, project):
        takes = {s.get('take', 'V1') for s in plan['segments']}
        self.w = cut_words(plan, {t: json.loads((project / 'transcript' / t / 'words.json').read_text()) for t in takes})
        self.n = [norm(x['w']) for x in self.w]
        self.end = self.w[-1]['e']

    def find(self, text, after=0.0):
        want = [norm(x) for x in text.split() if norm(x)]
        for i in range(len(self.n) - len(want) + 1):
            if self.n[i:i + len(want)] == want and self.w[i]['s'] >= after - 0.01:
                return self.w[i]['s'], self.w[i + len(want) - 1]['e']
        for i, x in enumerate(self.n):            # fall back to the first word
            if want and x == want[0] and self.w[i]['s'] >= after - 0.01:
                return self.w[i]['s'], self.w[i]['e']
        raise SystemExit(f'words not found in the cut: "{text}"')


def portrait_crops(plan, graded):
    for k, s in enumerate(plan['segments']):
        if graded and graded.exists():
            s['source'] = str(graded)
        info = probe(s['source'])
        w, h = info['width'], info['height']
        if info.get('rotation') in (90, -90, 270, -270):
            w, h = h, w
        if h > w:                               # portrait phone footage: full frame / tight, never a sideways crop
            s['crop'] = ({'x': 0, 'y': 0, 'w': w, 'h': h, 'preset': 'wide'} if k % 2 == 0 else
                         {'x': int(w * .1), 'y': int(h * .07), 'w': int(w * .83), 'h': int(h * .83), 'preset': 'tight'})


def gen_broll(project, cid, cin):
    def shot(i, b):
        still, vid = project / f'broll/{cid}-b{i}-still.png', project / f'broll/{cid}-b{i}-grok.mp4'
        if not still.exists():
            run([PY, T / 'kie.py', 'image', b['still'], still, '--aspect', '9:16'], capture_output=True)
        if not vid.exists():
            run([PY, T / 'kie.py', 'video', b['motion'], vid, '--image', still, '--seconds', 5], capture_output=True)
        return vid

    def music():
        out = project / f'audio/{cid}-music.mp3'
        if not out.exists() and cin.get('music'):
            import produce
            shutil.copy(produce.music(cin['music'], 50), out)
        return out
    (project / 'broll').mkdir(exist_ok=True)
    (project / 'audio').mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        shots = [ex.submit(shot, i, b) for i, b in enumerate(cin.get('broll', []))]
        mus = ex.submit(music)
        return [s.result() for s in shots], mus.result()


def ui_graphics(cid, ui, words):
    """Turn the plan's ui[] into sovpack graphics placed on the cut clock: [(at, layer, graphic spec)]."""
    out = []
    for k, u in enumerate(ui):
        name, kind = f'{cid[:24]}-u{k}', u['kind']
        first = u.get('on_text') or next((c.get('on_text') for c in (u.get('chips') or u.get('items') or []) if c.get('on_text')), None)
        if not first:
            print(f'  · ui {k} has no on_text, skipped')
            continue
        s, e = words.find(first)
        if kind == 'timer':
            at = max(0.0, s - 0.05)
            g = {'duration': 2.5, 'parts': [{'kind': 'timer', 'at': 0.02, 'pos': {'left': 60, 'top': 210}, 'label': u.get('label', ''),
                                              'count': [0.15, max(0.9, e - at)], 'out': 2.0}]}
            layer = 'front'
        elif kind == 'bigword':
            at = max(0.0, s - 0.15)
            size = min(250, int(1750 / max(4, len(u['word']))))
            g = {'duration': 2.3, 'parts': [{'kind': 'bigword', 'word': u['word'], 'at': 0.05, 'out': 1.75, 'top': 160, 'size': size}]}
            layer = 'back'
        elif kind == 'check':
            times = [words.find(c['on_text'], s - 1) for c in u['chips']]
            at = max(0.0, times[0][0] - 0.55)
            out_t = times[-1][1] - at + 0.9
            g = {'duration': out_t + 0.55, 'parts': [{'kind': 'check', 'at': 0.0, 'top': 140, 'eyebrow': u.get('eyebrow', ''),
                 'title': u.get('title', ''), 'out': out_t,
                 'chips': [{'label': c.get('label') or c.get('text'), 'at': t[0] - at} for c, t in zip(u['chips'], times)]}]}
            layer = 'front'
        elif kind == 'person':
            at = max(0.0, s - 0.25)
            dur = max(1.5, words.end - at + 0.2)
            g = {'duration': dur, 'parts': [{'kind': 'person', 'at': 0.0, 'top': 140, 'eyebrow': u.get('eyebrow', ''),
                 'title': u.get('title', ''), **({'dm_at': min(0.9, dur - 0.6), 'dm_offset': 330} if u.get('dm', True) else {})}]}
            layer = 'front'
        elif kind in ('cards', 'fan'):
            items = u.get('items') or [{'label': x} for x in u.get('labels', [])]
            at = max(0.0, s - 0.3)
            out_t = (words.find(u['out_text'], s)[0] - at) if u.get('out_text') else 3.0
            if kind == 'fan':
                spots = [({'left': -40, 'top': 330}, -16), ({'right': -60, 'top': 480}, 14), ({'left': -80, 'top': 770}, 12), ({'right': -40, 'top': 940}, -12)]
                part = {'kind': 'fan', 'at': 0.1, 'out': out_t, 'cards': [{'label': it.get('label') or it.get('title'), 'sub': 'Tool',
                        'rot': spots[i % 4][1], 'pos': spots[i % 4][0], 'progress': .55 + .1 * (i % 3)} for i, it in enumerate(items)]}
                layer = 'back'
            else:
                spots = [({'left': 30, 'top': 300}, [6, 18, -7]), ({'right': 40, 'top': 470}, [6, -18, 6]),
                         ({'left': 50, 'top': 1120}, [-6, 14, 4]), ({'right': 50, 'top': 1260}, [-6, -14, -4])]
                part = {'kind': 'cards', 'strike': u.get('strike', False), 'out': out_t, 'cards': [
                    {'title': it.get('title') or it.get('label'), 'icon': it.get('icon', 'plane'),
                     'at': (words.find(it['on_text'], s - 1)[0] - at - 0.15) if it.get('on_text') else 0.2 + .3 * i,
                     'pos': spots[i % 4][0], 'tilt': spots[i % 4][1], **({'layer': 'back'} if it.get('layer') == 'back' else {})}
                    for i, it in enumerate(items)]}
                layer = 'mixed'
            g = {'duration': out_t + 0.6, 'parts': [part]}
        else:
            print(f'  · skipping unknown ui kind "{kind}"')
            continue
        g['name'] = name
        out.append((at, layer, g))
    return out


def build_graphic(project, g):
    d = project / 'graphics' / g['name']
    stamp = hashlib.sha1(json.dumps(g, sort_keys=True).encode()).hexdigest()[:12]
    if (d / '.spec').exists() and (d / '.spec').read_text() == stamp:
        return d
    motionpack.build(project.name, g)
    (d / '.spec').write_text(stamp)
    return d


def write_plan(base, path, **over):
    p = {**base, **over}
    path.write_text(json.dumps(p, indent=2))
    return path


def render(plan_path, captions=True):
    run([PY, ROOT / 'tools/render.py', plan_path] + ([] if captions else ['--no-captions']), cwd=ROOT,
        stdout=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--only')
    ap.add_argument('--speed', type=float, default=1.10)
    ap.add_argument('--music-db', type=float, default=-3.5)
    a = ap.parse_args()
    plan_path = Path(a.plan).resolve()
    project = plan_path.parent.parent
    clips = json.loads(plan_path.read_text())['clips']
    for clip in clips:
        cid = clip['id']
        if a.only and cid != a.only:
            continue
        cin = clip.get('cinema', {})
        print(f'▶ {cid}')
        run([PY, ROOT / 'tools/plan.py', plan_path, '--only', cid], cwd=ROOT, stdout=subprocess.DEVNULL)
        cdir = project / cid
        ep = json.loads((cdir / 'edit-plan.json').read_text())
        grade = project / 'takes' / 'grade.txt'
        if not grade.exists():
            shutil.copy(T / 'grade-filmic.txt', grade)
        graded = {}
        for s in ep['segments']:                  # grade each take once (cached), then cut from the graded copy
            src = Path(s['source'])
            g = project / 'takes' / f'{src.stem.replace("-clean", "")}-graded.mp4'
            if not g.exists():
                print(f'  grading {src.name} (once)')
                run([FF, '-y', '-v', 'error', '-i', src, '-map', '0:v:0', '-map', '0:a:0', '-vf', grade.read_text().strip(),
                     '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 16, '-pix_fmt', 'yuv420p', '-c:a', 'copy', g])
            graded[str(src)] = g
        portrait_crops(ep, None)
        for s in ep['segments']:
            s['source'] = str(graded.get(s['source'], s['source']))
        (cdir / 'edit-plan.json').write_text(json.dumps(ep, indent=2))
        words = Words(ep, project)
        exp = cdir / 'exports'
        exp.mkdir(exist_ok=True)

        print('  generating b-roll + music (cached)')
        shots, music = gen_broll(project, cid, cin)

        graphics_front, graphics_back, sfx, windows = [], [], [], []
        taken = []
        for i, (b, src) in enumerate(zip(cin.get('broll', []), shots)):
            s, _ = words.find(b['on_text'])
            at = max(0.0, s - 0.05)
            dur = float(b.get('seconds', 2.2))
            nxt = [t for t in taken if t > at]
            dur = min(dur, (min(nxt) - at - 0.1) if nxt else dur)
            fx = project / f'broll/{cid}-b{i}-fx.mp4'
            focus = b.get('focus', '0.5,0.5')
            focus = focus if ',' in focus and all(c in '0123456789., ' for c in focus) else '0.5,0.5'
            run([SYS_PY, T / 'broll_fx.py', src, fx, '--start', 0.4, '--dur', f'{dur:.2f}', '--push', 1.12, '--focus', focus]
                + (['--grade', grade] if grade.exists() else []), stdout=subprocess.DEVNULL)
            graphics_front.append({'file': str(fx), 'at': round(at, 3), 'sfx': False})
            sfx += [{'file': 'whoosh-cinematic', 'at': max(0, at - 0.08), 'db': -19}, {'file': 'whoosh-short', 'at': at + dur - 0.1, 'db': -22}]
            taken.append(at)

        for at, layer, g in ui_graphics(cid, cin.get('ui', []), words):
            d = build_graphic(project, g)
            front, back = d / 'renders' / f'{g["name"]}.mov', d / 'renders' / f'{g["name"]}-back.mov'
            if front.exists() and layer != 'back':
                graphics_front.append({'file': str(front), 'at': round(at, 3), 'sfx': False})
            if back.exists() and layer != 'front':
                graphics_back.append({'file': str(back), 'at': round(at, 3), 'sfx': False})
                windows.append((round(at, 3), round(at + g['duration'], 3)))
            sfx.append({'file': 'whoosh-short' if layer == 'back' else 'pop', 'at': at + 0.05, 'db': -22})

        for c in cin.get('sound', []):
            f, db = CUE.get(c.get('cue'), CUE['pop'])
            sfx.append({'file': f, 'at': max(0.0, words.find(c['on_text'])[0] - (0.04 if c.get('cue') == 'hit' else 0)), 'db': db})
        sfx.append({'file': 'chime', 'at': max(0.0, words.end - 0.35), 'db': -21})
        (cdir / 'sfx.json').write_text(json.dumps(sfx, indent=0))

        print(f'  rendering passes ({len(graphics_front)} front, {len(graphics_back)} behind-head)')
        run([PY, ROOT / 'tools/captions.py', cdir / 'edit-plan.json'], cwd=ROOT, stdout=subprocess.DEVNULL)
        base = write_plan(ep, cdir / 'pass-base.json', id=f'{cid}-base', graphics=[])
        render(base, captions=False)
        video = exp / f'{cid}-base.mp4'
        if graphics_back and platform.system() != 'Darwin':   # the cut-out needs Apple Vision: elsewhere, back cards go on top
            graphics_front += graphics_back
            graphics_back = []
        if graphics_back:
            back = write_plan(ep, cdir / 'pass-back.json', id=f'{cid}-back', graphics=graphics_back)
            render(back, captions=False)
            wargs = sum([['--window', a_, b_] for a_, b_ in windows], [])
            run(['uv', 'run', '-q', '--with', 'pyobjc-framework-Vision', '--with', 'pyobjc-framework-Quartz', 'python',
                 T / 'depth.py', exp / f'{cid}-back.mp4', video, exp / f'{cid}-depth.mp4', *wargs], stdout=subprocess.DEVNULL)
            video = exp / f'{cid}-depth.mp4'
        run([SYS_PY, T / 'mixdown.py', video, 'none', cdir / 'sfx.json', exp / 'vo-sfx.wav'], stdout=subprocess.DEVNULL)
        comp = exp / f'{cid}-comp.mov'
        run([FF, '-y', '-v', 'error', '-i', video, '-i', exp / 'vo-sfx.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le', comp])
        dur = probe(comp)['duration']
        final = write_plan({k: v for k, v in ep.items() if k not in ('segments', 'graphics')}, cdir / 'pass-final.json',
                           id=f'{cid}-cut', segments=[{'id': 'S1', 'take': 'V1', 'source': str(comp), 'role': 'ALL', 'in': 0.0,
                           'out': round(dur - 0.04, 3), 'text': '', 'crop': {'x': 0, 'y': 0, 'w': 1080, 'h': 1920, 'preset': 'wide'},
                           'face': None}], graphics=graphics_front)
        render(final)

        print(f'  speed x{a.speed}, music, master')
        cut, fast = exp / f'{cid}-cut.mp4', exp / f'{cid}-fast.mov'
        run([FF, '-y', '-v', 'error', '-i', cut, '-filter_complex', f'[0:v]setpts=PTS/{a.speed},fps=30[v];[0:a]atempo={a.speed}[a]',
             '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', 16, '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', fast])
        mix = exp / 'final-mix.wav'
        (exp / 'nosfx.json').write_text('[]')
        run([SYS_PY, T / 'mixdown.py', fast, music if music and music.exists() else 'none', exp / 'nosfx.json', mix,
             '--music-db', a.music_db, '--duck', 2], stdout=subprocess.DEVNULL)
        out = exp / f'{cid}-final.mp4'
        run([FF, '-y', '-v', 'error', '-i', fast, '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
             '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', 48000, '-c:a', 'aac', '-b:a', '256k', out])
        # contact sheet for the frame check
        d = probe(out)['duration']
        sheet = exp / f'{cid}-sheet.jpg'
        run([FF, '-y', '-v', 'error', '-i', out, '-vf', f'fps=8/{d:.2f},scale=240:-1,tile=8x1', '-frames:v', 1, sheet])
        print(f'✓ {out} ({d:.1f}s)\n  sheet: {sheet}')


if __name__ == '__main__':
    main()
