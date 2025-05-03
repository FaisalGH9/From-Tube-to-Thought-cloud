"""
YouTube service for downloading and processing videos
"""
import os
import re
import hashlib
import asyncio
import json
import subprocess
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
    YT_USER_AGENT,
    FORCE_YT_DLP_UPDATE
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

# Force update yt-dlp if setting enabled
if FORCE_YT_DLP_UPDATE:
    try:
        print("Updating yt-dlp to latest version...")
        result = subprocess.run(["pip", "install", "--upgrade", "yt-dlp"], capture_output=True, text=True)
        print(f"yt-dlp update result: {result.stdout}")
        if result.stderr:
            print(f"yt-dlp update errors: {result.stderr}")
    except Exception as e:
        print(f"Error updating yt-dlp: {str(e)}")

class YouTubeService:
    """Handles YouTube video downloading and metadata extraction"""
    
    def extract_video_id(self, url: str) -> str:
        youtube_regex = r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|embed\/|v\/|shorts\/))([^?&"\'>]+)'
        match = re.search(youtube_regex, url)
        if match:
            return match.group(4)
        return hashlib.md5(url.encode()).hexdigest()
    
    async def verify_video_exists(self, url: str) -> bool:
        """Check if a video exists and is accessible via direct HTTP head request"""
        video_id = self.extract_video_id(url)
        check_url = f"https://www.youtube.com/watch?v={video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Try with cookies if available
        cookies = {}
        if os.path.exists(COOKIES_PATH):
            try:
                with open(COOKIES_PATH, 'r') as f:
                    for line in f:
                        if not line.startswith('#') and line.strip():
                            fields = line.strip().split('\t')
                            if len(fields) >= 7:  # Netscape format
                                domain, flag, path, secure, expiration, name, value = fields
                                if 'youtube.com' in domain:
                                    cookies[name] = value
            except Exception as e:
                print(f"Error parsing cookies for verification: {str(e)}")
        
        try:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.head(check_url, headers=headers, cookies=cookies) as response:
                        return response.status == 200
            except ImportError:
                # Fall back to synchronous requests if aiohttp not available
                import requests
                response = requests.head(check_url, headers=headers, cookies=cookies)
                return response.status_code == 200
        except Exception as e:
            print(f"Error checking video existence: {str(e)}")
            # Fall back to a simple existence check
            return True  # Assume it exists and let yt-dlp handle the error
    
    async def download_with_multiple_strategies(self, url, output_path, audio_quality):
        """Try multiple download strategies in sequence to handle difficult videos"""
        strategies = [
            # Strategy 1: Standard with cookies (desktop)
            {
                'format': 'bestaudio/best',
                'outtmpl': f'{output_path}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AUDIO_FORMAT,
                    'preferredquality': audio_quality.replace('k', ''),
                }],
                'quiet': False,
                'verbose': True,
                'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
            },
            
            # Strategy 2: Android client (no cookies)
            {
                'format': 'bestaudio/best',
                'outtmpl': f'{output_path}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AUDIO_FORMAT,
                    'preferredquality': audio_quality.replace('k', ''),
                }],
                'quiet': False,
                'verbose': True,
                'user_agent': 'Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage', 'configs', 'js']
                    }
                },
            },
            
            # Strategy 3: YouTube Music client
            {
                'format': 'bestaudio/best',
                'outtmpl': f'{output_path}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AUDIO_FORMAT,
                    'preferredquality': audio_quality.replace('k', ''),
                }],
                'quiet': False,
                'verbose': True,
                'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios'],
                    }
                },
            },
            
            # Strategy 4: Direct m3u8 extraction with different headers
            {
                'format': 'm3u8/bestaudio/best',
                'outtmpl': f'{output_path}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AUDIO_FORMAT,
                    'preferredquality': audio_quality.replace('k', ''),
                }],
                'quiet': False,
                'verbose': True,
                'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
                'http_headers': {
                    'Origin': 'https://www.youtube.com',
                    'Referer': 'https://www.youtube.com/',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            }
        ]
        
        errors = []
        for i, strategy in enumerate(strategies):
            # Remove None values from strategy
            strategy = {k: v for k, v in strategy.items() if v is not None}
            
            try:
                print(f"Trying download strategy {i+1}/{len(strategies)}...")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._download_with_options, url, strategy)
                
                # Check if download was successful
                if os.path.exists(f"{output_path}.{AUDIO_FORMAT}"):
                    print(f"Strategy {i+1} successful!")
                    return f"{output_path}.{AUDIO_FORMAT}"
            except Exception as e:
                error_msg = str(e)
                errors.append(f"Strategy {i+1} failed: {error_msg}")
                print(errors[-1])
        
        # If we reach here, all strategies failed
        error_details = "\n".join(errors)
        raise Exception(f"All download strategies failed:\n{error_details}")
    
    async def download_audio(self, url: str, options: Dict[str, Any]) -> str:
        video_id = self.extract_video_id(url)
        output_path = os.path.join(MEDIA_DIR, f"{video_id}")
        existing_path = f"{output_path}.{AUDIO_FORMAT}"
        if os.path.exists(existing_path):
            print(f"Using existing audio file: {existing_path}")
            return existing_path
        
        # Check if video exists first
        video_exists = await self.verify_video_exists(url)
        if not video_exists:
            print(f"Video {video_id} appears to be unavailable")
            # We'll still try to download it to confirm
        
        duration = options.get('duration', 'full_video')
        try:
            video_info = await self._get_video_info(url)
            duration_seconds = video_info.get('duration', 0)
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            # Continue with default duration
            duration_seconds = 0
        
        audio_quality = DEFAULT_AUDIO_QUALITY
        if duration_seconds > LONG_VIDEO_THRESHOLD:
            audio_quality = LONG_AUDIO_QUALITY
        
        # Use the multi-strategy approach
        try:
            audio_path = await self.download_with_multiple_strategies(url, output_path, audio_quality)
        except Exception as e:
            # Last resort - try yt-dlp CLI directly as a subprocess
            print(f"All strategies failed, trying direct CLI call as last resort: {str(e)}")
            try:
                # Construct the command
                cmd = [
                    "yt-dlp",
                    "--extract-audio",
                    "--audio-format", AUDIO_FORMAT,
                    "--audio-quality", audio_quality.replace('k', ''),
                    "-o", f"{output_path}.%(ext)s",
                    "--verbose"
                ]
                
                # Add cookies if available
                if os.path.exists(COOKIES_PATH):
                    cmd.extend(["--cookies", COOKIES_PATH])
                
                # Add URL
                cmd.append(url)
                
                # Run the command
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # Log output
                if stdout:
                    print(f"yt-dlp stdout: {stdout.decode()}")
                if stderr:
                    print(f"yt-dlp stderr: {stderr.decode()}")
                
                if process.returncode != 0:
                    raise Exception(f"yt-dlp CLI failed with code {process.returncode}")
                    
                audio_path = f"{output_path}.{AUDIO_FORMAT}"
                
                # Check if file actually exists
                if not os.path.exists(audio_path):
                    raise Exception(f"CLI approach did not create the output file")
                
            except Exception as cli_e:
                print(f"CLI approach also failed: {str(cli_e)}")
                
                # One last attempt - try to diagnose the video
                try:
                    diagnosis = await self.diagnose_video(url)
                    diagnostic_message = diagnosis.get("diagnosis", "Unknown issue with the video")
                    raise Exception(f"All download methods failed. {diagnostic_message}\n\nOriginal error: {str(e)}\n\nCLI error: {str(cli_e)}")
                except:
                    raise Exception(f"All download methods failed. Video may be unavailable: {str(e)}\n\nCLI error: {str(cli_e)}")
        
        if duration != 'full_video':
            return await self._process_duration_limit(audio_path, duration)
        
        return audio_path
    
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
    
    async def diagnose_video(self, url: str) -> Dict[str, Any]:
        """Run diagnostics on a YouTube video to determine accessibility issues"""
        video_id = self.extract_video_id(url)
        result = {
            "video_id": video_id,
            "url": url,
            "tests": []
        }
        
        # Test 1: Basic extraction without cookies
        try:
            ydl_opts = {
                'skip_download': True,
                'quiet': False,
                'verbose': True,
                'no_warnings': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
            }
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )
            result["tests"].append({
                "name": "Basic extraction (no cookies)",
                "status": "success",
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "is_private": info.get("is_private", False),
                "age_restricted": info.get("age_restricted", False)
            })
        except Exception as e:
            result["tests"].append({
                "name": "Basic extraction (no cookies)",
                "status": "failed",
                "error": str(e)
            })
        
        # Test 2: With cookies
        if os.path.exists(COOKIES_PATH):
            try:
                ydl_opts = {
                    'skip_download': True,
                    'quiet': False,
                    'verbose': True,
                    'no_warnings': False,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
                    'cookiefile': COOKIES_PATH
                }
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, 
                    lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
                )
                result["tests"].append({
                    "name": "With cookies",
                    "status": "success",
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "is_private": info.get("is_private", False),
                    "age_restricted": info.get("age_restricted", False)
                })
            except Exception as e:
                result["tests"].append({
                    "name": "With cookies",
                    "status": "failed",
                    "error": str(e)
                })
        
        # Test 3: Android client
        try:
            ydl_opts = {
                'skip_download': True,
                'quiet': False,
                'verbose': True,
                'no_warnings': False,
                'user_agent': 'Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage', 'configs', 'js']
                    }
                }
            }
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
            )
            result["tests"].append({
                "name": "Android client",
                "status": "success",
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "is_private": info.get("is_private", False),
                "formats_available": len(info.get("formats", []))
            })
        except Exception as e:
            result["tests"].append({
                "name": "Android client",
                "status": "failed",
                "error": str(e)
            })
        
        # Add recommendations based on test results
        result["diagnosis"] = self._analyze_diagnosis_results(result["tests"])
        
        return result

    def _analyze_diagnosis_results(self, tests):
        """Analyze diagnostic test results and provide recommendations"""
        all_failed = all(test["status"] == "failed" for test in tests)
        
        if all_failed:
            errors = [test.get("error", "") for test in tests]
            
            if any("private video" in error.lower() for error in errors):
                return "Video is private and requires special access that cannot be obtained via yt-dlp."
            
            if any("this video is unavailable" in error.lower() for error in errors):
                return "Video appears to be unavailable. It may have been deleted, unlisted, or is only available in certain regions."
            
            if any("sign in to confirm your age" in error.lower() for error in errors):
                return "Video is age-restricted. Your cookies might not be valid, or the current account lacks age verification."
            
            return "Video is not accessible through any method. It might be permanently unavailable or requires special permissions."
        
        success_tests = [test for test in tests if test["status"] == "success"]
        if success_tests:
            # Find the successful method
            methods = [test["name"] for test in success_tests]
            return f"Video is accessible using: {', '.join(methods)}. Use these methods for downloading."
        
        return "Inconclusive results. Try updating yt-dlp or your cookies."
