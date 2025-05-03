"""
YouTube service for downloading and processing videos
"""
import os
import re
import hashlib
import asyncio
import json
from typing import Dict, Any, Optional

import yt_dlp
from pydub import AudioSegment

from config.settings import (
    MEDIA_DIR, 
    AUDIO_FORMAT, 
    DEFAULT_AUDIO_QUALITY,
    LONG_AUDIO_QUALITY,
    LONG_VIDEO_THRESHOLD,
    COOKIES_PATH,
    USE_ALTERNATE_AGENTS,
    YT_USER_AGENT
)

# Debug information at startup
print(f"YouTube Service Initialization:")
print(f"Current Working Directory: {os.getcwd()}")
print(f"COOKIES_PATH set to: {COOKIES_PATH}")
print(f"COOKIES_PATH exists: {os.path.exists(COOKIES_PATH)}")
if os.path.exists(COOKIES_PATH):
    try:
        with open(COOKIES_PATH, 'r') as f:
            cookies_preview = f.read(50)
            print(f"Cookie file preview (first 50 chars): {cookies_preview}...")
    except Exception as e:
        print(f"Error reading cookie file: {str(e)}")

class YouTubeService:
    """Handles YouTube video downloading and metadata extraction"""
    
    def extract_video_id(self, url: str) -> str:
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"\'>]+)'
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()
    
    async def download_audio(self, url: str, options: Dict[str, Any]) -> str:
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, f"{video_id}")
        existing_path = f"{output_path}.{AUDIO_FORMAT}"
        if os.path.exists(existing_path):
            print(f"Using existing audio file: {existing_path}")
            return existing_path
            
        duration = options.get('duration', 'full_video')
        video_info = await self._get_video_info(url)
        duration_seconds = video_info.get('duration', 0)
        audio_quality = DEFAULT_AUDIO_QUALITY
        if duration_seconds > LONG_VIDEO_THRESHOLD:
            audio_quality = LONG_AUDIO_QUALITY
        
        # Set up download options with better error handling for cookies
        ydl_opts = self._create_download_options(
            output_path=output_path,
            audio_quality=audio_quality,
            debug_prefix="download_audio"
        )
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._download_with_options, url, ydl_opts)
            
            # Check if download was successful
            if not os.path.exists(f"{output_path}.{AUDIO_FORMAT}"):
                # Try again with fallback options if file wasn't created
                print("Initial download failed. Trying fallback method...")
                fallback_opts = self._create_fallback_options(output_path, audio_quality)
                await loop.run_in_executor(None, self._download_with_options, url, fallback_opts)
        except Exception as e:
            print(f"Download error: {str(e)}")
            # Try again with fallback options
            try:
                fallback_opts = self._create_fallback_options(output_path, audio_quality)
                await loop.run_in_executor(None, self._download_with_options, url, fallback_opts)
            except Exception as fallback_e:
                print(f"Fallback download also failed: {str(fallback_e)}")
                raise
        
        if duration != 'full_video':
            return await self._process_duration_limit(f"{output_path}.{AUDIO_FORMAT}", duration)
        
        return f"{output_path}.{AUDIO_FORMAT}"
    
    def _create_download_options(self, output_path, audio_quality, debug_prefix=""):
        """Create download options with proper cookie handling"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_path}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': AUDIO_FORMAT,
                'preferredquality': audio_quality.replace('k', ''),
            }],
            'quiet': False,  # Enable output for debugging
            'verbose': True,  # More detailed output
        }
        
        # Add cookies if file exists
        if os.path.exists(COOKIES_PATH):
            print(f"{debug_prefix}: Using cookies file at {COOKIES_PATH}")
            ydl_opts['cookiefile'] = COOKIES_PATH
            # When using cookies, don't use android client
            ydl_opts['user_agent'] = YT_USER_AGENT
        else:
            print(f"{debug_prefix}: WARNING - No cookies file found at {COOKIES_PATH}")
            # Only use android client when NOT using cookies
            if USE_ALTERNATE_AGENTS:
                ydl_opts['user_agent'] = YT_USER_AGENT
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage', 'configs', 'js']
                    }
                }
        
        return ydl_opts
    
    def _create_fallback_options(self, output_path, audio_quality):
        """Create fallback options for when regular download fails"""
        fallback_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_path}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': AUDIO_FORMAT,
                'preferredquality': audio_quality.replace('k', ''),
            }],
            'quiet': False,
            'verbose': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
            'socket_timeout': 30,
            'retries': 10,
        }
        
        # Only add cookies if file exists
        if os.path.exists(COOKIES_PATH):
            fallback_opts['cookiefile'] = COOKIES_PATH
            # Don't use player_client with cookies
        else:
            # Try without cookies
            fallback_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android'],
                    'player_skip': ['webpage', 'configs', 'js']
                }
            }
        
        return fallback_opts
    
    async def _get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video info with enhanced error handling and debugging"""
        # Base options with appropriate debugging
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,  # Enable output for debugging
            'skip_download': True,
            'no_warnings': False,
            'verbose': True,
        }
        
        # Add cookies if file exists
        cookies_exist = os.path.exists(COOKIES_PATH)
        if cookies_exist:
            print(f"get_video_info: Using cookies file at {COOKIES_PATH}")
            ydl_opts['cookiefile'] = COOKIES_PATH
            ydl_opts['user_agent'] = YT_USER_AGENT
        else:
            print(f"get_video_info: WARNING - No cookies file found at {COOKIES_PATH}")
            # Only use android client when NOT using cookies
            if USE_ALTERNATE_AGENTS:
                ydl_opts['user_agent'] = YT_USER_AGENT
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage', 'configs', 'js']
                    }
                }
        
        loop = asyncio.get_event_loop()
        try:
            print(f"Attempting to extract info for URL: {url}")
            info_dict = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )
            print(f"Successfully extracted info for video: {info_dict.get('title', 'Unknown title')}")
            return info_dict
        except Exception as e:
            print(f"Error extracting video info: {str(e)}")
            # Try with fallback options
            try:
                # Switch strategies - if cookies failed, try without cookies
                # If no cookies were used, try with a different approach
                fallback_opts = {
                    'format': 'bestaudio/best',
                    'quiet': False,
                    'skip_download': True,
                    'no_warnings': False,
                    'verbose': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
                }
                
                # Flip the strategy for fallback
                if cookies_exist:
                    # First attempt used cookies, now try without cookies and with android client
                    fallback_opts['extractor_args'] = {
                        'youtube': {
                            'player_client': ['android'],
                            'player_skip': ['webpage', 'configs', 'js']
                        }
                    }
                    print("Trying fallback without cookies, using android client...")
                else:
                    # First attempt was without cookies or with android client, now try with cookies
                    if os.path.exists(COOKIES_PATH):
                        fallback_opts['cookiefile'] = COOKIES_PATH
                        print("Trying fallback with cookies, without android client...")
                    else:
                        # No cookies available, try a completely different user agent
                        fallback_opts['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
                        print("Trying fallback with iOS user agent...")
                
                info_dict = await loop.run_in_executor(
                    None, 
                    lambda: yt_dlp.YoutubeDL(fallback_opts).extract_info(url, download=False)
                )
                print(f"Fallback method succeeded for video: {info_dict.get('title', 'Unknown title')}")
                return info_dict
            except Exception as fallback_e:
                print(f"Fallback info extraction also failed: {str(fallback_e)}")
                # Return a basic info dict with video ID to allow the process to continue
                return {
                    "id": self.extract_video_id(url),
                    "title": f"Unknown video ({self.extract_video_id(url)})",
                    "duration": 0,
                    "error": str(fallback_e)
                }
    
    def _download_with_options(self, url: str, options: Dict[str, Any]) -> None:
        """Download with options and enhanced debugging"""
        # Add cookie file verification
        if 'cookiefile' in options:
            cookie_path = options['cookiefile']
            if os.path.exists(cookie_path):
                print(f"Cookie file found at: {cookie_path}")
                try:
                    # Print first few characters to verify content
                    with open(cookie_path, 'r') as f:
                        content = f.read(50)
                        print(f"Cookie file preview: {content[:20]}...")
                except Exception as e:
                    print(f"Error reading cookie file: {str(e)}")
            else:
                print(f"WARNING: Cookie file not found at: {cookie_path}")
                # Remove the cookiefile option to avoid errors
                options.pop('cookiefile')
        
        # Print key options for debugging
        debug_options = {k: v for k, v in options.items() if k not in ['postprocessors']}
        print(f"Download options: {json.dumps(debug_options, default=str)}")
        
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Download failed with error: {str(e)}")
            raise
    
    async def _process_duration_limit(self, audio_path: str, duration: str) -> str:
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
        await loop.run_in_executor(None, lambda: trimmed_sound.export(output_path, format=AUDIO_FORMAT))
        return output_path
