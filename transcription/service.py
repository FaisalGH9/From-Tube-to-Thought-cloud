"""
Transcription service with language detection using langdetect
"""
import os
import asyncio
import json
import time
from typing import Dict, Any

from openai import AsyncOpenAI
from pydub import AudioSegment
from langdetect import detect

from config.settings import (
    OPENAI_API_KEY,
    TRANSCRIPTION_MODEL,
    CACHE_DIR
)

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

        audio = AudioSegment.from_file(audio_path)
        total_duration_ms = len(audio)

        if total_duration_ms < 10 * 60 * 1000:
            result = await self._transcribe_simple(audio_path)
        else:
            result = await self._transcribe_parallel(audio_path, video_id, options.get("parallelization", 3))

        self._save_to_cache(video_id, result)
        return result

    async def _transcribe_simple(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as audio_file:
            response = await self.client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=audio_file
            )

        transcript_text = response.text
        try:
            detected_lang = detect(transcript_text)
            language = detected_lang if detected_lang in SUPPORTED_LANGUAGES else "en"
            if detected_lang not in SUPPORTED_LANGUAGES:
                print(f"[langdetect] Detected unsupported language '{detected_lang}', defaulting to English.")
        except Exception as e:
            print(f"[langdetect] Detection failed: {e}")
            language = "en"

        return {
            "transcript": transcript_text,
            "language": language
        }

    async def _transcribe_parallel(self, audio_path: str, video_id: str, max_parallel: int) -> Dict[str, Any]:
        chunk_size_ms = 5 * 60 * 1000
        audio = AudioSegment.from_file(audio_path)
        total_duration_ms = len(audio)
        chunk_count = (total_duration_ms + chunk_size_ms - 1) // chunk_size_ms

        temp_dir = os.path.join(self.cache_dir, f"temp_{video_id}")
        os.makedirs(temp_dir, exist_ok=True)

        semaphore = asyncio.Semaphore(max_parallel)
        tasks = []

        async def process_chunk(i: int) -> str:
            async with semaphore:
                start = i * chunk_size_ms
                end = min((i + 1) * chunk_size_ms, total_duration_ms)
                chunk = audio[start:end]
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
                chunk.export(chunk_path, format="mp3")

                try:
                    with open(chunk_path, "rb") as audio_file:
                        response = await self.client.audio.transcriptions.create(
                            model=TRANSCRIPTION_MODEL,
                            file=audio_file
                        )
                        return response.text
                finally:
                    os.remove(chunk_path)

        for i in range(chunk_count):
            tasks.append(process_chunk(i))

        results = await asyncio.gather(*tasks)
        full_transcript = " ".join(results)

        try:
            detected_lang = detect(full_transcript)
            language = detected_lang if detected_lang in SUPPORTED_LANGUAGES else "en"
            if detected_lang not in SUPPORTED_LANGUAGES:
                print(f"[langdetect] Detected unsupported language '{detected_lang}' in long transcript, defaulting to English.")
        except Exception as e:
            print(f"[langdetect] Detection failed on long transcript: {e}")
            language = "en"

        try:
            os.rmdir(temp_dir)
        except:
            pass

        return {
            "transcript": full_transcript,
            "language": language
        }

    def _save_to_cache(self, video_id: str, result: Dict[str, Any]) -> None:
        cache_path = os.path.join(self.cache_dir, f"{video_id}.json")
        result["video_id"] = video_id
        result["timestamp"] = time.time()

        with open(cache_path, "w") as f:
            json.dump(result, f)
