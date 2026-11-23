#!/usr/bin/env bash
# Hoplite workspace setup: installs the video production toolkit for every new thread.
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Fonts are licensed and stay out of the public repo; pick them up from this thread's attachments if present.
mkdir -p video-tools/fonts
find .hoplite/attachments -maxdepth 2 -type f \( -iname '*din*next*.otf' -o -iname '*din*next*.ttf' \) \
  -exec cp -n {} video-tools/fonts/ \; 2>/dev/null || true

if [ -x video-tools/.venv/bin/python ] && video-tools/.venv/bin/python video-tools/check_tools.py >/dev/null 2>&1; then
  echo "Video toolkit already installed."
  exit 0
fi
video-tools/install-linux.sh
