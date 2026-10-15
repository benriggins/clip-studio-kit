#!/usr/bin/env python3
"""Produce a finished video from scratch: a VIDEO_BLUEPRINT from ChatGPT (a LinkedIn write-up turned into shots,
voiceover, graphics and sound), or a montage of clips. Claude Code has the final say: every decision lands in an
editable timeline.json, which renders deterministically.

usage:
  produce.py prompts  <blueprint.json>          the Grok Imagine shot list to run (prompt + photo to upload per shot)
  produce.py timeline <blueprint.json>          voiceover + music + shots → projects/<p>/<id>/timeline.json
  produce.py montage  <project> <name> <clip…> [--bpm 112] [--seconds 20] [--format 16:9] [--music f.mp3]
                                                [--music-prompt "…"] [--style back-and-forth]
  produce.py render   <timeline.json> [--draft] timeline → base.mov, then captions + graphics + loudness master

Shots for a blueprint go in projects/<p>/<id>/shots/ named after the shot ids (S01.mp4 …). Any other names are
taken in alphabetical order. A shot with no clip falls back to a still IMKAT photo with a slow push-in.
Voice, music and sound effects come from ElevenLabs (agent-os/secrets/elevenlabs.local.json, or ELEVENLABS_API_KEY);
the voice is brand.json voice.voice_id. Generated audio is cached by its text, so re-rendering costs nothing.

timeline.json (everything Claude Code may change):
  canvas {width, height, fps} · grade (imkat-warm | clean | cinematic | bw | none) · grain · vignette
  clips[]: src, in (s), pieces [[source_seconds, speed, {"reverse": true}?] …] (or dur + speed), camera
           (none | push | pull | punch | drift), transition {type, dur} into this clip
           (cut | fade | dip | flash | whip | whip-right | zoom | slide | blur | circle), audio (clip sound, dB or null)
  voice[]: text, at, file          music: file, gain_db, duck, fade_in, fade_out, start
  sfx[]: kind (whoosh | hit | riser | file), at, gain_db, file?      flashes[]: times of white flash frames
  graphics[], accents[], caption_style, platform (passed to the edit plan)
"""
import argparse
import base64
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT, STUDIO, brand, die, ffmpeg, pcm, probe, run, slug  # noqa: E402

FORMATS = {'9:16': (1080, 1920), '16:9': (1920, 1080), '1:1': (1080, 1080), '4:5': (1080, 1350)}
XFADE = {'fade': 'fade', 'dip': 'fadeblack', 'flash': 'fadewhite', 'whip': 'smoothleft', 'whip-right': 'smoothright',
         'zoom': 'zoomin', 'slide': 'slideup', 'blur': 'hblur', 'circle': 'circleopen'}
GRADES = {
    'imkat-warm': "eq=contrast=1.06:saturation=1.10:gamma=0.98,colorbalance=rs=0.02:bs=-0.03:rh=0.035:bh=-0.035,"
                  "curves=master='0/0.02 0.5/0.5 1/0.985'",
    'clean': 'eq=contrast=1.04:saturation=1.05',
    'cinematic': "eq=contrast=1.10:saturation=0.95,colorbalance=rs=-0.04:bs=0.05:rh=0.05:bh=-0.05,"
                 "curves=master='0/0.03 0.5/0.48 1/0.96'",
    'bw': "hue=s=0,eq=contrast=1.15,curves=master='0/0.03 1/0.97'",
    'none': '',
}


# ---------------------------------------------------------------- ElevenLabs (voice, music, sound effects)
def _key():
    if os.environ.get('ELEVENLABS_API_KEY'):
        return os.environ['ELEVENLABS_API_KEY']
    for p in (Path('/Users/Shared/Projects/agent-os/secrets/elevenlabs.local.json'), STUDIO / 'elevenlabs.local.json'):
        if p.exists():
            d = json.loads(p.read_text())
            return next(v for k, v in d.items() if 'key' in k.lower() and isinstance(v, str))
    die('No ElevenLabs key: set ELEVENLABS_API_KEY or add agent-os/secrets/elevenlabs.local.json')


def _eleven(path, body):
    req = urllib.request.Request('https://api.elevenlabs.io' + path, data=json.dumps(body).encode(),
                                 headers={'xi-api-key': _key(), 'Content-Type': 'application/json',
                                          'User-Agent': 'Mozilla/5.0 (ClipStudio)'})
    return urllib.request.urlopen(req, timeout=600).read()


