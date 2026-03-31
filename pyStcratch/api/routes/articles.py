"""
Article routes - CRUD operations and semantic search.
"""
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, List
from loguru import logger

router = APIRouter()


@router.get("")
async def get_articles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(None, description="Filter by source"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_quality: Optional[float] = Query(None, ge=0, le=1, description="Minimum quality score"),
    search: Optional[str] = Query(None, description="Search in title and content")
):
    """Get articles with pagination and filtering."""
    try:
        from storage.supabase_client import SupabaseClient

        supabase = SupabaseClient()
        if not supabase.client:
            # Fallback to SQLite
            from storage.database import DatabaseManager
            db = DatabaseManager()

            filters = {}
            if source:
                filters["source"] = source
            if category:
                filters["category"] = category
            if min_quality is not None:
                filters["min_quality"] = min_quality

            articles = db.get_articles(
                limit=page_size,
                offset=(page - 1) * page_size,
                **filters
            )
            total = len(articles)  # SQLite doesn't have easy count with filters

            return {
                "items": articles,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        # Use Supabase
        filters = {}
        if source:
            filters["source"] = source
        if category:
            filters["category"] = category
        if min_quality is not None:
            filters["min_quality"] = min_quality
        if search:
            filters["search"] = search

        result = await supabase.get_articles(filters=filters, page=page, page_size=page_size)
        return result

    except Exception as e:
        logger.error(f"Failed to get articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{article_id}")
async def get_article(article_id: int):
    """Get article by ID."""
    try:
        from storage.supabase_client import SupabaseClient

        supabase = SupabaseClient()
        if supabase.client:
            article = await supabase.get_article_by_id(article_id)
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            return article

        # Fallback to SQLite
        from storage.database import DatabaseManager
        db = DatabaseManager()
        article = db.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get article: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch")
async def delete_articles(ids: List[int]):
    """Delete articles by IDs."""
    try:
        from storage.supabase_client import SupabaseClient

        supabase = SupabaseClient()
        if supabase.client:
            success = await supabase.delete_articles(ids)
            return {"success": success, "deleted": len(ids) if success else 0}

        # Fallback to SQLite
        from storage.database import DatabaseManager
        db = DatabaseManager()
        deleted = db.delete_articles_batch(ids)
        return {"success": True, "deleted": deleted}

    except Exception as e:
        logger.error(f"Failed to delete articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar")
async def get_similar_articles(
    topic: str = Query(..., description="Search topic"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get similar articles using semantic search."""
    try:
        from storage.pinecone_store import PineconeStore
        from storage.supabase_client import SupabaseClient
        from utils.embedding import QwenEmbedder

        pinecone = PineconeStore()
        embedder = QwenEmbedder()

        if not pinecone.index or not embedder.api_key:
            # Fallback to keyword search
            return await _keyword_search(topic, limit, category)

        # Semantic search
        filter_dict = {"category": category} if category else None
        results = await pinecone.search_by_text(
            query=topic,
            embedder=embedder,
            top_k=limit,
            filter=filter_dict
        )

        # Get full article details
        article_ids = [int(r["id"]) for r in results if r["id"].isdigit()]
        supabase = SupabaseClient()
        articles = await supabase.get_articles_by_ids(article_ids) if article_ids else []

        # Merge results with scores
        article_map = {str(a["id"]): a for a in articles}
        merged = []
        for r in results:
            if r["id"] in article_map:
                merged.append({
                    **article_map[r["id"]],
                    "similarity_score": r["score"]
                })

        return {"items": merged, "total": len(merged)}

    except Exception as e:
        logger.error(f"Failed to get similar articles: {e}")
        # Return empty instead of error
        return {"items": [], "total": 0}


async def _keyword_search(topic: str, limit: int, category: Optional[str]):
    """Fallback keyword search."""
    from storage.supabase_client import SupabaseClient

    supabase = SupabaseClient()
    result = await supabase.get_articles(
        filters={"search": topic, "category": category},
        page=1,
        page_size=limit
    )
    return result
