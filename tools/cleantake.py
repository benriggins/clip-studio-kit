#!/usr/bin/env python3
"""Clean the audio of a raw take: remove noise and background sound, then voice EQ, gentle levelling, loudness.

    tools/cleantake.py <video-or-audio> [--out file] [--atten N] [--target -16] [--no-eq] [--wav-only]

transcribe.py runs this automatically on every take, so everything downstream (plan, verify, render, qc) works
on clean audio without anyone asking. Run it by hand only to test or to tune one file.

Free and local: DeepFilterNet (a small downloaded binary, ~27 MB) + ffmpeg. The original file is never touched.
The result is the same video (stream copy, rotation kept) with the clean audio swapped in.
render.py still masters the finished cut to -14 LUFS.
"""
import argparse, hashlib, json, platform, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, ffmpeg as ffmpeg_bin, die  # noqa: E402

DFN_VERSION = '0.5.6'
DFN_URLS = {
    ('Darwin', 'arm64'): ('deep-filter-0.5.6-aarch64-apple-darwin',
                          '4601e7f4e4c03e59a4c5b5000216ef3add3e808799cfccd95e14e83ea4611081'),
}
SR = 48000


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def dfn_path():
    p = ROOT / 'bin' / 'deep-filter'
    if p.exists():
        return p
    key = (platform.system(), platform.machine())
    if key not in DFN_URLS:
        die('DeepFilterNet is not packaged for this computer. See https://github.com/Rikorose/DeepFilterNet/releases '
            'and put the binary at bin/deep-filter')
    name, sha = DFN_URLS[key]
    p.parent.mkdir(exist_ok=True)
    print(f'Downloading DeepFilterNet {DFN_VERSION} (free, ~27 MB)…')
    urllib.request.urlretrieve(f'https://github.com/Rikorose/DeepFilterNet/releases/download/v{DFN_VERSION}/{name}', p)
    if hashlib.sha256(p.read_bytes()).hexdigest() != sha:
        p.unlink()
        die('The DeepFilterNet download failed its checksum, so it was not used.')
    p.chmod(0o755)
    run(['xattr', '-d', 'com.apple.quarantine', str(p)])
    return p


def load(path):
    r = subprocess.run([ffmpeg_bin(), '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def stats(path):
    """Loudness (EBU R128) plus noise floor / speech level from 50 ms frames."""
    r = run([ffmpeg_bin(), '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    t = r.stderr[r.stderr.rfind('Summary:'):]
    g = lambda pat: float(re.search(pat, t).group(1))
    x = load(path)
    n = int(.05 * SR); k = len(x) // n
    db = 20 * np.log10(np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1)) + 1e-9)
    nf, sp = float(np.percentile(db, 10)), float(np.percentile(db, 90))
    return dict(lufs=g(r'I:\s+(-?[\d.]+) LUFS'), lra=g(r'LRA:\s+(-?[\d.]+) LU'), tp=g(r'Peak:\s+(-?[\d.]+) dBFS'),
                noise=round(nf, 1), speech=round(sp, 1), snr=round(sp - nf, 1))


def fmt(label, s):
    return (f"{label:7s} {s['lufs']:6.1f} LUFS  LRA {s['lra']:4.1f}  peak {s['tp']:5.1f} dBTP  "
            f"noise {s['noise']:6.1f} dB  SNR {s['snr']:5.1f} dB")


def eq_chain(eq):
    f = ['highpass=f=80']
    if eq:
        f += ['equalizer=f=250:t=q:w=1.0:g=-2',      # phone/room boxiness
              'equalizer=f=3200:t=q:w=0.9:g=2.5',    # presence / intelligibility
              'equalizer=f=7500:t=h:w=1.0:g=1.5']    # a little air; the denoiser leaves the top a touch dull
    f += ['acompressor=threshold=0.063:ratio=2.5:attack=15:release=180:makeup=2']
    return ','.join(f)


def loudnorm_two_pass(src, dst, target, tp=-1.5, lra=8):
    base = f'loudnorm=I={target}:TP={tp}:LRA={lra}'
    r = run([ffmpeg_bin(), '-hide_banner', '-nostats', '-i', str(src), '-af', base + ':print_format=json', '-f', 'null', '-'])
    j = json.loads(r.stderr[r.stderr.rfind('{'):r.stderr.rfind('}') + 1])
    af = (f"{base}:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    r = run([ffmpeg_bin(), '-y', '-v', 'error', '-i', str(src), '-af', af, '-ar', str(SR), '-c:a', 'pcm_s24le', str(dst)])
    if r.returncode:
        die('loudness pass failed: ' + r.stderr[-300:])


def clean(src, out, atten=None, target=-16.0, eq=True, wav_only=False):
    """Write a clean copy of src to out. Returns (before, after) stats. Safe to call from other tools."""
    src, out = Path(src), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_bin()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        raw = td / 'raw.wav'
        # first audio stream only (iPhone files also carry a 4-channel spatial track ffmpeg can't decode)
        r = run([ff, '-y', '-v', 'error', '-i', str(src), '-map', '0:a:0', '-ac', '1', '-ar', str(SR),
                 '-c:a', 'pcm_f32le', str(raw)])
        if r.returncode:
            die(f'could not read the audio of {src.name}: ' + r.stderr[-300:])
        dn = td / 'dfn'; dn.mkdir()
        cmd = [str(dfn_path()), '-o', str(dn), str(raw)]
        if atten is not None:
            cmd[1:1] = ['-a', str(atten)]
        r = run(cmd)
        if r.returncode or not (dn / 'raw.wav').exists():
            die('noise removal failed: ' + (r.stderr or r.stdout)[-300:])
        eqd = td / 'eq.wav'
        r = run([ff, '-y', '-v', 'error', '-i', str(dn / 'raw.wav'), '-af', eq_chain(eq), '-c:a', 'pcm_f32le', str(eqd)])
        if r.returncode:
            die('EQ/levelling failed: ' + r.stderr[-300:])
        wav = td / 'final.wav'
        loudnorm_two_pass(eqd, wav, target)
        before, after = stats(raw), stats(wav)
        if wav_only:
            wav.replace(out)
        else:
            # keep the original video stream and its metadata (rotation); swap in the clean audio
            r = run([ff, '-y', '-v', 'error', '-i', str(src), '-i', str(wav), '-map', '0:v:0', '-map', '1:a:0',
                     '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', str(SR), '-movflags', '+faststart', str(out)])
            if r.returncode:
                die('could not write the clean video: ' + r.stderr[-300:])
    return before, after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out')
    ap.add_argument('--atten', type=float, default=None,
                    help='cap noise removal at N dB (e.g. 18) for a more natural room; default is full')
    ap.add_argument('--target', type=float, default=-16.0, help='LUFS of the clean take (render.py masters the cut to -14)')
    ap.add_argument('--no-eq', action='store_true')
    ap.add_argument('--wav-only', action='store_true')
    a = ap.parse_args()
    src = Path(a.src).expanduser().resolve()
    if not src.exists():
        die(f'{src} not found')
    out = Path(a.out).expanduser() if a.out else ROOT / 'inbox' / f'{src.stem}-clean{".wav" if a.wav_only else src.suffix}'
    print('Removing noise and background sound…')
    before, after = clean(src, out, a.atten, a.target, not a.no_eq, a.wav_only)
    print(fmt('before', before)); print(fmt('after', after)); print(f'→ {out}')


if __name__ == '__main__':
    main()