def _cache(kind, payload, ext):
    d = STUDIO / 'audio-cache' / kind
    d.mkdir(parents=True, exist_ok=True)
    return d / (hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16] + ext)


def tts(text, voice=None):
    """Voiceover line → (mp3 path, words [{w, s, e}]) using ElevenLabs character timestamps."""
    v = {**brand().get('voice', {}), **(voice or {})}
    if not v.get('voice_id'):
        die('No voice yet: set brand.json voice.voice_id (Claude Code saves the chosen IMKAT voice there).')
    say = v.get('say', {})            # pronunciation aliases, e.g. {"IMKAT": "I'm-Kat"}; captions keep the real word
    spoken = ' '.join(next((al for k, al in say.items() if w.strip('.,!?;:').upper() == k.upper()), None) and
                      w.replace(w.strip('.,!?;:'), next(al for k, al in say.items() if w.strip('.,!?;:').upper() == k.upper()))
                      or w for w in text.split())
    body = {'text': spoken, 'model_id': v.get('model', 'eleven_multilingual_v2'),
            'voice_settings': v.get('settings', {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.15,
                                                  'use_speaker_boost': True})}
    mp3 = _cache('voice', {**body, 'v': v['voice_id']}, '.mp3')
    meta = mp3.with_suffix('.json')
    if not mp3.exists():
        r = json.loads(_eleven(f"/v1/text-to-speech/{v['voice_id']}/with-timestamps?output_format=mp3_44100_192", body))
        mp3.write_bytes(base64.b64decode(r['audio_base64']))
        al = r.get('alignment') or r.get('normalized_alignment')
        words, cur, s0 = [], '', None
        for ch, a, b in zip(al['characters'], al['character_start_times_seconds'], al['character_end_times_seconds']):
            if ch.isspace():
                if cur:
                    words.append({'w': cur, 's': round(s0, 3), 'e': round(prev_e, 3)})
                cur, s0 = '', None
                continue
            if s0 is None:
                s0 = a
            cur += ch
            prev_e = b
        if cur:
            words.append({'w': cur, 's': round(s0, 3), 'e': round(prev_e, 3)})
        orig = text.split()
        if len(orig) == len(words):   # one alias token per word: show the real spelling in captions
            for w, o in zip(words, orig):
                w['w'] = o
        meta.write_text(json.dumps(words))
    return mp3, json.loads(meta.read_text())


def music(prompt, seconds):
    body = {'prompt': prompt, 'music_length_ms': int(seconds * 1000)}
    out = _cache('music', body, '.mp3')
    if not out.exists():
        out.write_bytes(_eleven('/v1/music', body))
    return out


def sound(prompt, seconds):
    body = {'text': prompt, 'duration_seconds': seconds, 'prompt_influence': 0.6}
    out = _cache('sfx', body, '.mp3')
    if not out.exists():
        out.write_bytes(_eleven('/v1/sound-generation', body))
    return out


SFX_PROMPTS = {'whoosh': ('fast clean cinematic whoosh transition, airy, no music', 0.8),
               'hit': ('deep soft cinematic impact hit with short tail, clean, no music', 1.2),
               'riser': ('short cinematic riser building tension, clean, no music', 2.0)}


# ---------------------------------------------------------------- beats
def detect_bpm(path):
    """Rough tempo from the onset envelope (no extra libraries): autocorrelation over 70-180 BPM."""
    import numpy as np
    x = pcm(path, dur=60, sr=11025)
    hop = 256
    n = len(x) // hop
    env = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))
    on = np.maximum(0, np.diff(env))
    on = on - on.mean()
    fps = 11025 / hop
    best, bpm = -1, 112.0
    for b in np.arange(70, 180, 0.5):
        lag = fps * 60 / b
        i = int(round(lag))
        if i < len(on):
            c = float((on[:-i] * on[i:]).sum())
            if c > best:
                best, bpm = c, float(b)
    return bpm


