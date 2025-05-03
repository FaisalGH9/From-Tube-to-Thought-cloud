import re
import hashlib
import os
from pytubefix import YouTube
from config.settings import MEDIA_DIR, AUDIO_FORMAT
import streamlit as st  # ✅ Add for visible logs

class YouTubeService:
    def extract_video_id(self, url: str) -> str:
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"\'>]+)'
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()

    async def download_audio(self, url: str, options: dict) -> str:
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, f"{video_id}.{AUDIO_FORMAT}")

        # 🧪 Log to UI
        st.warning(f"MEDIA_DIR: {MEDIA_DIR}")
        st.warning(f"Output path: {output_path}")

        # ✅ Ensure folder exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if os.path.exists(output_path):
            st.success("Audio already downloaded.")
            return output_path

        try:
            yt = YouTube(url)
            audio_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
            if not audio_stream:
                raise Exception("No suitable audio stream found")

            audio_stream.download(filename=output_path)
            st.success("Audio downloaded successfully.")
            return output_path
        except Exception as e:
            st.error(f"Audio download failed: {e}")
            raise Exception(f"Audio download failed: {e}")
