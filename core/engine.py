import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List, Union

from services.youtube import YouTubeService
from transcription.service import TranscriptionService
from retrieval.vector_store import VectorStore
from llm.provider import LLMProvider
from cache.manager import CacheManager
from config.settings import DEFAULT_MODEL
from langdetect import detect


class ProcessingEngine:
    def __init__(self):
        self.youtube_service = YouTubeService()
        self.transcription = TranscriptionService()
        self.vector_store = VectorStore()
        self.llm_provider = LLMProvider()
        self.cache_manager = CacheManager()

    async def process_video(self, video_url: str, options: Dict[str, Any]) -> str:
        video_id = self.youtube_service.extract_video_id(video_url)

        if self.cache_manager.has_processed_video(video_id):
            return video_id

        audio_path = await self.youtube_service.download_audio(video_url, options)
        transcript_data = await self.transcription.transcribe(audio_path, video_id, options)
        await self.vector_store.index_transcript(transcript_data, video_id)
        self.cache_manager.mark_video_processed(video_id)

        return video_id

    async def query_video(
        self,
        video_id: str,
        query: str,
        stream: bool = True,
        options: Dict[str, Any] = {}
    ) -> Union[str, AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        original_query = query
        try:
            query_lang = detect(query)
        except:
            query_lang = "en"

        needs_translation = query_lang != "en"

        if needs_translation:
            query = await self.llm_provider.translate(query, target_lang="en")

        cached_response = self.cache_manager.get_cached_response(video_id, original_query)
        if cached_response:
            if stream:
                async def yield_cached():
                    yield {
                        "token": cached_response,
                        "is_complete": True,
                        "processed_response": cached_response
                    }
                return yield_cached()
            else:
                return {
                    "response": cached_response,
                    "hallucination": None,
                    "relevance": None
                }

        # Get search method and set vector weight
        search_method = options.get("search_method", "hybrid")
        vector_weight = {
            "vector": 1.0,
            "keyword": 0.0,
            "hybrid": 0.7
        }.get(search_method, 0.7)

        context_data = await self.vector_store.hybrid_search(video_id, query, k=2, vector_weight=vector_weight)

        if stream:
            async def process_stream():
                full_response = ""
                async for chunk in self.llm_provider.stream_response(
                    query,
                    context_data,
                    video_id=video_id,
                    model=options.get("model", DEFAULT_MODEL),
                    max_tokens=300
                ):
                    if not chunk["is_complete"]:
                        full_response += chunk["token"]
                        yield chunk
                    else:
                        processed_response = chunk.get("processed_response", full_response)

                        if needs_translation:
                            processed_response = await self.llm_provider.translate(processed_response, target_lang=query_lang)

                        self.cache_manager.cache_response(video_id, original_query, processed_response)
                        yield {
                            "token": "",
                            "is_complete": True,
                            "processed_response": processed_response
                        }

            return process_stream()

        else:
            result = await self.llm_provider.generate(
                query,
                context_data,
                video_id=video_id,
                model=options.get("model", DEFAULT_MODEL),
                max_tokens=400
            )
            processed_response = result["response"]

            if needs_translation:
                processed_response = await self.llm_provider.translate(processed_response, target_lang=query_lang)

            self.cache_manager.cache_response(video_id, original_query, processed_response)

            return {
                "response": processed_response,
            }

    async def summarize_video(self, video_id: str, length: str = "medium") -> str:
        cached_summary = self.cache_manager.get_cached_response(video_id, f"summarize {length}")
        if cached_summary:
            return cached_summary

        all_chunks = await self.vector_store.hybrid_search(video_id, "full transcript", k=2)
        full_content = "\n\n".join([chunk["content"] for chunk in all_chunks])

        if not full_content.strip():
            print("[WARNING] Transcript is empty, skipping summarization.")
            return ""

        summary = await self.llm_provider.summarize(full_content, length)
        self.cache_manager.cache_response(video_id, f"summarize {length}", summary)

        return summary
