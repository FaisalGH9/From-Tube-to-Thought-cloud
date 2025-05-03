#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Reinstalling yt-dlp with additional parameters..."
pip uninstall -y yt-dlp
pip install --no-cache-dir yt-dlp==2023.11.14
python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

echo "Installing curl for external downloading..."
apt-get update && apt-get install -y curl || true

echo "Setting up SSL environment variables..."
export PYTHONHTTPSVERIFY=0
export CURL_CA_BUNDLE=""
export SSL_CERT_FILE=""

# Create a Python script that will disable SSL verification
cat > disable_ssl.py << 'EOL'
import os
import ssl
try:
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    ssl._create_default_https_context = ssl._create_unverified_context
    print("SSL certificate verification disabled")
except Exception as e:
    print(f"Failed to modify SSL context: {e}")
EOL

# Run the Python script to disable SSL verification
python disable_ssl.py

echo "Installation complete."
