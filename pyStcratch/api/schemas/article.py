"""
Article schemas for requests and responses.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ArticleBase(BaseModel):
    """Base article schema."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    author: Optional[str] = Field(None, max_length=200)
    url: Optional[str] = None
    source: str = Field(..., max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    subcategory: Optional[str] = Field(None, max_length=50)
    sub_subcategory: Optional[str] = Field(None, max_length=50)
    quality_score: Optional[float] = Field(0.0, ge=0, le=1)


class ArticleResponse(ArticleBase):
    """Full article response."""
    id: int
    article_id: str
    publish_time: Optional[datetime] = None
    category_path: Optional[List[str]] = []
    confidence: float = 0.0
    is_valid: bool = True
    is_spam: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArticleFilter(BaseModel):
    """Filter for article queries."""
    source: Optional[str] = None
    category: Optional[str] = None
    min_quality: Optional[float] = Field(None, ge=0, le=1)
    search: Optional[str] = None


class ArticleListResponse(BaseModel):
    """Paginated article list response."""
    items: List[ArticleResponse]
    total: int
    page: int
    page_size: int


class SimilarArticle(BaseModel):
    """Similar article from semantic search."""
    id: str
    score: float
    title: str
    content: str
    source: str
    category: Optional[str] = None
