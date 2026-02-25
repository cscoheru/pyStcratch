"""
System routes - health check and system info.
"""
from fastapi import APIRouter, status
from loguru import logger
import os

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "crawler-api",
        "version": "1.0.0",
        "database": os.getenv("SUPABASE_URL", "sqlite:///data/crawler.db")
    }


@router.get("/info")
async def system_info():
    """System information."""
    return {
        "name": "Crawler Data Management API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
