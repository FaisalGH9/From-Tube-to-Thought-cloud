#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Reinstalling yt-dlp with additional parameters..."
pip uninstall -y yt-dlp
pip install --no-cache-dir yt-dlp==2023.11.14
python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

echo "Creating SSL workaround..."
# Create a Python script to try to fix SSL issues
cat > ssl_fix.py << 'EOL'
import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
    print("SSL certificate verification disabled")
except Exception as e:
    print(f"Failed to modify SSL context: {e}")
EOL

# Try to run the SSL fix
python ssl_fix.py

echo "Installation complete."
