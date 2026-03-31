"""
Content creation routes - AI-powered article creation.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
import uuid
import asyncio

router = APIRouter()


class CreateArticleRequest(BaseModel):
    """Request to create article."""
    topic: str
    reference_ids: Optional[List[int]] = []
    style: str = "professional"
    length: str = "medium"
    title_type: str = "catchy"
    target_audience: Optional[str] = None
    tips: Optional[List[str]] = []


# In-memory task storage (in production, use Redis or database)
_creation_tasks = {}


@router.post("/create-article")
async def create_article(request: CreateArticleRequest, background_tasks: BackgroundTasks):
    """Create article using AI (background task)."""
    task_id = str(uuid.uuid4())

    # Initialize task status
    _creation_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "topic": request.topic,
        "created_at": None,
        "article": None
    }

    # Run in background
    background_tasks.add_task(_run_article_creation, task_id, request)

    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "status": "pending",
            "message": "Article creation task started"
        }
    }


@router.get("/create-article/{task_id}")
async def get_creation_status(task_id: str):
    """Get article creation task status."""
    if task_id not in _creation_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _creation_tasks[task_id]
    return {
        "success": True,
        "data": task
    }


@router.get("/created-articles")
async def get_created_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get list of created articles."""
    try:
        from storage.supabase_client import SupabaseClient

        supabase = SupabaseClient()
        if supabase.client:
            result = await supabase.get_created_articles(page=page, page_size=page_size)
            return {"success": True, "data": result}

        # Fallback: return in-memory tasks
        items = list(_creation_tasks.values())
        return {
            "success": True,
            "data": {
                "items": items,
                "total": len(items),
                "page": page,
                "page_size": page_size
            }
        }

    except Exception as e:
        logger.error(f"Failed to get created articles: {e}")
        return {"success": False, "error": str(e)}, 500


@router.post("/created-articles/{article_id}/export")
async def export_created_article(article_id: int, format: str = "markdown"):
    """Export created article in specified format."""
    try:
        from creator.wechat_formatter import WeChatFormatter

        # Get article (placeholder - would fetch from database)
        article = {
            "id": article_id,
            "title": "Sample Article",
            "content": "Sample content here..."
        }

        formatter = WeChatFormatter()

        if format == "markdown":
            content = formatter.to_markdown(article)
        elif format == "html":
            content = formatter.to_html(article)
        elif format == "plain":
            content = formatter.to_plain_text(article)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        return {
            "success": True,
            "data": {
                "content": content,
                "format": format
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export article: {e}")
        return {"success": False, "error": str(e)}, 500


async def _run_article_creation(task_id: str, request: CreateArticleRequest):
    """Background task for article creation."""
    try:
        _creation_tasks[task_id]["status"] = "processing"

        # Get reference articles
        reference_articles = []
        if request.reference_ids:
            from storage.supabase_client import SupabaseClient
            supabase = SupabaseClient()
            reference_articles = await supabase.get_articles_by_ids(request.reference_ids)

        # Create article (placeholder - would use actual AI)
        await asyncio.sleep(2)  # Simulate processing

        _creation_tasks[task_id].update({
            "status": "completed",
            "article": {
                "id": task_id,
                "topic": request.topic,
                "title": f"AI Generated: {request.topic}",
                "content": "This is a placeholder for AI-generated content...",
                "style": request.style,
                "length": request.length
            }
        })

        logger.info(f"Article creation completed: {task_id}")

    except Exception as e:
        logger.error(f"Article creation failed: {e}")
        _creation_tasks[task_id]["status"] = "failed"
        _creation_tasks[task_id]["error"] = str(e)
