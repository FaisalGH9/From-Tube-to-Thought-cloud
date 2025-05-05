"""
Configuration settings for the YouTube AI Assistant C-Version (Cloud Run + Local)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Enable LangSmith tracing if needed
if os.getenv("LANGSMITH_TRACING") == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "default")

# Smart base directory switch: Cloud Run = /tmp, otherwise use project root
if os.getenv("CLOUD_RUN", "false").lower() == "true":
    BASE_DIR = "/tmp"
else:
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

# Chunking
DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 100

# Performance Settings
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))
CACHE_TTL = 86400  # 24 hours

# YouTube audio download settings
AUDIO_FORMAT = "mp3"
DEFAULT_AUDIO_QUALITY = "64k"
LONG_AUDIO_QUALITY = "18k"
LONG_VIDEO_THRESHOLD = 60 * 60  # 60 minutes

# Create folders if needed
for dir_path in [VECTOR_DIR, CACHE_DIR, MEDIA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
