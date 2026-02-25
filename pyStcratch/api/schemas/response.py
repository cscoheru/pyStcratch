"""
Common response schemas.
"""
from typing import Optional, Any, Dict
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """Standard API response."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: Optional[str] = None
    detail: Optional[str] = None


class StatisticsResponse(BaseModel):
    """Statistics response."""
    total_articles: int
    valid_articles: int
    by_source: Dict[str, int]
    by_category: Dict[str, int]
    average_quality_score: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    database: Optional[str] = None
    version: str = "1.0.0"


class CrawlRequest(BaseModel):
    """Request to trigger crawler."""
    source: str = "zhihu"
    max_pages: int = Field(1, ge=1, le=10)


class CrawlResponse(BaseModel):
    """Response from crawl trigger."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
