# Clip Studio setup for Windows 10/11 (PowerShell). Free tools only, installed with winget.
# Run from the kit folder:  powershell -ExecutionPolicy Bypass -File setup\install-windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
function Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }

Step "ffmpeg (Gyan full build, includes caption burning), uv, Node.js"
winget install --silent --accept-source-agreements --accept-package-agreements -e --id Gyan.FFmpeg
winget install --silent --accept-source-agreements --accept-package-agreements -e --id astral-sh.uv
winget install --silent --accept-source-agreements --accept-package-agreements -e --id OpenJS.NodeJS.LTS
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Step "Python 3.12 environment"
if (-not (Test-Path ".venv\Scripts\python.exe")) { uv venv --python 3.12 .venv }
uv pip install --python .venv\Scripts\python.exe -q -r setup\requirements.txt

Step "Animation library, fonts, transcription model"
Push-Location graphics; npm install --silent --no-audit --no-fund; Pop-Location
.venv\Scripts\python.exe tools\fetch_fonts.py
.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='auto', compute_type='int8'); print('model ready')"

Step "Check"
.venv\Scripts\python.exe tools\doctor.py
