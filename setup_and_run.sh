#!/usr/bin/env bash
set -e

echo "======================================================"
echo "  Installing System Dependencies (FFmpeg, TTS, Fonts)  "
echo "======================================================"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ffmpeg espeak-ng fonts-dejavu-core python3-pip
fi

echo "======================================================"
echo "  Installing Python Dependencies                       "
echo "======================================================"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "======================================================"
echo "  Setting up directories                               "
echo "======================================================"
mkdir -p outputs workspaces assets/media assets/geo assets/fonts

echo "✅ Setup Complete!"
echo "Run 'python3 app.py' to start the UI, or 'python3 -m pipeline.demo' for the offline demo."