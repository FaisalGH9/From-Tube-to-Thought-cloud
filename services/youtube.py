"""
YouTube service for downloading and processing videos
"""
import os
import re
import hashlib
import asyncio
import logging
import ssl
import urllib.request
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)

# Apply SSL certificate verification bypass - comprehensive approach
from services.ssl_fix import apply_ssl_fix
ssl_success = apply_ssl_fix()
logging.info(f"SSL fix application success: {ssl_success}")

# Apply yt-dlp fix before importing
from services.yt_dlp_fix import apply_yt_dlp_fix
yt_dlp_success = apply_yt_dlp_fix()
if not yt_dlp_success:
    logging.error("Failed to apply yt-dlp fix. Video downloads may fail.")

import yt_dlp
from pydub import AudioSegment

from config.settings import (
    MEDIA_DIR,
    AUDIO_FORMAT,
    DEFAULT_AUDIO_QUALITY,
    LONG_AUDIO_QUALITY,
    LONG_VIDEO_THRESHOLD,
    COOKIES_PATH
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
            logging.info(f"Using existing audio file: {existing_path}")
            return existing_path
            
        # Get duration option
        duration = options.get('duration', 'full_video')
        
        # Set default audio quality
        audio_quality = DEFAULT_AUDIO_QUALITY
        
        # Try different download strategies in sequence
        downloaded = False
        error_messages = []
        
        # Unified base options with best security bypass settings
        base_opts = {
            'quiet': False,
            'verbose': True,
            'nocheckcertificate': True,
            'no_warnings': False,
            'prefer_insecure': True,
            'geo_bypass': True,
            'socket_timeout': 30,
            'retries': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        # Try to use external downloader
        if not downloaded:
            try:
                logging.info("Strategy 1: Using external downloader (curl)")
                ydl_opts = {
                    **base_opts,
                    'format': 'bestaudio/best',
                    'outtmpl': f'{output_path}.%(ext)s',
                    'external_downloader': 'curl',
                    'external_downloader_args': ['--insecure', '--retry', '10'],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': AUDIO_FORMAT,
                        'preferredquality': audio_quality.replace('k', ''),
                    }]
                }
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._download_with_options, url, ydl_opts)
                downloaded = True
                logging.info("Strategy 1 succeeded")
            except Exception as e:
                error_msg = f"Strategy 1 failed: {str(e)}"
                logging.error(error_msg)
                error_messages.append(error_msg)
        
        # Try with iOS client
        if not downloaded:
            try:
                logging.info("Strategy 2: Using iOS client")
                ydl_opts = {
                    **base_opts,
                    'format': 'bestaudio/best',
                    'outtmpl': f'{output_path}.%(ext)s',
                    'extractor_args': {'youtube': {'player_client': ['ios']}},
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': AUDIO_FORMAT,
                        'preferredquality': audio_quality.replace('k', ''),
                    }]
                }
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._download_with_options, url, ydl_opts)
                downloaded = True
                logging.info("Strategy 2 succeeded")
            except Exception as e:
                error_msg = f"Strategy 2 failed: {str(e)}"
                logging.error(error_msg)
                error_messages.append(error_msg)
        
        # Try with tvhtml5 client
        if not downloaded:
            try:
                logging.info("Strategy 3: Using tvhtml5 client")
                ydl_opts = {
                    **base_opts,
                    'format': 'bestaudio/best',
                    'outtmpl': f'{output_path}.%(ext)s',
                    'extractor_args': {'youtube': {'player_client': ['tvhtml5']}},
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': AUDIO_FORMAT,
                        'preferredquality': audio_quality.replace('k', ''),
                    }]
                }
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._download_with_options, url, ydl_opts)
                downloaded = True
                logging.info("Strategy 3 succeeded")
            except Exception as e:
                error_msg = f"Strategy 3 failed: {str(e)}"
                logging.error(error_msg)
                error_messages.append(error_msg)
        
        # If all strategies failed, raise exception with all error messages
        if not downloaded:
            raise Exception(f"All download strategies failed: {'; '.join(error_messages)}")
        
        # Process duration limit if needed
        if duration != 'full_video':
            return await self._process_duration_limit(f"{output_path}.{AUDIO_FORMAT}", duration)
        
        return f"{output_path}.{AUDIO_FORMAT}"
    
    async def _get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information using yt-dlp
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary with video information
        """
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'skip_download': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'prefer_insecure': True,
                'geo_bypass': True,
                'extractor_args': {'youtube': {'player_client': ['ios']}},
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                }
            }
            
            loop = asyncio.get_event_loop()
            info_dict = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )
            return info_dict
        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            # Return minimal info when extraction fails
            return {
                'title': 'Unknown',
                'duration': 0
            }
    
    def _download_with_options(self, url: str, options: Dict[str, Any]) -> None:
        """
        Download with yt-dlp using specified options
        
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
        duration_limits = {
            'first_5_minutes': 5 * 60 * 1000,
            'first_10_minutes': 10 * 60 * 1000,
            'first_30_minutes': 30 * 60 * 1000,
            'first_60_minutes': 60 * 60 * 1000
        }
        
        limit_ms = duration_limits.get(duration, None)
        if not limit_ms:
            return audio_path
        
        output_path = audio_path.replace(f".{AUDIO_FORMAT}", f"_{duration}.{AUDIO_FORMAT}")
        
        if os.path.exists(output_path):
            return output_path
        
        loop = asyncio.get_event_loop()
        sound = await loop.run_in_executor(None, AudioSegment.from_file, audio_path)
        trimmed_sound = sound[:limit_ms]
        await loop.run_in_executor(
            None,
            lambda: trimmed_sound.export(output_path, format=AUDIO_FORMAT)
        )
        
        return output_path
