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

# Load proxy URL from environment (e.g., set PROXY_URL in .env or Cloud Run settings)
PROXY_URL = os.getenv("PROXY_URL")
PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

# Optionally set global env proxies so underlying libraries pick it up
if PROXY_URL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

class YouTubeService:
    """Handles YouTube video downloading and metadata extraction with proxy support"""
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL or create a hash if extraction fails
        """
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"'>]+)'
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()
    
    async def download_audio(self, url: str, options: Dict[str, Any]) -> str:
        """
        Download audio from YouTube video asynchronously
        """
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, f"{video_id}")
        
        existing_path = f"{output_path}.{AUDIO_FORMAT}"
        if os.path.exists(existing_path):
            print(f"Using existing audio file: {existing_path}")
            return existing_path
            
        # Fetch simple info
        video_info = {'duration': 0, 'title': 'Unknown'}
        try:
            simple = await self._get_simple_video_info(url)
            if simple:
                video_info = simple
        except Exception as e:
            print(f"Simple info retrieval failed: {e}")
        
        duration_seconds = video_info.get('duration', 0)
        audio_quality = DEFAULT_AUDIO_QUALITY
        if duration_seconds > LONG_VIDEO_THRESHOLD:
            audio_quality = LONG_AUDIO_QUALITY
        
        downloaded_file = None
        # Attempt pytube download with proxy
        try:
            loop = asyncio.get_event_loop()
            downloaded_file = await loop.run_in_executor(None, self._download_with_pytube, url, output_path)
        except Exception as e:
            print(f"Pytube download failed: {e}")
            # Add alternative methods here
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception(f"All download methods failed for {url}")
        
        # Convert to audio format
        if not downloaded_file.endswith(f".{AUDIO_FORMAT}"):
            audio = AudioSegment.from_file(downloaded_file)
            audio_file = f"{output_path}.{AUDIO_FORMAT}"
            audio.export(audio_file, format=AUDIO_FORMAT, bitrate=audio_quality)
            if downloaded_file != audio_file:
                os.remove(downloaded_file)
            downloaded_file = audio_file
        
        # Handle duration limits
        duration_opt = options.get('duration', 'full_video')
        if duration_opt != 'full_video':
            return await self._process_duration_limit(downloaded_file, duration_opt)
        
        return downloaded_file
    
    async def _get_simple_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get basic video info without heavy libraries, using HTTP (with proxy)
        """
        try:
            resp = requests.get(url, timeout=10, proxies=PROXIES)
            resp.raise_for_status()
            content = resp.text
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(' - YouTube', '') if title_match else 'Unknown'
            return {'title': title, 'duration': 0, 'source': 'simple_http'}
        except Exception as e:
            print(f"Simple info HTTP error: {e}")
            return None
    
    def _download_with_pytube(self, url: str, output_path: str) -> str:
        """
        Download using pytube (sync) with proxy support
        """
        try:
            yt = YouTube(
                url,
                use_oauth=False,
                allow_oauth_cache=False,
                proxies=PROXIES
            )
            yt.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/91.0.4472.124 Safari/537.36'}

            # Select best audio stream
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').last()
            if not audio_stream:
                audio_stream = yt.streams.filter(progressive=True).order_by('resolution').first()
            if not audio_stream:
                raise Exception(f"No suitable audio stream found for {url}")

            downloaded = audio_stream.download(
                output_path=os.path.dirname(output_path),
                filename=os.path.basename(output_path)
            )
            return downloaded
        except Exception as e:
            print(f"Pytube download error: {e}")
            raise
    
    async def _process_duration_limit(self, audio_path: str, duration: str) -> str:
        """
        Trim audio to specified duration (with proxy unaffected)
        """
        duration_limits = {
            'first_5_minutes': 5*60*1000,
            'first_10_minutes': 10*60*1000,
            'first_30_minutes': 30*60*1000,
            'first_60_minutes': 60*60*1000
        }
        limit_ms = duration_limits.get(duration)
        if not limit_ms:
            return audio_path
        output_trim = audio_path.replace(f".{AUDIO_FORMAT}", f"_{duration}.{AUDIO_FORMAT}")
        if os.path.exists(output_trim):
            return output_trim
        loop = asyncio.get_event_loop()
        sound = await loop.run_in_executor(None, AudioSegment.from_file, audio_path)
        trimmed = sound[:limit_ms]
        await loop.run_in_executor(None, lambda: trimmed.export(output_trim, format=AUDIO_FORMAT))
        return output_trim
