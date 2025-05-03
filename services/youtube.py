"""
YouTube service for downloading and processing videos
"""
import os
import re
import hashlib
import asyncio
from typing import Dict, Any, Optional

import yt_dlp
from pydub import AudioSegment

from config.settings import (
    MEDIA_DIR, 
    AUDIO_FORMAT, 
    DEFAULT_AUDIO_QUALITY,
    LONG_AUDIO_QUALITY,
    LONG_VIDEO_THRESHOLD
)

class YouTubeService:
    """Handles YouTube video downloading and metadata extraction"""
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL or create a hash if extraction fails
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID or hash of URL
        """
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"\'>]+)'
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()
    
    async def download_audio(self, url: str, options: Dict[str, Any]) -> str:
        """
        Download audio from YouTube video asynchronously
        
        Args:
            url: YouTube URL
            options: Options dictionary including duration settings
            
        Returns:
            Path to the downloaded audio file
        """
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, f"{video_id}")
        
        # Check if already downloaded
        existing_path = f"{output_path}.{AUDIO_FORMAT}"
        if os.path.exists(existing_path):
            print(f"Using existing audio file: {existing_path}")
            return existing_path
            
        # Get duration option
        duration = options.get('duration', 'full_video')
        
        # Determine if it's a long video before downloading
        video_info = await self._get_video_info(url)
        duration_seconds = video_info.get('duration', 0)
        
        # Set audio quality based on video length
        audio_quality = DEFAULT_AUDIO_QUALITY
        if duration_seconds > LONG_VIDEO_THRESHOLD:
            audio_quality = LONG_AUDIO_QUALITY
            
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_path}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': AUDIO_FORMAT,
                'preferredquality': audio_quality.replace('k', ''),
            }],
            'quiet': True,
        }
        
        # Run download in a separate thread to not block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._download_with_options, url, ydl_opts)
        
        # Process duration limits if needed
        if duration != 'full_video':
            return await self._process_duration_limit(f"{output_path}.{AUDIO_FORMAT}", duration)
        
        return f"{output_path}.{AUDIO_FORMAT}"
    
    async def _get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video metadata without downloading
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary with video information
        """
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
        }
        
        loop = asyncio.get_event_loop()
        info_dict = await loop.run_in_executor(
            None, 
            lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
        )
        
        return info_dict
    
    def _download_with_options(self, url: str, options: Dict[str, Any]) -> None:
        """
        Download using yt-dlp with given options (sync function for executor)
        
        Args:
            url: YouTube URL
            options: yt-dlp options dictionary
        """
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    
    async def _process_duration_limit(self, audio_path: str, duration: str) -> str:
        """
        Process audio file to limit duration
        
        Args:
            audio_path: Path to audio file
            duration: Duration setting (e.g., 'first_5_minutes')
            
        Returns:
            Path to processed audio file
        """
        # Define duration limit in milliseconds
        duration_limits = {
            'first_5_minutes': 5 * 60 * 1000,
            'first_10_minutes': 10 * 60 * 1000,
            'first_30_minutes': 30 * 60 * 1000,
            'first_60_minutes': 60 * 60 * 1000
        }
        
        limit_ms = duration_limits.get(duration, None)
        if not limit_ms:
            return audio_path  # Return original if no valid limit
        
        # Create output path
        output_path = audio_path.replace(f".{AUDIO_FORMAT}", f"_{duration}.{AUDIO_FORMAT}")
        
        # Check if already processed
        if os.path.exists(output_path):
            return output_path
            
        # Load audio file
        loop = asyncio.get_event_loop()
        sound = await loop.run_in_executor(None, AudioSegment.from_file, audio_path)
        
        # Trim to duration
        trimmed_sound = sound[:limit_ms]
        
        # Export
        await loop.run_in_executor(
            None,
            lambda: trimmed_sound.export(output_path, format=AUDIO_FORMAT)
        )
        
        return output_path
