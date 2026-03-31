"""
Content creation schemas.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CreateArticleRequest(BaseModel):
    """Request to create a new article using AI."""
    topic: str = Field(..., min_length=1, max_length=200, description="Article topic")
    reference_ids: Optional[List[int]] = Field(
        default_factory=list,
        description="Reference article IDs for context"
    )
    style: str = Field(
        "professional",
        description="Writing style: professional, casual, humorous"
    )
    length: str = Field(
        "medium",
        description="Article length: short, medium, long"
    )
    title_type: str = Field(
        "catchy",
        description="Title style: catchy, descriptive, question"
    )
    target_audience: Optional[str] = Field(
        None,
        description="Target audience description"
    )
    tips: Optional[List[str]] = Field(
        default_factory=list,
        description="Additional tips or requirements"
    )


class CreateArticleResponse(BaseModel):
    """Response for article creation request."""
    task_id: str
    status: str
    message: str


class CreatedArticleResponse(BaseModel):
    """Response for a created article."""
    id: int
    task_id: str
    topic: str
    title: str
    content: str
    style: str
    length: str
    word_count: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CreatedArticleListResponse(BaseModel):
    """Paginated list of created articles."""
    items: List[CreatedArticleResponse]
    total: int
    page: int
    page_size: int


class ExportFormatRequest(BaseModel):
    """Request for export format."""
    format: str = Field(
        "markdown",
        description="Export format: markdown, html, plain"
    )
