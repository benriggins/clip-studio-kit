#!/usr/bin/env bash
# Clip Studio setup for macOS. Free tools only. Safe to re-run: each step skips what is already installed.
# Claude Code runs this for you. If Homebrew is missing it stops with NEED_HOMEBREW (installing Homebrew needs
# your Mac password, so you paste one command yourself; Claude Code gives it to you).
set -euo pipefail
cd "$(dirname "$0")/.."
step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

if ! command -v brew >/dev/null 2>&1; then
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)"; done
fi
command -v brew >/dev/null 2>&1 || { echo "NEED_HOMEBREW"; exit 10; }

step "ffmpeg (the full build, which can burn captions), uv (Python manager), Node.js (for animations)"
for f in ffmpeg-full uv node; do brew list --versions "$f" >/dev/null 2>&1 || brew install "$f"; done

step "Python 3.12 environment + transcription, face finding, fonts"
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -q -r setup/requirements.txt

step "Animation library (GSAP) for explainer graphics"
(cd graphics && npm install --silent --no-audit --no-fund)

step "Fonts (free Google Fonts)"
.venv/bin/python tools/fetch_fonts.py

step "Transcription model (downloads once, about 480 MB)"
.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='auto', compute_type='int8'); print('model ready')"

step "HyperFrames renderer (downloads once)"
npx --yes hyperframes@0.8.34 --version >/dev/null 2>&1 && echo "hyperframes ready" || echo "hyperframes will download on first use"

step "Check"
.venv/bin/python tools/doctor.py
