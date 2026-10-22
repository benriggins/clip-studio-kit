#!/usr/bin/env python3
"""Mix a music bed + sound effects under the cut's voice (voice stays on top; music ducks under it).

usage: mixdown.py <video.mp4> <music.mp3|none> <sfx.json> <out.wav> [--music-db -21]

sfx.json: [{"file": "pop", "at": 9.28, "db": -20}, …]  (file = a name in SFX_DIR or a path; "len" trims it)
SFX: your own files in my-studio/sfx/, else the media-use skill set if installed, else rights-free ffmpeg synths.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ffmpeg  # noqa: E402
FF = ffmpeg()
SFX_DIR = Path(__file__).resolve().parent.parent / 'my-studio' / 'sfx'   # drop your own .mp3/.wav here to override
SKILL_SFX = Path('/Users/Shared/Projects/.agents-skills-content/media-use/audio/assets/sfx')
# Rights-free fallbacks synthesised with ffmpeg when no file exists (name -> lavfi source + filter, seconds)
SYNTH = {
    'whoosh': ('anoisesrc=d=0.6:c=pink:r=48000:a=0.6', 'highpass=f=300,lowpass=f=6000,afade=t=in:d=0.18,afade=t=out:st=0.25:d=0.35'),
    'whoosh-short': ('anoisesrc=d=0.35:c=pink:r=48000:a=0.6', 'highpass=f=500,lowpass=f=7000,afade=t=in:d=0.08,afade=t=out:st=0.12:d=0.23'),
    'whoosh-cinematic': ('anoisesrc=d=1.0:c=brown:r=48000:a=0.8', 'highpass=f=120,lowpass=f=4500,afade=t=in:d=0.4,afade=t=out:st=0.5:d=0.5'),
    'pop': ('sine=f=880:d=0.08:r=48000', 'afade=t=out:st=0.02:d=0.06,volume=2'),
    'click-soft': ('sine=f=2200:d=0.04:r=48000', 'afade=t=out:st=0.01:d=0.03'),
    'key-press': ('sine=f=3000:d=0.03:r=48000', 'afade=t=out:st=0.005:d=0.025'),
    'ping': ('sine=f=1760:d=0.5:r=48000', 'afade=t=out:st=0.05:d=0.45'),
    'chime': ('sine=f=1318:d=1.2:r=48000', 'afade=t=out:st=0.1:d=1.1'),
    'notification': ('sine=f=1568:d=0.35:r=48000', 'afade=t=out:st=0.05:d=0.3'),
    'impact-bass-1': ('sine=f=60:d=0.9:r=48000', 'afade=t=out:st=0.05:d=0.85,volume=6'),
    'impact-bass-2': ('sine=f=50:d=1.0:r=48000', 'afade=t=out:st=0.05:d=0.95,volume=6'),
    'riser': ('anoisesrc=d=1.2:c=white:r=48000:a=0.4', 'highpass=f=800,afade=t=in:d=1.1,afade=t=out:st=1.1:d=0.1'),
    'typing': ('anoisesrc=d=1.5:c=white:r=48000:a=0.3', 'highpass=f=2500,apulsator=hz=12,afade=t=out:st=1.3:d=0.2'),
}


def sfx_file(name):
    for d in (SFX_DIR, SKILL_SFX):
        for ext in ('.mp3', '.wav'):
            if (d / f'{name}{ext}').exists():
                return d / f'{name}{ext}'
    cache = Path(__file__).resolve().parent.parent / 'cache' / 'sfx'
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / f'{name}.wav'
    if not out.exists():
        src, flt = SYNTH.get(name, SYNTH['pop'])
        subprocess.run([FF, '-y', '-v', 'error', '-f', 'lavfi', '-i', src, '-af', flt, str(out)], check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('music')
    ap.add_argument('sfx')
    ap.add_argument('out')
    ap.add_argument('--music-db', type=float, default=-21)
    ap.add_argument('--duck', type=float, default=5, help='sidechain ratio; lower keeps the beat audible')
    a = ap.parse_args()
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.video],
                               capture_output=True, text=True).stdout)
    ins, fc, mix = ['-i', a.video], ['[0:a]aresample=48000,asplit=2[voice][key]'], ['[voice]']
    n = 1
    if a.music != 'none':
        ins += ['-i', a.music]
        fc.append(f'[{n}:a]aresample=48000,atrim=0:{dur:.3f},afade=t=in:d=0.6,afade=t=out:st={dur - 1.6:.3f}:d=1.6,'
                  f'volume={a.music_db}dB[mus0]')
        # duck the bed whenever he speaks, recover between phrases
        fc.append(f'[mus0][key]sidechaincompress=threshold=0.05:ratio={a.duck}:attack=20:release=250:makeup=1[mus]')
        mix.append('[mus]')
        n += 1
    else:
        fc[0] = '[0:a]aresample=48000[voice]'
    for k, s in enumerate(json.loads(Path(a.sfx).read_text())):
        f = Path(s['file']) if '/' in s['file'] else sfx_file(s['file'])
        ins += ['-i', str(f)]
        ms = int(s['at'] * 1000)
        trim = f'atrim=0:{s["len"]},afade=t=out:st={max(0, s["len"] - .08):.3f}:d=0.08,' if s.get('len') else ''
        fc.append(f'[{n}:a]aresample=48000,{trim}volume={s.get("db", -20)}dB,adelay={ms}|{ms}[s{k}]')
        mix.append(f'[s{k}]')
        n += 1
    fc.append(f'{"".join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,atrim=0:{dur:.3f}[out]')
    subprocess.run([FF, '-y', '-v', 'error', *ins, '-filter_complex', ';'.join(fc), '-map', '[out]', '-ar', '48000', '-ac', '2',
                    a.out], check=True)
    print(f'mix → {a.out}')


if __name__ == '__main__':
    main()
