"""
YouTube service for downloading and processing videos using pytube
with fallback to direct requests
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
        
        # Get video info (use simple implementation that doesn't rely on Torch)
        video_info = {
            'duration': 0,  # Default to 0 seconds if we can't determine
            'title': 'Unknown'
        }
        
        try:
            # Try to get basic info without using the problematic pytube methods
            simple_info = await self._get_simple_video_info(url)
            if simple_info:
                video_info = simple_info
        except Exception as e:
            print(f"Simple info retrieval failed: {e}")
        
        duration_seconds = video_info.get('duration', 0)
        
        # Set audio quality based on video length
        audio_quality = DEFAULT_AUDIO_QUALITY
        if duration_seconds > LONG_VIDEO_THRESHOLD:
            audio_quality = LONG_AUDIO_QUALITY
            
        # Try multiple download methods
        downloaded_file = None
        
        # Method 1: Try pytube
        try:
            loop = asyncio.get_event_loop()
            downloaded_file = await loop.run_in_executor(None, self._download_with_pytube, url, output_path)
        except Exception as e:
            print(f"Pytube download failed: {e}")
            
            # Method 2: Try alternative download using requests (bypassing torch)
            try:
                download_path = f"{output_path}.mp4"
                success = await self._download_with_requests(url, download_path)
                if success:
                    downloaded_file = download_path
            except Exception as e2:
                print(f"Alternative download also failed: {e2}")
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception(f"All download methods failed for {url}")
            
        # Convert to requested audio format if needed
        if not downloaded_file.endswith(f".{AUDIO_FORMAT}"):
            audio = AudioSegment.from_file(downloaded_file)
            audio_file = f"{output_path}.{AUDIO_FORMAT}"
            audio.export(audio_file, format=AUDIO_FORMAT, bitrate=audio_quality)
            
            # Remove original file if different
            if downloaded_file != audio_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
                
            downloaded_file = audio_file
        
        # Process duration limits if needed
        if duration != 'full_video':
            return await self._process_duration_limit(downloaded_file, duration)
        
        return downloaded_file
    
    async def _get_simple_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get basic video info without using problematic pytube methods
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary with basic video information
        """
        # Direct HTTP request to get title and possibly duration
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            content = response.text
            
            # Extract title
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(' - YouTube', '') if title_match else 'Unknown'
            
            # We'll use a standard duration since it's hard to extract reliably
            # from HTML only, but we could add more sophisticated extraction later
            return {
                'title': title,
                'duration': 0,  # Default duration
                'source': 'simple_http'
            }
        except Exception as e:
            print(f"Simple info HTTP error: {e}")
            return None
    
    def _download_with_pytube(self, url: str, output_path: str) -> str:
        """
        Download using pytube (sync function for executor)
        
        Args:
            url: YouTube URL
            output_path: Base path for output file (without extension)
            
        Returns:
            Path to downloaded file
        """
        try:
            # Initialize pytube with additional user agent
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
            
            # Add a custom user agent to avoid some blocks
            yt.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Get the best audio stream
            audio_stream = None
            try:
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').last()
            except:
                pass
            
            if not audio_stream:
                # Fall back to any stream with audio
                try:
                    audio_stream = yt.streams.filter(progressive=True).order_by('resolution').first()
                except:
                    pass
            
            if not audio_stream:
                raise Exception(f"No suitable audio stream found for {url}")
            
            # Download the stream
            downloaded_file = audio_stream.download(
                output_path=os.path.dirname(output_path),
                filename=os.path.basename(output_path)
            )
            
            return downloaded_file
        except Exception as e:
            print(f"Pytube download error: {e}")
            raise
    
    async def _download_with_requests(self, url: str, output_path: str) -> bool:
        """
        Alternative download method using direct HTTP requests
        
        Args:
            url: YouTube URL
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        # This is a simple placeholder. In a real implementation, we would 
        # need to implement a way to get the direct media URL and download it.
        # For now, we'll just return False to indicate this method is not fully implemented
        print("Direct download method not implemented yet")
        return False
    
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
