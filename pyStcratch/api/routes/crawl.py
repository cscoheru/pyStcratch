"""
Crawl routes - trigger and monitor crawler tasks.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

router = APIRouter()


class CrawlTriggerRequest(BaseModel):
    """Request to trigger crawler."""
    source: str = "zhihu"
    max_pages: int = 1


@router.post("/trigger")
async def trigger_crawl(request: CrawlTriggerRequest, background_tasks: BackgroundTasks):
    """Trigger manual crawl task."""
    try:
        from scheduler.jobs import ManualJobs
        from storage.database import DatabaseManager

        db_manager = DatabaseManager()
        jobs = ManualJobs(db_manager=db_manager)

        logger.info(f"Manual crawl triggered: source={request.source}, max_pages={request.max_pages}")

        # Run crawl in background
        result = jobs.crawl_source(request.source, max_pages=request.max_pages)

        return {
            "success": True,
            "data": {
                "source": request.source,
                "result": result
            }
        }

    except Exception as e:
        logger.error(f"Failed to trigger crawl: {e}")
        return {
            "success": False,
            "error": str(e)
        }, 500


@router.post("/full-sync")
async def run_full_sync(background_tasks: BackgroundTasks):
    """
    Run full sync workflow: crawl → classify → export → vectorize.
    """
    try:
        from storage.database import DatabaseManager

        db_manager = DatabaseManager()
        results = {}

        # 1. Crawl data
        logger.info("Step 1: Crawling data...")
        try:
            from scheduler.jobs import ManualJobs
            jobs = ManualJobs(db_manager=db_manager)

            sources = ["zhihu", "toutiao", "wechat"]
            crawl_results = {}
            for source in sources:
                try:
                    result = jobs.crawl_source(source, max_pages=1)
                    crawl_results[source] = result
                    logger.info(f"Crawled {source}: {result}")
                except Exception as e:
                    logger.error(f"Failed to crawl {source}: {e}")
                    crawl_results[source] = {"error": str(e)}

            results["crawl"] = crawl_results
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            results["crawl"] = {"error": str(e)}

        # 2. Classify articles
        logger.info("Step 2: Classifying articles...")
        try:
            from scheduler.jobs import CrawlerScheduler
            import asyncio

            scheduler = CrawlerScheduler(db_manager=db_manager)
            await asyncio.run(scheduler._classify_articles_job())
            results["classify"] = {"success": True}
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            results["classify"] = {"error": str(e)}

        # 3. Get final stats
        logger.info("Step 3: Getting stats...")
        try:
            stats = db_manager.get_statistics()
            results["stats"] = stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            results["stats"] = {"error": str(e)}

        logger.info(f"Full sync completed: {results}")

        return {
            "success": True,
            "data": results
        }

    except Exception as e:
        logger.error(f"Full sync failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }, 500


@router.get("/status/{job_id}")
async def get_crawl_status(job_id: str):
    """Get crawl job status (placeholder)."""
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Crawl job completed"
    }
