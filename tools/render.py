#!/usr/bin/env python3
"""Render an edit plan to a finished, platform-ready MP4.

usage: render.py <edit-plan.json> [out.mp4] [--no-captions] [--draft]

One pass does: per-segment static crop + scale, click-free audio joins, explainer graphics OVERLAID on the
continuous cut (the footage and voice never stop underneath), optional live face card on a graphic, a soft
whoosh under each graphic entrance, burned-in captions (captions.ass next to the plan), then a two-pass
loudness master to -14 LUFS with true peak at or below -1 dBTP.

Plan graphics entries: {"file": "graphics/<name>/renders/<name>.mp4", "at": 2.3,
                        "face_card": {"x": 1180, "y": 220, "w": 560, "h": 640, "r": 28},
                        "sfx": true}
  file is relative to the project folder; the graphic must be rendered at the plan's canvas size.
  face_card: the live footage (same moment, never paused) in a rounded card on top of the graphic. "src": "auto"
  (default) centres it on the speaker's face; or give [x, y] = top-left of the crop in the finished frame.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import FONTS, die, ffmpeg, has_libass, probe, run  # noqa: E402

TARGET_LUFS, TARGET_TP = -14.0, -1.0


def loudness(path):
    err = subprocess.run([ffmpeg(), '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true',
                          '-f', 'null', '-'], capture_output=True, text=True).stderr
    summary = err[err.rfind('Summary:'):]
    i = re.search(r'I:\s+(-?[\d.]+) LUFS', summary)
    tp = re.search(r'Peak:\s+(-?[\d.]+) dBFS', summary)
    return (float(i.group(1)) if i else None), (float(tp.group(1)) if tp else None)


def master(pic, out):
    """Two-pass loudnorm to -14 LUFS / -1.5 dBTP, AAC; re-measure and pull down if the AAC peaks over -1."""
    meas = subprocess.run([ffmpeg(), '-hide_banner', '-nostats', '-i', str(pic), '-af',
                           f'loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                          capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rfind('{'):meas.rfind('}') + 1])
    gain = 0.0
    for _ in range(3):
        af = (f'loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:'
              f'measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:'
              f'linear=true,aresample=48000,volume={gain}dB')
        run([ffmpeg(), '-y', '-v', 'error', '-i', pic, '-c:v', 'copy', '-af', af, '-c:a', 'aac', '-b:a', '256k',
             '-movflags', '+faststart', out])
        lufs, tp = loudness(out)
        if tp is None or tp <= TARGET_TP:
            return lufs, tp
        gain -= (tp - TARGET_TP) + 0.2
    return lufs, tp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--no-captions', action='store_true')
    ap.add_argument('--draft', action='store_true', help='fast preview: lower quality, no mastering')
    a = ap.parse_args()
    plan_path = Path(a.plan).resolve()
    d = json.loads(plan_path.read_text())
    project = plan_path.parent.parent
    out = Path(a.out) if a.out else plan_path.parent / 'exports' / f'{d["id"]}{"-draft" if a.draft else ""}.mp4'
    out.parent.mkdir(parents=True, exist_ok=True)
    info = probe(d['segments'][0]['source'])
    W, H, fps = d['canvas']['width'], d['canvas']['height'], d['canvas'].get('fps', 30)
    ass = plan_path.parent / 'captions.ass'
    use_caps = not a.no_captions and ass.exists()
    if use_caps and not has_libass():
        die('this ffmpeg cannot burn captions (no libass). Run setup again; on Mac it installs ffmpeg-full.')

    ins, fc = [], []
    for i, s in enumerate(d['segments']):
        du = s['out'] - s['in']
        ins += ['-ss', f'{s["in"]:.3f}', '-t', f'{du:.3f}', '-i', s['source']]   # each segment from its own take
        c = s.get('crop') or {'x': 0, 'y': 0, 'w': info['width'], 'h': info['height']}
        lut = f"lut3d='{project / d['lut']}'," if d.get('lut') else ''
        fc.append(f'[{i}:v]{lut}crop={c["w"]}:{c["h"]}:{c["x"]}:{c["y"]},scale={W}:{H}:flags=lanczos,'
                  f'unsharp=5:5:0.4,setsar=1,fps={fps}[v{i}]')
        fc.append(f'[{i}:a]aresample=48000,afade=t=in:d=0.012,afade=t=out:st={du - 0.015:.4f}:d=0.015[a{i}]')
    n = len(d['segments'])
    fc.append(''.join(f'[v{i}][a{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=1[vc][ac]')
    total = sum(s['out'] - s['in'] for s in d['segments'])

    gfx = d.get('graphics', [])
    nin = n
    base = 'vc'
    cards = [k for k, g in enumerate(gfx) if g.get('face_card')]
    if cards:
        fc.append(f'[vc]split={len(cards) + 1}[vbase]' + ''.join(f'[vs{k}]' for k in cards))
        base = 'vbase'
    td_obj = tempfile.TemporaryDirectory()
    td = Path(td_obj.name)
    sfx_inputs = []
    for k, g in enumerate(gfx):
        gpath = project / g['file'] if not Path(g['file']).is_absolute() else Path(g['file'])
        if not gpath.exists():
            die(f'graphic {gpath} not rendered yet')
        gdur = probe(gpath)['duration']
        t0 = float(g['at'])
        ins += ['-i', str(gpath)]
        gi = nin
        nin += 1
        fade = f'fade=t=in:st={t0}:d=0.2:alpha=1,fade=t=out:st={t0 + gdur - 0.2:.3f}:d=0.2:alpha=1'
        fc.append(f'[{gi}:v]scale={W}:{H},fps={fps},setpts=PTS-STARTPTS+{t0}/TB,format=gbrap,{fade}[g{k}]')
        fc.append(f'[{base}]format=gbrp[b{k}];[b{k}][g{k}]overlay=0:0:eof_action=pass:format=gbrp[o{k}]')
        base = f'o{k}'
        fs = g.get('face_card')
        if fs:
            from PIL import Image, ImageDraw
            mask = td / f'mask{k}.png'
            im = Image.new('L', (fs['w'], fs['h']), 0)
            ImageDraw.Draw(im).rounded_rectangle([0, 0, fs['w'] - 1, fs['h'] - 1], radius=fs.get('r', 24), fill=255)
            im.save(mask)
            ins += ['-loop', '1', '-t', f'{total:.3f}', '-framerate', str(fps), '-i', str(mask)]
            mi = nin
            nin += 1
            # the region of the live frame shown in the card: a whole head (about 2.3x the face height), scaled to fit
            zoom = 1.0
            if fs.get('src', 'auto') == 'auto' and not any(sg.get('face') for sg in d['segments']):
                fs = {**fs, 'src': 'full'}           # no speaker to centre on (b-roll, generated shots): show the whole shot
            if fs.get('src') == 'full':
                ar = fs['w'] / fs['h']
                rw, rh = (int(H * ar) // 2 * 2, H) if W / H > ar else (W, int(W / ar) // 2 * 2)
                sx, sy = (W - rw) // 2, (H - rh) // 2
            elif fs.get('src', 'auto') == 'auto':      # centre on the speaker's face across the segments it covers
                spans, t = [], 0.0
                for sg in d['segments']:
                    if t < t0 + gdur and t + sg['out'] - sg['in'] > t0 and sg.get('face'):
                        spans.append(sg['face'])
                    t += sg['out'] - sg['in']
                f = ({k_: sum(x[k_] for x in spans) / len(spans) for k_ in ('cx', 'cy', 'h')} if spans
                     else {'cx': W / 2, 'cy': H * 0.35, 'h': fs['h'] * 0.45})
                zoom = min(3.0, max(1.0, f['h'] * 2.3 / fs['h']))
                rw, rh = int(fs['w'] * zoom) // 2 * 2, int(fs['h'] * zoom) // 2 * 2
                sx = int(min(max(0, f['cx'] - rw / 2), W - rw))
                sy = int(min(max(0, f['cy'] - rh * 0.45), H - rh))
            elif fs.get('src') != 'full':
                sx, sy = fs['src']
                rw, rh = fs['w'], fs['h']
            fc.append(f'[vs{k}]crop={rw}:{rh}:{sx}:{sy},scale={fs["w"]}:{fs["h"]},format=gbrap[c{k}];[{mi}:v]format=gray[m{k}];'
                      f'[c{k}][m{k}]alphamerge,{fade}[f{k}]')
            fc.append(f'[{base}][f{k}]overlay={fs["x"]}:{fs["y"]}:eof_action=pass:format=gbrp[p{k}]')
            base = f'p{k}'
        if g.get('sfx', True):
            ins += ['-f', 'lavfi', '-t', '0.6', '-i', 'anoisesrc=c=pink:r=48000:a=0.5']
            si = nin
            nin += 1
            ms = max(0, int((t0 - 0.12) * 1000))
            fc.append(f'[{si}:a]highpass=f=700,lowpass=f=5500,afade=t=in:d=0.22,afade=t=out:st=0.22:d=0.38,'
                      f'volume=-24dB,adelay={ms}|{ms},apad=whole_dur={total:.3f}[x{k}]')
            sfx_inputs.append(f'[x{k}]')
    if sfx_inputs:
        fc.append('[ac]' + ''.join(sfx_inputs) + f'amix=inputs={len(sfx_inputs) + 1}:normalize=0:duration=first[a]')
    else:
        fc.append('[ac]anull[a]')
    if use_caps:
        ass_esc = str(ass).replace('\\', '/').replace(':', '\\:')
        fonts_esc = str(FONTS).replace('\\', '/').replace(':', '\\:')
        fc.append(f"[{base}]ass='{ass_esc}':fontsdir='{fonts_esc}',format=yuv420p[v]")
    else:
        fc.append(f'[{base}]format=yuv420p[v]')

    pic = td / 'pic.mov'
    # the bitrate cap keeps grainy or busy footage at an uploadable size (platforms re-encode above ~20 Mb/s anyway)
    q = (['-crf', '28', '-preset', 'veryfast'] if a.draft
         else ['-crf', '18', '-preset', 'medium', '-maxrate', '16M', '-bufsize', '32M'])
    print(f'rendering {d["id"]}: {n} segments, {len(gfx)} graphics, {total:.1f}s, captions {"on" if use_caps else "off"} …')
    run([ffmpeg(), '-y', '-v', 'error', *ins, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
         '-c:v', 'libx264', *q, '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', pic])
    if a.draft:
        run([ffmpeg(), '-y', '-v', 'error', '-i', pic, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
             '-movflags', '+faststart', out])
        print(f'draft → {out}')
    else:
        lufs, tp = master(pic, out)
        print(f'wrote {out}\n   loudness {lufs} LUFS, true peak {tp} dBTP')
    td_obj.cleanup()


if __name__ == '__main__':
    main()
