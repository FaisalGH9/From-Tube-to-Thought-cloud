"""
YouTube service for downloading and processing videos using pytube with proxy support
"""
import os
import re
import hashlib
import asyncio
import requests
from typing import Dict, Any, Optional

from pytubefix import YouTube
from pydub import AudioSegment

from config.settings import (
    MEDIA_DIR,
    AUDIO_FORMAT,
    DEFAULT_AUDIO_QUALITY,
    LONG_AUDIO_QUALITY,
    LONG_VIDEO_THRESHOLD
)

# Load proxy URL from environment
PROXY_URL = os.getenv("PROXY_URL")
PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
if PROXY_URL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

class YouTubeService:
    """Handles YouTube video downloading and metadata extraction with proxy support"""

    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL or create a hash if extraction fails
        """
        youtube_regex = r"(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&\"'>]+)"
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()

    async def download_audio(self, url: str, options: Dict[str, Any]) -> str:
        """
        Download audio from YouTube video asynchronously
        """
        video_id = self.extract_video_id(url)
        output_base = os.path.join(MEDIA_DIR, video_id)
        existing = f"{output_base}.{AUDIO_FORMAT}"
        if os.path.exists(existing):
            print(f"Using existing audio file: {existing}")
            return existing

        # Fetch basic video info
        video_info = {'duration': 0, 'title': 'Unknown'}
        try:
            info = await self._get_simple_video_info(url)
            if info:
                video_info = info
        except Exception as e:
            print(f"Simple info retrieval failed: {e}")

        duration_seconds = video_info.get('duration', 0)
        # Choose quality based on length
        quality = DEFAULT_AUDIO_QUALITY if duration_seconds <= LONG_VIDEO_THRESHOLD else LONG_AUDIO_QUALITY

        # Attempt download via pytube
        downloaded = None
        try:
            loop = asyncio.get_event_loop()
            downloaded = await loop.run_in_executor(None, self._download_with_pytube, url, output_base)
        except Exception as e:
            print(f"Pytube download failed: {e}")

        if not downloaded or not os.path.exists(downloaded):
            raise Exception(f"All download methods failed for {url}")

        # Convert to requested audio format
        if not downloaded.endswith(f".{AUDIO_FORMAT}"):
            audio = AudioSegment.from_file(downloaded)
            target = f"{output_base}.{AUDIO_FORMAT}"
            audio.export(target, format=AUDIO_FORMAT, bitrate=quality)
            os.remove(downloaded)
            downloaded = target

        # Trim duration if needed
        dur_opt = options.get('duration', 'full_video')
        if dur_opt != 'full_video':
            downloaded = await self._process_duration_limit(downloaded, dur_opt)

        return downloaded

    async def _get_simple_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get basic video info via HTTP (with proxy)
        """
        try:
            resp = requests.get(url, timeout=10, proxies=PROXIES)
            resp.raise_for_status()
            title_match = re.search(r'<title>(.*?)<\/title>', resp.text)
            title = title_match.group(1).replace(' - YouTube', '') if title_match else 'Unknown'
            return {'title': title, 'duration': 0}
        except Exception as e:
            print(f"Simple info HTTP error: {e}")
            return None

    def _download_with_pytube(self, url: str, output_base: str) -> str:
        """
        Download audio using pytube synchronously with proxy
        """
        yt = YouTube(
            url,
            use_oauth=False,
            allow_oauth_cache=False,
            proxies=PROXIES
        )
        # Mimic a real browser
        yt.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/91.0.4472.124 Safari/537.36'
        }
        # Pick best audio stream
        stream = yt.streams.filter(only_audio=True).order_by('abr').last()
        if not stream:
            stream = yt.streams.filter(progressive=True).order_by('resolution').first()
        if not stream:
            raise Exception(f"No suitable audio stream found for {url}")
        path = stream.download(
            output_path=os.path.dirname(output_base),
            filename=os.path.basename(output_base)
        )
        return path

    async def _process_duration_limit(self, audio_path: str, duration: str) -> str:
        """
        Trim audio file to the specified duration
        """
        limits = {
            'first_5_minutes': 5*60*1000,
            'first_10_minutes': 10*60*1000,
            'first_30_minutes': 30*60*1000,
            'first_60_minutes': 60*60*1000
        }
        limit_ms = limits.get(duration)
        if not limit_ms:
            return audio_path
        trimmed_path = audio_path.replace(f".{AUDIO_FORMAT}", f"_{duration}.{AUDIO_FORMAT}")
        if os.path.exists(trimmed_path):
            return trimmed_path
        loop = asyncio.get_event_loop()
        sound = await loop.run_in_executor(None, AudioSegment.from_file, audio_path)
        trimmed = sound[:limit_ms]
        await loop.run_in_executor(None, lambda: trimmed.export(trimmed_path, format=AUDIO_FORMAT))
        return trimmed_path

