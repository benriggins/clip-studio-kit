#!/usr/bin/env bash
# Clip Studio setup for Debian/Ubuntu Linux. Needs sudo for apt (you'll be asked for your password once).
set -euo pipefail
cd "$(dirname "$0")/.."
sudo apt-get update -y
sudo apt-get install -y ffmpeg nodejs npm python3-pip curl
command -v uv >/dev/null 2>&1 || python3 -m pip install --user uv
export PATH="$HOME/.local/bin:$PATH"
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -q -r setup/requirements.txt
(cd graphics && npm install --silent --no-audit --no-fund)
.venv/bin/python tools/fetch_fonts.py
.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='auto', compute_type='int8'); print('model ready')"
.venv/bin/python tools/doctor.py
