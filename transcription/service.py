import os
import json
import time
from typing import Dict, Any
from openai import AsyncOpenAI
from langdetect import detect

from config.settings import OPENAI_API_KEY, TRANSCRIPTION_MODEL, CACHE_DIR

SUPPORTED_LANGUAGES = {"en", "ar", "es", "it", "sv"}

class TranscriptionService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.cache_dir = os.path.join(CACHE_DIR, "transcripts")
        os.makedirs(self.cache_dir, exist_ok=True)

    async def transcribe(self, audio_path: str, video_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        cache_path = os.path.join(self.cache_dir, f"{video_id}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)

        # ✅ WAIT for file to exist before transcription
        for _ in range(100):  # wait max 5 seconds
            if os.path.exists(audio_path):
                break
            time.sleep(5)
        else:
            raise FileNotFoundError(f"[ERROR] Audio not found after download: {audio_path}")

        with open(audio_path, "rb") as audio_file:
            response = await self.client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=audio_file
            )

        transcript_text = response.text

        try:
            lang = detect(transcript_text)
            language = lang if lang in SUPPORTED_LANGUAGES else "en"
        except:
            language = "en"

        result = {
            "transcript": transcript_text,
            "language": language,
            "video_id": video_id,
            "timestamp": time.time()
        }

        with open(cache_path, "w") as f:
            json.dump(result, f)

        return result
