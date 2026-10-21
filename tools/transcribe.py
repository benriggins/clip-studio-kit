#!/usr/bin/env python3
"""Transcribe one video or several takes, with word-level timing (faster-whisper: free, runs on your computer).

usage: transcribe.py <media> [<media> ...] --project NAME [--model small.en] [--language en] [--raw]

Every file becomes a TAKE: V1, V2, V3 … in the order given (re-running adds new files as the next take numbers).
Every take is CLEANED first (noise and background sound removed, voice levelled: tools/cleantake.py), and the clean
copy in projects/NAME/takes/ is what every later tool cuts from. The original is never touched. --raw skips this.
Writes into projects/NAME/transcript/:
  transcript.txt       ALL takes in one file, each under a "VIDEO n" heading, every line timecoded.
                       Upload THIS file to ChatGPT.
  V1/words.json …      every word of each take with start/end seconds (the editor cuts on these)
  V1/transcript.srt …  standard subtitles per take
  ../takes.json        V1 -> file path, duration (the editor reads this to find each take's media)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, brand, die, fmt, pcm, probe, slug  # noqa: E402

MAX_WORDS = 22      # long sentences get split so every line has a usable timecode
GAP_BREAK = 0.8     # a pause this long starts a new line


def sentences(words):
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end = w['w'].rstrip().endswith(('.', '?', '!'))
        gap = nxt and nxt['s'] - w['e'] > GAP_BREAK
        if nxt is None or end or gap or len(cur) >= MAX_WORDS:
            lines.append(cur)
            cur = []
    return lines


def srt_time(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}'


def transcribe_one(model, media, language):
    # decode with our own ffmpeg and hand faster-whisper the samples: its bundled PyAV decoder breaks across versions
    audio = pcm(media)
    segs, _ = model.transcribe(audio, language=None if language == 'auto' else language,
                               word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
    words = []
    for seg in segs:
        for w in seg.words or []:
            txt = w.word.strip()
            if txt:
                words.append({'w': txt, 's': round(w.start, 3), 'e': round(w.end, 3)})
        if words:
            print(f'    … {fmt(words[-1]["e"], ms=False)}', end='\r', flush=True)
    print()
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('media', nargs='+')
    ap.add_argument('--project')
    ap.add_argument('--model')
    ap.add_argument('--language')
    ap.add_argument('--raw', action='store_true', help='skip the audio clean-up (already-clean studio audio)')
    a = ap.parse_args()
    files = [Path(m).resolve() for m in a.media]
    for f in files:
        if not f.exists():
            die(f'{f} not found')
    try:
        cfg = brand().get('transcription', {})
    except SystemExit:
        cfg = {}
    model_name = a.model or cfg.get('model', 'small.en')
    language = a.language or cfg.get('language', 'en')
    project = ROOT / 'projects' / (a.project or slug(files[0].stem))
    tdir = project / 'transcript'
    tdir.mkdir(parents=True, exist_ok=True)
    takes_f = project / 'takes.json'
    takes = json.loads(takes_f.read_text()) if takes_f.exists() else {}
    known = {}
    for k, v in takes.items():
        known[v['file']] = k
        known[v.get('original', v['file'])] = k
    acfg = {}
    try:
        acfg = brand().get('audio', {})
    except SystemExit:
        pass
    do_clean = not a.raw and acfg.get('clean', True)

    from faster_whisper import WhisperModel
    model = None
    for orig in files:
        f = orig
        if str(orig) in known and (tdir / known[str(orig)] / 'words.json').exists():
            print(f'{known[str(orig)]} {orig.name}: already transcribed')
            continue
        if do_clean:
            f = project / 'takes' / f'{orig.stem}-clean{orig.suffix}'
            if not f.exists() or f.stat().st_mtime < orig.stat().st_mtime:
                print(f'{orig.name}: removing noise and background sound …')
                import cleantake
                before, after = cleantake.clean(orig, f, atten=acfg.get('atten'), target=acfg.get('take_lufs', -16.0))
                print('  ' + cleantake.fmt('before', before) + '\n  ' + cleantake.fmt('after', after))
        tid = known.get(str(orig)) or f'V{len(takes) + 1}'
        info = probe(f)
        print(f'{tid} {f.name} ({fmt(info["duration"], ms=False)}) with {model_name} '
              f'(the first run downloads the model) …')
        model = model or WhisperModel(model_name, device='auto', compute_type='int8')
        words = transcribe_one(model, f, language)
        if not words:
            print(f'  {tid}: no speech found, skipped')
            continue
        (tdir / tid).mkdir(exist_ok=True)
        (tdir / tid / 'words.json').write_text(json.dumps(words))
        (tdir / tid / 'transcript.srt').write_text('\n'.join(
            f'{i + 1}\n{srt_time(ln[0]["s"])} --> {srt_time(ln[-1]["e"])}\n' + ' '.join(w['w'] for w in ln) + '\n'
            for i, ln in enumerate(sentences(words))))
        takes[tid] = {'file': str(f), 'name': orig.name, 'original': str(orig), 'duration': round(info['duration'], 2),
                      'width': info['width'], 'height': info['height']}
        takes_f.write_text(json.dumps(takes, indent=1))

    # one combined file for ChatGPT, every take under its own heading
    parts = [f'# Transcript for project "{project.name}": {len(takes)} '
             f'{"take" if len(takes) == 1 else "takes"}\n'
             '# Timecodes are [start → end] in minutes:seconds of THAT take\'s own file.\n'
             '# Refer to a take by its ID (V1, V2 …) in every splice plan.\n']
    for tid in sorted(takes, key=lambda k: int(k[1:])):
        wf = tdir / tid / 'words.json'
        if not wf.exists():
            continue
        words = json.loads(wf.read_text())
        t = takes[tid]
        parts.append(f'\n=== VIDEO {tid[1:]} · {tid} · {t["name"]} · {fmt(t["duration"], ms=False)} ===\n')
        parts.append('\n'.join(f'[{fmt(ln[0]["s"])} → {fmt(ln[-1]["e"])}] ' + ' '.join(w['w'] for w in ln)
                               for ln in sentences(words)) + '\n')
    (tdir / 'transcript.txt').write_text(''.join(parts))
    print(f'\n{len(takes)} take(s) → {tdir / "transcript.txt"}  (upload this file to ChatGPT)')


if __name__ == '__main__':
    main()
