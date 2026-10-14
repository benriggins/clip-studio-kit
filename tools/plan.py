#!/usr/bin/env python3
"""Turn ChatGPT's CLIP PLAN into exact, cut-ready edit plans.

usage: plan.py <projects/NAME/chatgpt/clip-plan.json> [--only CLIP_ID]

Works for one video or many takes: each segment names its take ("take": "V2"; default V1) and is cut from that
take's file (projects/NAME/takes.json). For every clip in the plan, for every segment:
  1. Finds the segment's words in that take's words.json near ChatGPT's timecodes (fuzzy, but they must be the speaker's
     real words: a paraphrase is rejected and reported, never "fixed").
  2. Snaps the in/out points to MEASURED silence between words (10 ms energy bins), never to a timecode label.
  3. Sets a static, face-centred crop for the clip's format, alternating wide/tight so jump cuts look deliberate.
Writes projects/<project>/<clip-id>/edit-plan.json and prints warnings (tight joins, missed faces).
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import CANVAS, die, fmt, norm, pcm, probe, to_sec  # noqa: E402
from face import face_box  # noqa: E402

WINDOW = 8.0          # seconds either side of ChatGPT's timecode to search for the words
MIN_GAP = 0.10        # a gap smaller than this between words is a "tight" join: cut lands on a breath at best
TIGHT = 0.90          # tight crop = 90% of the wide crop (looser would not read as a change; tighter clips hats on a lean-in)


def find_span(words, text, t0, t1):
    """Index range of `text` in words, searched near [t0, t1]. Returns (i, j, ratio)."""
    want = [norm(x) for x in text.split() if norm(x)]
    cand = [i for i, w in enumerate(words) if t0 - WINDOW <= w['s'] <= t1 + WINDOW]
    if not cand or not want:
        return None
    lo, hi = cand[0], cand[-1] + 1
    hay = [norm(w['w']) for w in words[lo:hi]]
    best = (0.0, None, None)
    n = len(want)
    for i in range(0, len(hay) - 1):
        for L in range(max(1, n - 3), n + 4):
            seg = hay[i:i + L]
            if not seg:
                continue
            r = difflib.SequenceMatcher(None, want, seg, autojunk=False).ratio()
            if r > best[0]:
                best = (r, lo + i, lo + i + len(seg) - 1)
    return best[1], best[2], best[0]


def quietest(media, a, b):
    """Time of the quietest 30 ms inside [a, b] (measured), or the midpoint if the span is tiny."""
    import numpy as np
    if b - a < 0.04:
        return (a + b) / 2
    x = pcm(media, a, b - a)
    hop = 160                                   # 10 ms at 16 kHz
    if len(x) < hop * 3:
        return (a + b) / 2
    e = np.sqrt(np.convolve(x ** 2, np.ones(hop * 3) / (hop * 3), mode='valid')[::hop] + 1e-12)
    k = int(np.argmin(e))
    return a + (k * hop + hop * 1.5) / 16000


def cut_points(media, words, i, j, warnings, sid):
    first, last = words[i], words[j]
    prev_e = words[i - 1]['e'] if i > 0 else max(0.0, first['s'] - 0.5)
    next_s = words[j + 1]['s'] if j + 1 < len(words) else last['e'] + 0.5
    if first['s'] - prev_e < MIN_GAP:
        warnings.append(f'{sid}: tight IN before "{first["w"]}" ({first["s"] - prev_e:.2f}s gap); listen to the join')
    if next_s - last['e'] < MIN_GAP:
        warnings.append(f'{sid}: tight OUT after "{last["w"]}" ({next_s - last["e"]:.2f}s gap); listen to the join')
    a = quietest(media, max(prev_e, first['s'] - 0.6), first['s'] - 0.01)
    b = quietest(media, last['e'] + 0.01, min(next_s, last['e'] + 0.6))
    return round(a, 3), round(b, 3)


def crop_for(info, fmt_, face, tight):
    W, H = info['width'], info['height']
    cw, ch = CANVAS[fmt_]
    ar = cw / ch
    if W / H > ar:                     # source wider than target: full height, slide horizontally
        h = H
        w = h * ar
    else:
        w = W
        h = w / ar
    if tight:
        w, h = w * TIGHT, h * TIGHT
    w, h = int(w) // 2 * 2, int(h) // 2 * 2
    x = face['cx'] - w / 2
    # the face box stops at the eyebrows: leave room for hair or a hat (~0.8 face heights) plus a little air
    y = (face['cy'] - face['h'] * 1.3 - h * 0.05) if (face['found'] and h < H) else (H - h) / 2
    x = int(min(max(0, x), W - w)) // 2 * 2
    y = int(min(max(0, y), H - h)) // 2 * 2
    return {'x': x, 'y': y, 'w': w, 'h': h, 'preset': 'tight' if tight else 'wide'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip_plan')
    ap.add_argument('--only')
    a = ap.parse_args()
    plan_path = Path(a.clip_plan).resolve()
    project = plan_path.parent.parent if plan_path.parent.name == 'chatgpt' else plan_path.parent
    takes_f = project / 'takes.json'
    if not takes_f.exists():
        die(f'{takes_f} missing: run transcribe.py --project {project.name} on the video(s) first')
    takes = json.loads(takes_f.read_text())
    words, infos = {}, {}
    for tid, t in takes.items():
        wf = project / 'transcript' / tid / 'words.json'
        if wf.exists():
            words[tid] = json.loads(wf.read_text())
            infos[tid] = probe(t['file'])
    cp = json.loads(plan_path.read_text())
    clips = cp['clips'] if 'clips' in cp else [cp]
    for clip in clips:
        cid = clip['id']
        if a.only and cid != a.only:
            continue
        fmt_ = clip.get('format', '9:16')
        if fmt_ not in CANVAS:
            die(f'{cid}: unknown format {fmt_} (use one of {", ".join(CANVAS)})')
        warnings, segs, errors = [], [], []
        for k, s in enumerate(clip['segments']):
            sid = f'{cid}/S{k + 1}'
            tid = str(s.get('take', 'V1')).upper()
            if not tid.startswith('V'):
                tid = f'V{tid}'
            if tid not in words:
                errors.append(f'{sid}: take {tid} is not in this project (have {", ".join(sorted(words))})')
                continue
            ws, media, info = words[tid], takes[tid]['file'], infos[tid]
            found = find_span(ws, s['text'], to_sec(s['start']), to_sec(s['end']))
            if not found or found[2] < 0.75:
                near = ' '.join(w['w'] for w in ws if to_sec(s['start']) - 2 <= w['s'] <= to_sec(s['end']) + 2)
                errors.append(f'{sid} ({tid}): these words are not in the transcript near {s["start"]}–{s["end"]} '
                              f'(match {0 if not found else found[2]:.0%}).\n   ChatGPT wrote: "{s["text"]}"\n'
                              f'   Transcript there: "{near}"')
                continue
            i, j, r = found
            if r < 0.92:
                warnings.append(f'{sid}: words differ slightly from ChatGPT\'s text ({r:.0%} match); '
                                f'the real transcript words are used')
            t_in, t_out = cut_points(media, ws, i, j, warnings, sid)
            face = face_box(media, t_in, t_out)
            if not face['found']:
                warnings.append(f'{sid}: no face found; crop is centred. Check frames with frames.py')
            elif face.get('fallback'):
                warnings.append(f'{sid}: face not visible in this span; used its usual position in {tid}. Check frames')
            crop = crop_for(info, fmt_, face, tight=bool(k % 2)) if info['width'] else None
            cw, ch = CANVAS[fmt_]
            # where the face sits in the FINISHED frame (canvas pixels): face cards centre on this automatically
            fpos = ({'cx': round((face['cx'] - crop['x']) * cw / crop['w']), 'cy': round((face['cy'] - crop['y']) * ch / crop['h']),
                     'h': round(face['h'] * ch / crop['h'])} if crop and face['found'] else None)
            segs.append({'id': f'S{k + 1}', 'take': tid, 'source': media, 'role': s.get('role', ''),
                         'in': t_in, 'out': t_out, 'text': ' '.join(w['w'] for w in ws[i:j + 1]),
                         'crop': crop, 'face': fpos})
        if errors:
            print(f'\n✗ {cid}: {len(errors)} segment(s) rejected, nothing written for this clip:')
            for e in errors:
                print('  ' + e)
            continue
        out_dir = project / cid
        out_dir.mkdir(parents=True, exist_ok=True)
        cw, ch = CANVAS[fmt_]
        plan = {'id': cid, 'title': clip.get('title', ''), 'platform': clip.get('platform', ''), 'format': fmt_,
                'canvas': {'width': cw, 'height': ch, 'fps': 30},
                'segments': segs, 'accents': clip.get('accents', []), 'graphics': [],
                'explainer_ideas': clip.get('explainers', []), 'posting': clip.get('posting', {})}
        (out_dir / 'edit-plan.json').write_text(json.dumps(plan, indent=1, ensure_ascii=False))
        dur = sum(s['out'] - s['in'] for s in segs)
        print(f'\n✓ {cid} ({fmt_}, {len(segs)} segments, {dur:.1f}s) → {out_dir / "edit-plan.json"}')
        for s in segs:
            print(f'   {s["id"]} {s["take"]} {fmt(s["in"])}–{fmt(s["out"])} '
                  f'{s["crop"]["preset"] if s["crop"] else ""}: {s["text"][:66]}')
        for w in warnings:
            print('   ⚠ ' + w)


if __name__ == '__main__':
    main()