# ---------------------------------------------------------------- montage generator
def montage(project, name, clips, bpm=112, seconds=20, fmt='16:9', music_file=None, music_prompt=None,
            style='back-and-forth'):
    """Beat-cut back-and-forth montage: slow-mo intro, A/B alternation tightening to 1-beat cuts, a speed-ramped
    'drop' with a flash and punch, rewinds (boomerangs), and a pushed-in hero ending. A starting point to refine."""
    W, H = FORMATS[fmt]
    if music_file and not bpm:
        bpm = detect_bpm(music_file)
    beat = 60.0 / bpm
    srcs = [Path(c).resolve() for c in clips]
    durs = {s: probe(s)['duration'] for s in srcs}
    cursor = {s: 0.4 for s in srcs}

    def take(src, src_len):          # walk through each source so repeats show new frames
        a = cursor[src]
        if a + src_len > durs[src] - 0.1:
            a = 0.2
        cursor[src] = a + src_len * 0.8
        return round(a, 3)

    n = len(srcs)
    plan, t = [], 0.0
    hold = max(4, int(round((seconds or n * 4.5) / beat / n)))      # beats per clip when each clip is used once
    if style == 'back-and-forth' and n >= 10:
        # enough material for fast A/B cutting without repeats
        seq = [(4, 0, [[4, 0.5, {}]], 'push', ('fade', 0.5))]
        seq += [(2, i, [[2, 1.0, {}]], 'drift', ('whip' if i % 2 else 'whip-right', 0.25)) for i in range(1, n // 2)]
        seq += [(1, i, [[1, 1.0, {}]], 'punch', ('cut', 0)) for i in range(n // 2, n - 2)]
        seq += [(3, n - 2, [[1, 1.0, {}], [1.25, 0.4, {}], [0.75, 1.8, {}]], 'punch', ('flash', 0.15))]
        seq += [(4, n - 1, [[4, 0.8, {}]], 'hero', ('zoom', 0.35))]
    else:
        # each clip once, held long enough to breathe; motion and one speed ramp keep it alive
        cams = ['push', 'drift', 'pull', 'drift', 'hero']
        trs = [('fade', 0.6), ('zoom', 0.45), ('blur', 0.35), ('slide', 0.45), ('fade', 0.6)]
        seq = []
        for i in range(n):
            pcs = [[hold, 0.85, {}]]
            if i == n // 2:          # one slow-motion breath in the middle
                pcs = [[hold * 0.4, 1.0, {}], [hold * 0.6, 0.5, {}]]
            seq.append((hold, i, pcs, cams[i % len(cams)] if i < n - 1 else 'hero',
                        ('cut', 0) if i == 0 else trs[i % len(trs)]))
        if n < 10:
            print(f'note: {n} clips → one use each, ~{hold * beat:.1f}s per shot. For fast back-and-forth cutting '
                  f'without repeats, send {max(10, 2 * n)}+ clips.')
    total_beats = sum(s[0] for s in seq)
    scale = (seconds / beat) / total_beats if seconds else 1.0
    out_clips, flashes, sfx = [], [], []
    for bi, (beats, si, pieces, cam, (tr, tdur)) in enumerate(seq):
        src = srcs[si]
        pcs = []
        for bo, sp, opts in pieces:
            out_s = bo * beat * scale
            src_len = round(out_s * sp, 3)
            pcs.append([src_len, sp] + ([opts] if opts else []))
        start = take(src, sum(p[0] for p in pcs))
        out_clips.append({'src': os.path.relpath(src, ROOT), 'in': start, 'pieces': pcs, 'camera': cam,
                          'transition': {'type': tr, 'dur': tdur}, 'audio': None})
        if tr == 'flash':
            flashes.append(round(t, 3))
        t += beats * beat * scale - (tdur if tr != 'cut' else 0)
    total = t + 0.5
    mus = {'file': os.path.relpath(Path(music_file).resolve(), ROOT) if music_file else None,
           'prompt': music_prompt or brand().get('music', {}).get('default_prompt',
                    f'warm modern corporate instrumental, confident and uplifting, punchy drums, {int(bpm)} bpm, no vocals'),
           'gain_db': -6, 'duck': False, 'fade_in': 0.3, 'fade_out': 1.2, 'start': 0}
    tl = {'id': name, 'kind': 'montage', 'style': style, 'bpm': bpm, 'platform': 'linkedin' if fmt == '16:9' else 'instagram',
          'canvas': {'width': W, 'height': H, 'fps': 30}, 'grade': brand().get('style', {}).get('grade', 'imkat-warm'),
          'grain': True, 'vignette': True, 'clips': out_clips, 'voice': [], 'music': mus, 'sfx': sfx,
          'flashes': flashes, 'graphics': [], 'accents': [], 'seconds': round(total, 2)}
    d = ROOT / 'projects' / project / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'timeline.json').write_text(json.dumps(tl, indent=1))
    print(f'montage timeline → {d / "timeline.json"}  ({len(out_clips)} cuts, {bpm:.0f} bpm, ~{total:.1f}s)')
    return d / 'timeline.json'


# ---------------------------------------------------------------- blueprint → timeline
def load_blueprint(path):
    bp = json.loads(Path(path).read_text())
    if 'shots' not in bp:
        die('not a VIDEO_BLUEPRINT (no "shots")')
    return bp


def prompts(path):
    bp = load_blueprint(path)
    lines = [f'# Grok Imagine shots: {bp.get("title", bp.get("id", ""))}', '',
             f'Make each shot in Grok Imagine as **{bp.get("format", "16:9")}** video. Upload the photo named, paste the '
             'prompt, then save the clip as the shot id (S01.mp4 …) and drop them all in the shots folder.', '']
    for s in bp['shots']:
        v = s.get('visual', {})
        if v.get('source', 'grok') != 'grok':
            continue
        lines += [f'## {s["id"]} · {s.get("role", "")}', f'- Photo to upload: {v.get("photo", "none (text to video)")}',
                  f'- Prompt: {v.get("grok_prompt", "")}', '']
    out = Path(path).parent / 'GROK-SHOTS.md'
    out.write_text('\n'.join(lines))
    print(out.read_text())
    print(f'→ {out}')


def timeline(path):
    bp = load_blueprint(path)
    project = bp.get('project') or slug(bp.get('title', 'video'))
    vid = bp.get('id') or slug(bp.get('title', 'video'))
    d = ROOT / 'projects' / project / vid
    (d / 'shots').mkdir(parents=True, exist_ok=True)
    W, H = FORMATS.get(bp.get('format', '16:9'), (1920, 1080))
    found = sorted(p for p in (d / 'shots').iterdir() if p.suffix.lower() in ('.mp4', '.mov', '.webm'))
    by_id = {p.stem.upper(): p for p in found}
    spare = [p for p in found if p.stem.upper() not in {s['id'].upper() for s in bp['shots']}]
    photos = {Path(p).stem: ROOT / p for p in brand().get('style', {}).get('backdrop', {}).get('photos', [])}
    clips, voice, sfx, flashes, t = [], [], [], [], 0.0
    lead, tail = 0.25, 0.35
    for i, s in enumerate(bp['shots']):
        src = by_id.get(s['id'].upper()) or (spare.pop(0) if spare else None)
        still = None
        if not src:
            ph = s.get('visual', {}).get('photo', '')
            still = next((p for k, p in photos.items() if k in ph), None) or (list(photos.values()) or [None])[i % max(1, len(photos))]
            if not still:
                die(f'no clip for shot {s["id"]} and no brand photos to fall back on')
        vo = s.get('vo', '').strip()
        vo_dur = 0.0
        if vo:
            mp3, words = tts(vo)
            vo_dur = words[-1]['e'] if words else probe(mp3)['duration']
        tr = s.get('transition_in', 'fade' if i else 'cut')
        tdur = 0 if tr == 'cut' else {'flash': 0.15, 'whip': 0.25, 'whip-right': 0.25}.get(tr, 0.4)
        dur = max(float(s.get('seconds', 0) or 0), vo_dur + lead + tail, 1.6) + (tdur if i else 0)
        speed = {'slow-mo': 0.5, 'slow': 0.75, 'fast': 1.4}.get(s.get('speed', 'normal'), 1.0)
        start_out = t - (tdur if i else 0)
        if still:
            clip = {'still': os.path.relpath(still, ROOT), 'dur': round(dur, 3)}
        else:
            sd = probe(src)['duration']
            need = dur * speed
            if need > sd - 0.2:      # stretch the clip a little rather than run out of frames
                speed = max(0.45, (sd - 0.3) / dur)
                need = dur * speed
            clip = {'src': os.path.relpath(src, ROOT), 'in': round(min(0.3, max(0, sd - need - 0.05)), 3),
                    'pieces': [[round(need, 3), round(speed, 3)]]}
        clip.update({'shot': s['id'], 'camera': s.get('camera', 'push'),
                     'transition': {'type': tr, 'dur': tdur}, 'audio': s.get('clip_audio_db')})
        clips.append(clip)
        if vo:
            voice.append({'text': vo, 'at': round(start_out + (tdur if i else 0) + lead, 3), 'shot': s['id']})
        for k in s.get('sfx', []):
            sfx.append({'kind': k, 'at': round(max(0, start_out - (0.25 if k == 'whoosh' else 0)), 3),
                        'gain_db': {'whoosh': -16, 'hit': -12, 'riser': -16}.get(k, -16)})
        if tr == 'flash':
            flashes.append(round(start_out + tdur, 3))
        t = start_out + dur
    m = bp.get('music', {})
    tl = {'id': vid, 'kind': 'blueprint', 'title': bp.get('title', ''), 'platform': bp.get('platform', 'linkedin'),
          'canvas': {'width': W, 'height': H, 'fps': 30}, 'grade': bp.get('grade', 'imkat-warm'),
          'grain': True, 'vignette': True, 'clips': clips, 'voice': voice,
          'music': {'file': m.get('file'), 'prompt': m.get('prompt') or m.get('mood'), 'gain_db': -17, 'duck': True,
                    'fade_in': 0.8, 'fade_out': 1.5, 'start': 0},
          'sfx': sfx, 'flashes': flashes, 'graphics': [], 'on_screen': [
              {'shot': s['id'], **s['on_screen']} for s in bp['shots'] if s.get('on_screen')],
          'accents': bp.get('accents', []), 'caption_style': bp.get('captions'), 'posting': bp.get('posting', {}),
          'seconds': round(t + 0.6, 2)}
    (d / 'timeline.json').write_text(json.dumps(tl, indent=1))
    print(f'timeline → {d / "timeline.json"}  ({len(clips)} shots, {len(voice)} voice lines, ~{t:.1f}s)')
    if tl['on_screen']:
        print('on-screen graphics to build with explainer.py (then add to timeline "graphics"):')
        for g in tl['on_screen']:
            print(f'  {g["shot"]}: {g.get("template")} · {g.get("idea", "")} · labels {g.get("labels")}')
    return d / 'timeline.json'


# ---------------------------------------------------------------- render
def clip_chain(k, c, W, H, fps, inputs):
    """Filter graph for one timeline clip → label [c{k}], plus its duration in the cut."""
    fc, labels, out_dur = [], [], 0.0
    if c.get('still'):
        inputs += ['-loop', '1', '-framerate', str(fps), '-t', f'{c["dur"]:.3f}', '-i', str(ROOT / c['still'])]
        ii = len([x for x in inputs if x == '-i']) - 1
        fc.append(f'[{ii}:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},'
                  f'setsar=1,fps={fps}[p{k}_0]')
        labels.append(f'[p{k}_0]')
        out_dur = c['dur']
        src_w, src_h = W * 2, H * 2
    else:
        src = ROOT / c['src']
        info = probe(src)
        src_w, src_h = info['width'], info['height']
        pieces = c.get('pieces') or [[c['dur'] * c.get('speed', 1.0), c.get('speed', 1.0)]]
        a = float(c.get('in', 0))
        for j, p in enumerate(pieces):
            src_len, sp = float(p[0]), float(p[1])
            opts = p[2] if len(p) > 2 else {}
            inputs += ['-ss', f'{a:.3f}', '-t', f'{src_len:.3f}', '-i', str(src)]
            ii = len([x for x in inputs if x == '-i']) - 1
            smooth = ',minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1' if sp < 0.8 else ''
            rev = ',reverse' if opts.get('reverse') else ''
            fc.append(f'[{ii}:v]setpts=PTS-STARTPTS{rev}{smooth},setpts=(PTS-STARTPTS)/{sp},fps={fps},'
                      f'scale={src_w}:{src_h},setsar=1[p{k}_{j}]')
            labels.append(f'[p{k}_{j}]')
            out_dur += src_len / sp
            a += 0 if opts.get('reverse') else src_len
    if len(labels) > 1:
        fc.append(''.join(labels) + f'concat=n={len(labels)}:v=1:a=0[q{k}]')
    else:
        fc.append(f'{labels[0]}null[q{k}]')
    # camera: cover the canvas with headroom, then move inside it (zoompan on a 1.5x frame keeps motion smooth)
    cw, ch = W * 3 // 2 // 2 * 2, H * 3 // 2 // 2 * 2
    frames = max(1, int(out_dur * fps))
    zexpr = {'push': f"1+0.07*on/{frames}", 'pull': f"1.07-0.07*on/{frames}", 'hero': f"1+0.16*on/{frames}",
             'punch': "1+0.10*exp(-on/5)+0.03*on/%d" % frames, 'drift': "1.05", 'none': "1"}[c.get('camera', 'push')]
    xexpr = (f"(iw-iw/zoom)/2+(iw-iw/zoom)*0.35*(on/{frames}-0.5)" if c.get('camera') == 'drift'
             else "(iw-iw/zoom)/2")
    fc.append(f'[q{k}]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},'
              f"zoompan=z='{zexpr}':x='{xexpr}':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={fps},"
              f'setsar=1,format=yuv420p,settb=AVTB[c{k}]')
    return fc, out_dur


def render(tl_path, draft=False):
    tl_path = Path(tl_path).resolve()
    tl = json.loads(tl_path.read_text())
    d = tl_path.parent
    W, H, fps = tl['canvas']['width'], tl['canvas']['height'], tl['canvas'].get('fps', 30)
    inputs, fc, durs = [], [], []
    for k, c in enumerate(tl['clips']):
        f, du = clip_chain(k, c, W, H, fps, inputs)
        fc += f
        durs.append(du)
    # joins: xfade for transitions, plain concat-by-xfade(1 frame) for cuts
    cur, length = '[c0]', durs[0]
    starts = [0.0]
    for k in range(1, len(durs)):
        tr = tl['clips'][k].get('transition', {}) or {}
        typ = tr.get('type', 'cut')
        td = float(tr.get('dur', 0)) if typ != 'cut' else 1.0 / fps
        td = min(td, durs[k] - 0.05, length - 0.05)
        off = length - td
        fc.append(f'{cur}[c{k}]xfade=transition={XFADE.get(typ, "fade")}:duration={td:.3f}:offset={off:.3f}[j{k}]')
        cur = f'[j{k}]'
        starts.append(off)
        length = off + durs[k]
    total = length
    post = []
    g = GRADES.get(tl.get('grade', 'imkat-warm'), '')
    if g:
        post.append(g)
    if tl.get('vignette'):
        post.append('vignette=angle=PI/5:mode=forward')
    for ft in tl.get('flashes', []):
        post.append(f"eq=brightness=0.35:contrast=0.85:enable='between(t,{ft:.3f},{ft + 2 / fps:.3f})'")
    if tl.get('grain'):
        post.append('noise=alls=3:allf=t')   # light film grain; heavier grain balloons the file size
    fc.append(f'{cur}{",".join(post) or "null"},format=yuv420p[vout]')

    # audio: clip sound, voice, music (ducked under voice), sound effects
    nin = len([x for x in inputs if x == '-i'])
    mix, vo_labels = [], []
    for k, c in enumerate(tl['clips']):
        if c.get('audio') is None or c.get('still'):
            continue
        p = (c.get('pieces') or [[1, 1]])[0]
        inputs += ['-ss', f'{float(c.get("in", 0)):.3f}', '-t', f'{float(p[0]):.3f}', '-i', str(ROOT / c['src'])]
        ms = int(starts[k] * 1000)
        fc.append(f'[{nin}:a]atempo={max(0.5, min(2.0, float(p[1])))},volume={c["audio"]}dB,afade=t=in:d=0.2,'
                  f'adelay={ms}|{ms},apad[ca{k}]')
        mix.append(f'[ca{k}]')
        nin += 1
    for i, v in enumerate(tl.get('voice', [])):
        mp3 = Path(v['file']) if v.get('file') else tts(v['text'])[0]
        inputs += ['-i', str(mp3)]
        ms = int(float(v['at']) * 1000)
        fc.append(f'[{nin}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},apad[vo{i}]')
        vo_labels.append(f'[vo{i}]')
        nin += 1
    if vo_labels:
        fc.append(''.join(vo_labels) + f'amix=inputs={len(vo_labels)}:normalize=0:duration=longest,'
                  f'atrim=0:{total:.3f}[vox]')
        fc.append('[vox]asplit=2[voxa][voxk]')
        mix.append('[voxa]')
    m = tl.get('music') or {}
    mfile = (ROOT / m['file']) if m.get('file') else (music(m['prompt'], min(300, total + 2)) if m.get('prompt') else None)
    if mfile:
        inputs += ['-stream_loop', '-1', '-ss', f'{float(m.get("start", 0)):.3f}', '-i', str(mfile)]
        fo = float(m.get('fade_out', 1.5))
        fc.append(f'[{nin}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,'
                  f'volume={m.get("gain_db", -17)}dB,afade=t=in:d={m.get("fade_in", 0.8)},'
                  f'afade=t=out:st={max(0, total - fo):.3f}:d={fo}[mus0]')
        if m.get('duck', True) and vo_labels:
            fc.append('[mus0][voxk]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450:makeup=1[mus]')
        else:
            if vo_labels:
                fc.append('[voxk]anullsink')
            fc.append('[mus0]anull[mus]')
        mix.append('[mus]')
        nin += 1
    elif vo_labels:
        fc.append('[voxk]anullsink')
    for i, s in enumerate(tl.get('sfx', [])):
        f = Path(s['file']) if s.get('file') else sound(*SFX_PROMPTS[s['kind']])
        inputs += ['-i', str(f)]
        ms = max(0, int(float(s['at']) * 1000))
        fc.append(f'[{nin}:a]aresample=48000,aformat=channel_layouts=stereo,volume={s.get("gain_db", -14)}dB,'
                  f'adelay={ms}|{ms},apad[sx{i}]')
        mix.append(f'[sx{i}]')
        nin += 1
    if mix:
        fc.append(''.join(mix) + f'amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total:.3f}[aout]')
    else:
        inputs += ['-f', 'lavfi', '-t', f'{total:.3f}', '-i', 'anullsrc=r=48000:cl=stereo']
        fc.append(f'[{nin}:a]anull[aout]')
    base = d / 'base.mov'
    q = ['-crf', '26', '-preset', 'veryfast'] if draft else ['-crf', '14', '-preset', 'medium']
    print(f'rendering {tl["id"]}: {len(durs)} clips, {total:.1f}s …')
    run([ffmpeg(), '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
         '-c:v', 'libx264', *q, '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', '-t', f'{total:.3f}', base])

    # hand over to the normal finishing chain: captions from the voice's own timings, graphics, loudness master
    take = f'VO-{tl["id"]}'
    words = []
    for v in tl.get('voice', []):
        _, ws = tts(v['text']) if not v.get('file') else (None, v.get('words', []))
        words += [{'w': w['w'], 's': round(w['s'] + float(v['at']), 3), 'e': round(w['e'] + float(v['at']), 3)} for w in ws]
    project = d.parent
    if words:
        (project / 'transcript' / take).mkdir(parents=True, exist_ok=True)
        (project / 'transcript' / take / 'words.json').write_text(json.dumps(words))
    plan = {'id': tl['id'], 'title': tl.get('title', ''), 'platform': tl.get('platform', ''),
            'canvas': tl['canvas'], 'accents': tl.get('accents', []),
            'graphics': [{'sfx': False, **g} for g in tl.get('graphics', [])],
            'segments': [{'id': 'S1', 'take': take, 'source': str(base), 'in': 0.0, 'out': round(total, 3),
                          'text': ' '.join(v['text'] for v in tl.get('voice', []))}]}
    if tl.get('caption_style'):
        plan['caption_style'] = tl['caption_style']
    (d / 'edit-plan.json').write_text(json.dumps(plan, indent=1))
    py = sys.executable
    ass = d / 'captions.ass'
    if words:
        subprocess.run([py, str(ROOT / 'tools' / 'captions.py'), str(d / 'edit-plan.json')], check=True)
    elif ass.exists():
        ass.unlink()
    subprocess.run([py, str(ROOT / 'tools' / 'render.py'), str(d / 'edit-plan.json')] + (['--draft'] if draft else []),
                   check=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prompts', 'timeline', 'montage', 'render'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--bpm', type=float, default=112)
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--format', default='16:9')
    ap.add_argument('--music')
    ap.add_argument('--music-prompt')
    ap.add_argument('--style', default='back-and-forth')
    ap.add_argument('--draft', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'prompts':
        prompts(a.args[0])
    elif a.cmd == 'timeline':
        timeline(a.args[0])
    elif a.cmd == 'montage':
        if len(a.args) < 3:
            die('usage: produce.py montage <project> <name> <clip…>')
        montage(a.args[0], a.args[1], a.args[2:], a.bpm, a.seconds, a.format, a.music, a.music_prompt, a.style)
    else:
        render(a.args[0], a.draft)
