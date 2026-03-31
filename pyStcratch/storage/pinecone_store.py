"""
Pinecone vector database for semantic search.
"""
import os
from typing import List, Dict, Optional
from loguru import logger

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    logger.error("pinecone-client package not installed. Run: pip install pinecone-client")
    raise


class PineconeStore:
    """Pinecone vector store for article embeddings."""

    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "crawler-articles")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))  # OpenAI default
        self.pc: Optional[Pinecone] = None
        self.index = None

        if not self.api_key:
            logger.warning("PINECONE_API_KEY not set")
            return

        try:
            self.pc = Pinecone(api_key=self.api_key)
            self._get_or_create_index()
            logger.info(f"Pinecone initialized: index={self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")

    def _get_or_create_index(self):
        """Get existing index or create new one."""
        try:
            # Check if index exists
            indexes = [idx.name for idx in self.pc.list_indexes()]

            if self.index_name in indexes:
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Using existing index: {self.index_name}")
            else:
                # Create new index
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment
                    )
                )
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Created new index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to get or create index: {e}")

    async def add_vectors(
        self,
        items: List[Dict],
        vectors: List[List[float]]
    ) -> bool:
        """
        Add vectors to Pinecone.

        Args:
            items: List of article dicts with 'id' field
            vectors: List of embedding vectors

        Returns:
            True if successful
        """
        if not self.index or not items or not vectors:
            return False

        try:
            if len(items) != len(vectors):
                logger.error(f"Items and vectors count mismatch: {len(items)} vs {len(vectors)}")
                return False

            # Prepare vectors for upsert
            vectors_to_upsert = []
            for item, vector in zip(items, vectors):
                vector_id = str(item.get("id", ""))
                metadata = {
                    "title": item.get("title", "")[:500],
                    "source": item.get("source", ""),
                    "category": item.get("category", ""),
                    "url": item.get("url", "")
                }
                vectors_to_upsert.append({
                    "id": vector_id,
                    "values": vector,
                    "metadata": metadata
                })

            # Upsert in batches
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(vectors=batch)
                logger.debug(f"Upserted batch of {len(batch)} vectors")

            logger.info(f"Added {len(vectors_to_upsert)} vectors to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter: Dict = None
    ) -> List[Dict]:
        """
        Search for similar articles.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter: Metadata filter (e.g., {"category": "psychology"})

        Returns:
            List of matching articles with scores
        """
        if not self.index or not query_vector:
            return []

        try:
            query_params = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": True
            }

            if filter:
                query_params["filter"] = filter

            results = self.index.query(**query_params)

            matches = []
            for match in results.get("matches", []):
                matches.append({
                    "id": match.get("id"),
                    "score": match.get("score", 0),
                    "metadata": match.get("metadata", {})
                })

            return matches
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    async def search_by_text(
        self,
        query: str,
        embedder,
        top_k: int = 10,
        filter: Dict = None
    ) -> List[Dict]:
        """
        Search by text query (embeds query first).

        Args:
            query: Search query text
            embedder: Embedder instance with embed_text method
            top_k: Number of results
            filter: Metadata filter

        Returns:
            List of matching articles
        """
        try:
            # Generate embedding for query
            query_vector = await embedder.embed_text(query)
            return await self.search(query_vector, top_k, filter)
        except Exception as e:
            logger.error(f"Failed to search by text: {e}")
            return []

    async def delete_by_ids(self, ids: List[str]) -> bool:
        """
        Delete vectors by IDs.

        Args:
            ids: List of vector IDs to delete

        Returns:
            True if successful
        """
        if not self.index or not ids:
            return False

        try:
            self.index.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    async def get_vector_count(self) -> int:
        """Get total number of vectors in index."""
        if not self.index:
            return 0

        try:
            stats = self.index.describe_index_stats()
            return stats.get("total_vector_count", 0)
        except Exception as e:
            logger.error(f"Failed to get vector count: {e}")
            return 0
