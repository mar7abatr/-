#!/usr/bin/env bash
# Video production toolkit installer for macOS (Apple Silicon or Intel). Requires Homebrew: https://brew.sh
set -euo pipefail
cd "$(dirname "$0")"
KIT="$(pwd)"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it first from https://brew.sh then run this script again."
  exit 1
fi

echo "==> System packages (ffmpeg, Python, Cairo, Arabic text shaping)"
brew install ffmpeg python@3.12 cairo pkg-config fribidi harfbuzz libraqm

PY="$(brew --prefix python@3.12)/bin/python3.12"
echo "==> Python environment in $KIT/.venv"
"$PY" -m venv "$KIT/.venv"
"$KIT/.venv/bin/pip" install --upgrade pip
"$KIT/.venv/bin/pip" install torch torchvision
"$KIT/.venv/bin/pip" install -r requirements.txt
# simple-lama-inpainting pins old Pillow/numpy in its metadata but works with current versions
"$KIT/.venv/bin/pip" install --no-deps simple-lama-inpainting

# Keep downloaded AI models inside the kit (.cache/) so they persist with it.
# A .pth line runs on every interpreter start (sitecustomize.py can be shadowed by the system Python's own).
SITE="$("$KIT/.venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
rm -f "$SITE/sitecustomize.py"
echo "import os; c='$KIT/.cache'; [os.environ.setdefault(k, c + v) for k, v in (('HF_HOME', '/huggingface'), ('REMBG_HOME', '/rembg'), ('TORCH_HOME', '/torch'))]" \
  > "$SITE/video_tools_cache.pth"

echo "==> Checking the installation"
"$KIT/.venv/bin/python" check_tools.py
echo
echo "Done. Optional: download the AI models now (about 4 GB):"
echo "  $KIT/.venv/bin/python download_models.py"
