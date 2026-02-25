"""
FastAPI application for crawler data management.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    logger.info("Starting FastAPI application...")
    yield
    logger.info("Shutting down FastAPI application...")


# Create FastAPI app
app = FastAPI(
    title="Crawler Data Management API",
    description="API for managing crawled articles, content creation, and semantic search",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (will be created)
try:
    from api.routes import system, articles, statistics, creation, crawl

    app.include_router(system.router, prefix="/api/system", tags=["System"])
    app.include_router(statistics.router, prefix="/api", tags=["Statistics"])
    app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
    app.include_router(creation.router, prefix="/api", tags=["Content Creation"])
    app.include_router(crawl.router, prefix="/api/crawl", tags=["Crawl"])
    logger.info("All routers included successfully")
except ImportError as e:
    logger.warning(f"Some routers not yet implemented: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Crawler Data Management API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Health check (also available via system router)
@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
