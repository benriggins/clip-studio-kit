#!/usr/bin/env python3
"""Prove the cut: re-transcribe the rendered video around every join and compare with the words that should be there.

usage: verify.py <edit-plan.json> [rendered.mp4]      (default: <clip>/exports/<id>.mp4, or the -draft render)

For each join it listens to ±1.6 s and checks: the last word before the cut and the first word after it are both
heard (not clipped), no word from outside the segments leaked in, and nothing is doubled. Whisper sometimes invents
a stray "you" in silence; a leading "you" is called out so you can confirm by ear. Exit code 1 if any join fails.
"""
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import norm, pcm, probe  # noqa: E402
from captions import cut_words  # noqa: E402

PAD = 1.6


def similar(w, pool):
    return any(w == p or difflib.SequenceMatcher(None, w, p).ratio() >= 0.75 for p in pool)


def main(plan_path, media=None):
    plan_path = Path(plan_path).resolve()
    d = json.loads(plan_path.read_text())
    if media is None:
        ex = plan_path.parent / 'exports'
        media = next((p for p in [ex / f'{d["id"]}.mp4', ex / f'{d["id"]}-draft.mp4'] if p.exists()), None)
        if not media:
            print('no render found; run render.py first')
            sys.exit(1)
    from faster_whisper import WhisperModel
    model = WhisperModel('small.en', device='auto', compute_type='int8')
    segs = d['segments']
    project = plan_path.parent.parent
    takes = {s.get('take', 'V1') for s in segs}
    cut = cut_words(d, {t: json.loads((project / 'transcript' / t / 'words.json').read_text()) for t in takes})
    joins, t = [], 0.0
    for k, s in enumerate(segs):
        t += s['out'] - s['in']
        if k < len(segs) - 1:
            joins.append((k, t))
    dur = probe(media)['duration']
    fails = 0
    for k, at in joins:
        a, b = max(0, at - PAD), min(dur, at + PAD)
        got, _ = model.transcribe(pcm(media, a, b - a), language='en', condition_on_previous_text=False)
        heard = [norm(x) for g in got for x in g.text.split() if norm(x)]
        inside = [norm(w['w']) for w in cut if w['s'] >= a + 0.15 and w['e'] <= b - 0.15]
        nearby = [norm(w['w']) for w in cut if w['e'] >= a - 0.3 and w['s'] <= b + 0.3]
        last = norm([w for w in cut if w['seg'] == k][-1]['w'])
        first = norm([w for w in cut if w['seg'] == k + 1][0]['w'])
        missing = [x for x in inside if not similar(x, heard)]
        # the first and last heard words sit on the listening window's edge, half-cut, so they are often misheard
        extra = [x for i, x in enumerate(heard) if 0 < i < len(heard) - 1 and not similar(x, nearby)]
        critical = [x for x in (last, first) if not similar(x, heard)]
        ok = not critical and len(missing) <= 1 and not extra
        fails += not ok
        print(f'{"✓" if ok else "✗"} join {k + 1} at {at:6.2f}s  {segs[k]["id"]}→{segs[k + 1]["id"]}  '
              f'"…{last} | {first}…"  heard: "{" ".join(heard)}"')
        if not ok:
            print(f'     expected: "{" ".join(inside)}"')
            if critical:
                print(f'     the words AT the cut are clipped or gone: {critical}')
            if missing:
                print(f'     missing: {missing}')
            if extra:
                print(f'     extra (leaked from outside the segment, or misheard): {extra}')
    got, _ = model.transcribe(pcm(media), language='en', condition_on_previous_text=False)
    first_word = next((norm(x) for g in got for x in g.text.split() if norm(x)), '')
    if first_word == 'you' and norm(segs[0]['text'].split()[0]) != 'you':
        print('⚠ the transcript starts with "you", which is likely a whisper hallucination in silence. Listen to the '
              'first second; if there is no real word, ignore it.')
    print(f'\n{len(joins) - fails}/{len(joins)} joins clean' + ('' if not fails else ': fix the failing segments in '
          'edit-plan.json (move in/out by 0.05–0.2 s into silence), re-render, verify again'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main(*sys.argv[1:])
