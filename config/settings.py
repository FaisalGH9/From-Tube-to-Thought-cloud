"""
Configuration settings for the YouTube AI Assistant C-Version
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import tempfile

load_dotenv()

# Cookie handling with multiple fallbacks
COOKIES_CONTENT = os.getenv("YOUTUBE_COOKIES", "")
COOKIES_PATH = os.path.join(os.getcwd(), "cookies.txt")
RENDER_COOKIES_PATH = "/opt/render/project/src/cookies.txt"

# Determine if we're in Render environment
IS_RENDER = os.getenv("RENDER", "").lower() == "true"

# Choose the appropriate path based on environment
if IS_RENDER and os.path.exists(RENDER_COOKIES_PATH):
    COOKIES_PATH = RENDER_COOKIES_PATH
    print(f"Using Render cookies path: {COOKIES_PATH}")

# Create cookies file from env var if provided and file doesn't exist
if COOKIES_CONTENT and not os.path.exists(COOKIES_PATH):
    try:
        # Ensure the directory exists
        cookies_dir = os.path.dirname(COOKIES_PATH)
        os.makedirs(cookies_dir, exist_ok=True)
        
        with open(COOKIES_PATH, 'w') as f:
            f.write(COOKIES_CONTENT)
        print(f"Created cookies file at {COOKIES_PATH} from environment variable")
    except Exception as e:
        print(f"Failed to create cookies file from env var: {str(e)}")
        # Fallback to a temporary file
        try:
            temp_cookie = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            temp_cookie.write(COOKIES_CONTENT.encode())
            temp_cookie.close()
            COOKIES_PATH = temp_cookie.name
            print(f"Created temporary cookies file at {COOKIES_PATH}")
        except Exception as temp_e:
            print(f"Failed to create temporary cookies file: {str(temp_e)}")

# Check if cookies file exists and log status
if os.path.exists(COOKIES_PATH):
    file_size = os.path.getsize(COOKIES_PATH)
    print(f"Cookies file exists at {COOKIES_PATH} with size {file_size} bytes")
else:
    print(f"WARNING: Cookies file does not exist at {COOKIES_PATH}")

# Langsmith tracing
if os.getenv("LANGSMITH_TRACING") == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "default")

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
VECTOR_DIR = os.path.join(STORAGE_DIR, "vectors")
CACHE_DIR = os.path.join(STORAGE_DIR, "cache")
MEDIA_DIR = os.path.join(STORAGE_DIR, "media")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")

# LLM Models
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-3.5-turbo")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
TRANSCRIPTION_MODEL = os.getenv("TRANSCRIPTION_MODEL", "whisper-1")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "pcsk_7SCQAy_QtPgWpjvei5NsmcoZ5JvzQne8kUUWimQfgaMVhZyvpKPCtmEHFug6i7bVoqHqgN")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-west-1")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "youtube-index")

DEFAULT_CHUNK_SIZE = 4000
DEFAULT_CHUNK_OVERLAP = 400

# Performance Settings
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))
CACHE_TTL = 86400  # 24 hours (in seconds)

# YouTube download settings
AUDIO_FORMAT = "mp3"
DEFAULT_AUDIO_QUALITY = "64k"
LONG_AUDIO_QUALITY = "18k"  # Lower quality for long videos
LONG_VIDEO_THRESHOLD = 60 * 60  # 60 minutes in seconds

# YouTube anti-bot settings
USE_ALTERNATE_AGENTS = os.getenv("USE_ALTERNATE_AGENTS", "true").lower() == "true"
YT_USER_AGENT = os.getenv("YT_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# Add a setting to force use of the latest yt-dlp version
FORCE_YT_DLP_UPDATE = os.getenv("FORCE_YT_DLP_UPDATE", "true").lower() == "true"

# Ensure storage directories exist
for dir_path in [VECTOR_DIR, CACHE_DIR, MEDIA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
