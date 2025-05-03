"""
Vector storage using Pinecone v3 and BM25 hybrid search
"""
import os
import asyncio
from typing import List, Dict, Any

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from rank_bm25 import BM25Okapi
from pinecone import Pinecone, ServerlessSpec

from config.settings import (
    OPENAI_API_KEY,
    EMBEDDINGS_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME
)
from retrieval.chunking import adaptive_text_splitter

class VectorStore:
    def __init__(self):
        # Pinecone client init (v3)
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        if PINECONE_INDEX_NAME not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT)
            )
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=OPENAI_API_KEY,
            model=EMBEDDINGS_MODEL
        )
        self.bm25_indexes = {}

    async def index_transcript(self, transcript_data: Dict[str, Any], video_id: str) -> None:
        transcript_text = transcript_data.get("transcript", "")
        chunks = adaptive_text_splitter(
            transcript_text,
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP
        )

        texts = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "chunk_id": i,
                "video_id": video_id,
                "source": "transcript"
            })

        vectorstore = LangchainPinecone.from_existing_index(
            index_name=PINECONE_INDEX_NAME,
            embedding=self.embeddings,
            namespace=video_id
        )

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: vectorstore.add_texts(texts=texts, metadatas=metadatas)
        )

        docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
        await self._create_bm25_index(docs, video_id)

    async def hybrid_search(
        self,
        video_id: str,
        query: str,
        k: int = 4,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()

        vectorstore = LangchainPinecone.from_existing_index(
            index_name=PINECONE_INDEX_NAME,
            embedding=self.embeddings,
            namespace=video_id
        )

        vector_docs = await loop.run_in_executor(
            None,
            lambda: vectorstore.similarity_search(query, k=k)
        )

        if video_id not in self.bm25_indexes:
            await self._create_bm25_index(vector_docs, video_id)

        bm25_results = await self._bm25_search(video_id, query, k=k)

        combined_results = self._combine_search_results(
            vector_docs, bm25_results, vector_weight=vector_weight
        )

        return self._format_search_results(combined_results[:k])

    def _format_search_results(self, docs: List[Document]) -> List[Dict[str, Any]]:
        return [{"content": doc.page_content} for doc in docs]

    async def _create_bm25_index(self, docs: List[Document], video_id: str) -> None:
        tokenized = [doc.page_content.lower().split() for doc in docs]
        self.bm25_indexes[video_id] = {
            "index": BM25Okapi(tokenized),
            "docs": docs
        }

    async def _bm25_search(self, video_id: str, query: str, k: int = 4) -> List[Document]:
        if video_id not in self.bm25_indexes:
            return []

        index_data = self.bm25_indexes[video_id]
        scores = index_data["index"].get_scores(query.lower().split())
        top_k = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

        return [index_data["docs"][i] for i in top_k]

    def _combine_search_results(
        self,
        vector_docs: List[Document],
        bm25_docs: List[Document],
        vector_weight: float = 0.7
    ) -> List[Document]:
        vector_scores = {
            doc.page_content: 1.0 - (i / len(vector_docs)) for i, doc in enumerate(vector_docs)
        }
        bm25_scores = {
            doc.page_content: 1.0 - (i / len(bm25_docs)) for i, doc in enumerate(bm25_docs)
        }

        all_docs = {doc.page_content: doc for doc in vector_docs + bm25_docs}
        doc_scores = []

        for content, doc in all_docs.items():
            score = (vector_scores.get(content, 0) * vector_weight +
                     bm25_scores.get(content, 0) * (1 - vector_weight))
            doc_scores.append((doc, score))

        doc_scores.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in doc_scores]
