#!/usr/bin/env bash
# Video production toolkit installer for Ubuntu/Debian and Windows (WSL Ubuntu).
set -euo pipefail
cd "$(dirname "$0")"
KIT="$(pwd)"

echo "==> System packages (ffmpeg, Cairo, Arabic text shaping)"
sudo apt-get update -y
sudo apt-get install -y ffmpeg python3 python3-venv python3-dev python3-pip \
  libcairo2-dev pkg-config libfribidi0 libharfbuzz0b libraqm0 fonts-noto-core

echo "==> Python environment in $KIT/.venv"
python3 -m venv "$KIT/.venv"
"$KIT/.venv/bin/pip" install --upgrade pip
# CPU build of PyTorch keeps the download small (no CUDA libraries)
"$KIT/.venv/bin/pip" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
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
