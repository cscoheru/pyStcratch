"""
Statistics routes - database statistics and metrics.
"""
from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.get("/stats")
async def get_statistics():
    """Get database statistics."""
    try:
        # Try Supabase first
        from storage.supabase_client import SupabaseClient

        supabase = SupabaseClient()
        if supabase.client:
            stats = await supabase.get_statistics()
            return {"success": True, "data": stats}
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")

    # Fallback to SQLite
    try:
        from storage.database import DatabaseManager

        db = DatabaseManager()
        stats = db.get_statistics()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return {"success": False, "error": str(e)}, 500
