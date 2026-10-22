#!/usr/bin/env python3
"""Is a newer Clip Studio engine available? Prints one line, plus what's new (from CHANGELOG.md), and never changes anything.

usage: update_check.py            exit 0 = up to date (or offline), 10 = update available
       update_check.py --apply    git pull + doctor (only after the user says yes)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*a):
    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True, timeout=30)


def main():
    if '--apply' in sys.argv:
        r = git('pull', '--ff-only')
        print(r.stdout.strip() or r.stderr.strip())
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'doctor.py')])
        return
    if git('fetch', '-q').returncode != 0:
        print('update check skipped (offline or not a git clone)')
        return
    behind = git('rev-list', '--count', 'HEAD..@{u}').stdout.strip() or '0'
    if behind == '0':
        print('Clip Studio engine is up to date')
        return
    print(f'UPDATE AVAILABLE: {behind} new change(s) to the Clip Studio engine')
    new_log = git('diff', 'HEAD..@{u}', '--', 'CHANGELOG.md').stdout
    added = [ln[1:] for ln in new_log.splitlines() if ln.startswith('+') and not ln.startswith('+++') and ln[1:].strip()]
    for ln in added[:12]:
        print('  ' + ln)
    if not added:
        print('  ' + git('log', '--format=%s', 'HEAD..@{u}').stdout.strip().replace('\n', '\n  '))
    sys.exit(10)


if __name__ == '__main__':
    main()
