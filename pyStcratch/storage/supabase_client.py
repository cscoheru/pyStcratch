"""
Supabase client for database operations.
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

try:
    from supabase import create_client, Client
except ImportError:
    logger.error("supabase package not installed. Run: pip install supabase")
    raise


class SupabaseClient:
    """Supabase client for article and created article operations."""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        self.client: Optional[Client] = None

        if not self.url or not self.key:
            logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
            return

        try:
            self.client = create_client(self.url, self.key)
            logger.info(f"Supabase client initialized: {self.url}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")

    async def get_articles(
        self,
        filters: Dict = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        Get articles with pagination and filtering.

        Args:
            filters: Filter dict (source, category, min_quality, search)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Dict with items, total, page, page_size
        """
        if not self.client:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        try:
            query = self.client.table("articles").select("*")

            # Apply filters
            if filters:
                if filters.get("source"):
                    query = query.eq("source", filters["source"])
                if filters.get("category"):
                    query = query.eq("category", filters["category"])
                if filters.get("min_quality") is not None:
                    query = query.gte("quality_score", filters["min_quality"])
                if filters.get("search"):
                    query = query.or_(f"title.ilike.%{filters['search']}%,content.ilike.%{filters['search']}%")

            # Get total count
            count_result = query.count()
            total = count_result.count if hasattr(count_result, 'count') else 0

            # Apply pagination and execute
            offset = (page - 1) * page_size
            result = query.range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

            return {
                "items": result.data if result.data else [],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            logger.error(f"Failed to get articles: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """Get article by ID."""
        if not self.client:
            return None

        try:
            result = self.client.table("articles").select("*").eq("id", article_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get article {article_id}: {e}")
            return None

    async def create_article(self, article: Dict) -> Dict:
        """Create a new article."""
        if not self.client:
            return {"error": "Supabase client not initialized"}

        try:
            # Handle category_path - convert list to JSON string if needed
            category_path = article.get("category_path")
            if isinstance(category_path, list):
                import json
                article["category_path"] = json.dumps(category_path, ensure_ascii=False)

            result = self.client.table("articles").insert(article).execute()
            return result.data[0] if result.data else {"error": "Failed to create"}
        except Exception as e:
            logger.error(f"Failed to create article: {e}")
            return {"error": str(e)}

    async def create_articles_batch(self, articles: List[Dict]) -> Dict:
        """Batch create articles."""
        if not self.client:
            return {"success": 0, "failed": len(articles), "errors": ["Supabase not initialized"]}

        try:
            import json

            # Prepare articles
            prepared = []
            for article in articles:
                category_path = article.get("category_path")
                if isinstance(category_path, list):
                    article["category_path"] = json.dumps(category_path, ensure_ascii=False)
                prepared.append(article)

            result = self.client.table("articles").insert(prepared).execute()
            return {
                "success": len(result.data) if result.data else 0,
                "failed": len(articles) - (len(result.data) if result.data else 0),
                "errors": []
            }
        except Exception as e:
            logger.error(f"Failed to batch create articles: {e}")
            return {"success": 0, "failed": len(articles), "errors": [str(e)]}

    async def update_article(self, article_id: int, data: Dict) -> Optional[Dict]:
        """Update an article."""
        if not self.client:
            return None

        try:
            result = self.client.table("articles").update(data).eq("id", article_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update article {article_id}: {e}")
            return None

    async def delete_articles(self, article_ids: List[int]) -> bool:
        """Delete articles by IDs."""
        if not self.client:
            return False

        try:
            self.client.table("articles").delete().in_("id", article_ids).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete articles: {e}")
            return False

    async def get_articles_by_ids(self, ids: List[int]) -> List[Dict]:
        """Get articles by list of IDs."""
        if not self.client or not ids:
            return []

        try:
            result = self.client.table("articles").select("*").in_("id", ids).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get articles by IDs: {e}")
            return []

    async def get_recent_articles(
        self,
        hours: int = 24,
        min_quality: float = 0.6
    ) -> List[Dict]:
        """Get recent articles within hours and above quality threshold."""
        if not self.client:
            return []

        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            result = (
                self.client.table("articles")
                .select("*")
                .gte("created_at", since.isoformat())
                .gte("quality_score", min_quality)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get recent articles: {e}")
            return []

    async def get_statistics(self) -> Dict:
        """Get database statistics."""
        if not self.client:
            return self._empty_stats()

        try:
            # Total articles
            total_result = self.client.table("articles").select("id", count="exact").execute()
            total = total_result.count if hasattr(total_result, 'count') else 0

            # Valid articles
            valid_result = self.client.table("articles").select("id", count="exact").eq("is_valid", True).execute()
            valid = valid_result.count if hasattr(valid_result, 'count') else 0

            # By source
            by_source = {}
            for source in ["zhihu", "toutiao", "wechat"]:
                result = self.client.table("articles").select("id", count="exact").eq("source", source).execute()
                count = result.count if hasattr(result, 'count') else 0
                by_source[source] = count

            # By category
            by_category = {}
            for category in ["psychology", "management", "finance", "other"]:
                result = self.client.table("articles").select("id", count="exact").eq("category", category).execute()
                count = result.count if hasattr(result, 'count') else 0
                by_category[category] = count

            # Average quality score
            agg_result = self.client.table("articles").select("quality_score").execute()
            avg_quality = 0
            if agg_result.data:
                scores = [a.get("quality_score", 0) for a in agg_result.data if a.get("quality_score")]
                avg_quality = sum(scores) / len(scores) if scores else 0

            return {
                "total_articles": total,
                "valid_articles": valid,
                "by_source": by_source,
                "by_category": by_category,
                "average_quality_score": round(avg_quality, 2)
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return self._empty_stats()

    def _empty_stats(self) -> Dict:
        """Return empty statistics."""
        return {
            "total_articles": 0,
            "valid_articles": 0,
            "by_source": {"zhihu": 0, "toutiao": 0, "wechat": 0},
            "by_category": {"psychology": 0, "management": 0, "finance": 0, "other": 0},
            "average_quality_score": 0
        }

    # Created articles (for content creation feature)
    async def create_created_article(self, article: Dict) -> Dict:
        """Create a generated article."""
        if not self.client:
            return {"error": "Supabase client not initialized"}

        try:
            result = self.client.table("created_articles").insert(article).execute()
            return result.data[0] if result.data else {"error": "Failed to create"}
        except Exception as e:
            logger.error(f"Failed to create created article: {e}")
            return {"error": str(e)}

    async def get_created_articles(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """Get created articles with pagination."""
        if not self.client:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        try:
            offset = (page - 1) * page_size
            result = (
                self.client.table("created_articles")
                .select("*")
                .range(offset, offset + page_size - 1)
                .order("created_at", desc=True)
                .execute()
            )
            return {
                "items": result.data if result.data else [],
                "total": len(result.data) if result.data else 0,
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            logger.error(f"Failed to get created articles: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def update_created_article(self, article_id: int, data: Dict) -> Optional[Dict]:
        """Update a created article."""
        if not self.client:
            return None

        try:
            result = self.client.table("created_articles").update(data).eq("id", article_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update created article {article_id}: {e}")
            return None
