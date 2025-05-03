#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Reinstalling yt-dlp with additional parameters..."
pip uninstall -y yt-dlp
pip install --no-cache-dir yt-dlp==2023.11.14
python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

echo "Installing SSL certificates..."
apt-get update && apt-get install -y ca-certificates
update-ca-certificates

echo "Installation complete."
