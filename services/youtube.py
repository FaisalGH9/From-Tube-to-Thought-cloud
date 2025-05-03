import re
import hashlib
import os
from pytubefix import YouTube
from config.settings import MEDIA_DIR, AUDIO_FORMAT

class YouTubeService:
    """Handles YouTube video downloading and metadata extraction"""

    def extract_video_id(self, url: str) -> str:
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"\'>]+)'
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()

    async def download_audio(self, url: str, options: dict) -> str:
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, f"{video_id}.{AUDIO_FORMAT}")

        # ✅ Create parent directories if they don't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # ✅ If file already downloaded, skip
        if os.path.exists(output_path):
            return output_path

        try:
            yt = YouTube(url)
            audio_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
            if not audio_stream:
                raise Exception("No suitable audio stream found")

            # ✅ Download to the safe path
            audio_stream.download(filename=output_path)
            return output_path
        except Exception as e:
            raise Exception(f"Audio download failed: {e}")
