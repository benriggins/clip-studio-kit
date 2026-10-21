#!/usr/bin/env python3
"""Is everything installed and working? Prints one line per check and the fix for anything missing.

usage: doctor.py          exit code 0 = ready to edit
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import BRAND_FILE, FONTS, ROOT  # noqa: E402

ok = True


def check(name, passed, fix=''):
    global ok
    ok &= bool(passed)
    print(f'{"✓" if passed else "✗"} {name}' + ('' if passed else f'\n    fix: {fix}'))


def main():
    print(f'Clip Studio doctor ({ROOT})\n')
    check('Python 3.10+', sys.version_info >= (3, 10), 'run the setup script for your system')
    for mod in ('faster_whisper', 'numpy', 'PIL', 'cv2', 'fontTools'):
        # each in its own process: cv2 and faster_whisper both bundle FFmpeg libraries and warn if loaded together
        r = subprocess.run([sys.executable, '-c', f'import {mod}'], capture_output=True)
        check(f'python package {mod}', r.returncode == 0, 'run the setup script again')
    try:
        from _common import ffmpeg, has_libass
        path = ffmpeg()
        check(f'ffmpeg ({path})', True)
        check('ffmpeg can burn captions (libass)', has_libass(),
              'Mac: brew install ffmpeg-full · Windows: winget install Gyan.FFmpeg · Linux: apt install ffmpeg')
    except SystemExit:
        check('ffmpeg', False, 'run the setup script')
    try:
        from cleantake import dfn_path
        check('noise + background remover (DeepFilterNet)', subprocess.run(
            [str(dfn_path()), '--version'], capture_output=True).returncode == 0, 'run tools/cleantake.py once: it downloads it')
    except SystemExit:
        check('noise + background remover (DeepFilterNet)', False,
              'not available for this computer: see tools/cleantake.py for the download')
    try:
        from carousel import chrome
        check(f'Chrome for carousel slides ({chrome()})', True)
    except SystemExit:
        check('Chrome for carousel slides', False, 'install Google Chrome (free): https://www.google.com/chrome')
    npx = shutil.which('npx') or shutil.which('npx.cmd')
    check('Node.js / npx (animations)', npx, 'Mac: brew install node · Windows: winget install OpenJS.NodeJS.LTS')
    check('GSAP for graphics', (ROOT / 'graphics' / 'node_modules' / 'gsap' / 'dist' / 'gsap.min.js').exists(),
          'cd graphics && npm install')
    check('caption + graphics fonts', any(FONTS.glob('*.ttf')), '.venv python tools/fetch_fonts.py')
    if BRAND_FILE.exists():
        b = json.loads(BRAND_FILE.read_text())
        missing = [f['file'] for f in b.get('fonts', {}).values()
                   if isinstance(f, dict) and f.get('file') and not (ROOT / f['file']).exists()]
        check('brand profile (my-studio/brand.json)', not missing, f'missing font files: {missing}: run fetch_fonts.py')
    else:
        print('· brand profile not created yet (Claude Code does this in the brand interview)')
    if npx:
        r = subprocess.run([npx, '--yes', 'hyperframes@0.8.34', '--version'], capture_output=True, text=True, timeout=300)
        check('HyperFrames renderer', r.returncode == 0, 'check your internet connection, then re-run doctor')
    print('\n' + ('READY: drop a video in inbox/ and tell Claude Code what you want.' if ok else
                  'NOT READY: fix the ✗ lines above (or ask Claude Code to).'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
