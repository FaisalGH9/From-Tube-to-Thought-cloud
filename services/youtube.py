import os
import re
import hashlib
import asyncio
import yt_dlp
from pydub import AudioSegment
from typing import Dict, Any

from config.settings import (
    MEDIA_DIR,
    AUDIO_FORMAT,
    DEFAULT_AUDIO_QUALITY,
    LONG_AUDIO_QUALITY,
    LONG_VIDEO_THRESHOLD
)

class YouTubeService:
    def extract_video_id(self, url: str) -> str:
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"\'>]+)'
        match = re.search(youtube_regex, url)
        return match.group(4) if match else hashlib.md5(url.encode()).hexdigest()

    async def download_audio(self, url: str, options: Dict[str, Any]) -> str:
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, video_id)
        audio_file = f"{output_path}.{AUDIO_FORMAT}"

        if os.path.exists(audio_file):
            return audio_file

        duration = options.get('duration', 'full_video')
        audio_quality = DEFAULT_AUDIO_QUALITY

        try:
            video_info = await self._get_info_with_yt_dlp(url)
            if video_info['duration'] > LONG_VIDEO_THRESHOLD:
                audio_quality = LONG_AUDIO_QUALITY
        except:
            video_info = {'title': 'Unknown', 'duration': 0}

        await self._download_with_ytdlp(url, output_path, audio_quality)

        if not os.path.exists(audio_file):
            raise Exception(f"Download failed for {url}")

        if duration != 'full_video':
            return await self._process_duration_limit(audio_file, duration)

        return audio_file

    async def _get_info_with_yt_dlp(self, url: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()

        def extract():
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                return ydl.extract_info(url, download=False)
        
        return await loop.run_in_executor(None, extract)

    async def _download_with_ytdlp(self, url: str, output_path: str, quality: str):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{output_path}.%(ext)s",
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': AUDIO_FORMAT,
                'preferredquality': quality.replace("k", ""),
            }],
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

    async def _process_duration_limit(self, audio_path: str, duration: str) -> str:
        duration_limits = {
            'first_5_minutes': 5 * 60 * 1000,
            'first_10_minutes': 10 * 60 * 1000,
            'first_30_minutes': 30 * 60 * 1000,
            'first_60_minutes': 60 * 60 * 1000
        }

        limit_ms = duration_limits.get(duration)
        if not limit_ms:
            return audio_path

        output_path = audio_path.replace(f".{AUDIO_FORMAT}", f"_{duration}.{AUDIO_FORMAT}")
        if os.path.exists(output_path):
            return output_path

        loop = asyncio.get_event_loop()
        sound = await loop.run_in_executor(None, AudioSegment.from_file, audio_path)
        trimmed = sound[:limit_ms]

        await loop.run_in_executor(None, lambda: trimmed.export(output_path, format=AUDIO_FORMAT))
        return output_path
