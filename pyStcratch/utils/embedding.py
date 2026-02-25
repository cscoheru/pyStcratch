"""
Qwen Embedding API for text vectorization.
"""
import os
from typing import List
from loguru import logger

try:
    import dashscope
except ImportError:
    logger.error("dashscope package not installed. Run: pip install dashscope")
    raise


class QwenEmbedder:
    """Qwen Embedding API client for generating text embeddings."""

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-v2")
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

        if self.api_key:
            dashscope.api_key = self.api_key
            logger.info(f"Qwen Embedder initialized: model={self.model}")
        else:
            logger.warning("DASHSCOPE_API_KEY not set")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        if not self.api_key:
            logger.error("DASHSCOPE_API_KEY not set")
            return []

        try:
            from httpx import AsyncClient
            import json

            # Truncate text if too long (Qwen limit is around 2048 tokens)
            text = self._truncate_text(text, max_length=8000)

            # Call Dashscope API
            response = await self._call_embedding_api([text])

            if response and "data" in response:
                return response["data"][0]["embedding"]

            return []
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            return []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not self.api_key or not texts:
            return []

        try:
            # Truncate texts
            texts = [self._truncate_text(t, max_length=8000) for t in texts]

            # Call Dashscope API (supports up to 25 texts per request)
            embeddings = []
            batch_size = 25

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = await self._call_embedding_api(batch)

                if response and "data" in response:
                    batch_embeddings = [item["embedding"] for item in response["data"]]
                    embeddings.extend(batch_embeddings)

            return embeddings
        except Exception as e:
            logger.error(f"Failed to embed batch: {e}")
            return []

    async def embed_article(self, article: dict) -> List[float]:
        """
        Generate embedding for an article (combines title and content).

        Args:
            article: Article dict with title and content

        Returns:
            Embedding vector
        """
        title = article.get("title", "")
        content = article.get("content", "")

        # Combine title and content for better semantic representation
        combined_text = f"{title}\n\n{content}" if title and content else (title or content)

        return await self.embed_text(combined_text)

    async def _call_embedding_api(self, texts: List[str]) -> dict:
        """Call Dashscope embedding API asynchronously."""
        try:
            from httpx import AsyncClient, HTTPStatusError
            import asyncio

            url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "input": {
                    "texts": texts
                }
            }

            async with AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                return response.json()

        except HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return {}
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {}

    def _truncate_text(self, text: str, max_length: int = 8000) -> str:
        """Truncate text to max length."""
        if not text:
            return ""
        return text[:max_length] if len(text) > max_length else text

    async def vectorize_articles(
        self,
        articles: List[dict],
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Vectorize multiple articles.

        Args:
            articles: List of article dicts
            batch_size: Process in batches

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_embeddings = await self.embed_batch([
                f"{a.get('title', '')}\n\n{a.get('content', '')}"
                for a in batch
            ])
            all_embeddings.extend(batch_embeddings)
            logger.debug(f"Vectorized batch {i//batch_size + 1}/{(len(articles)-1)//batch_size + 1}")

        return all_embeddings
