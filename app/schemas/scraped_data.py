from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ScrapedDataResponse(BaseModel):
    id: int
    job_id: int
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    
    # Structured data
    structured_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    status_code: Optional[int] = None
    response_headers: Optional[Dict[str, Any]] = None
    
    # Content analysis
    word_count: Optional[int] = None
    image_count: Optional[int] = None
    link_count: Optional[int] = None
    
    # Timestamps
    scraped_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScrapedDataList(BaseModel):
    data: List[ScrapedDataResponse]
    total: int
    page: int
    size: int
    pages: int

class ScrapedDataSummary(BaseModel):
    job_id: int
    total_items: int
    avg_content_length: Optional[float] = None
    total_words: Optional[int] = None
    unique_domains: int
    scraped_at_range: Dict[str, datetime]  # first and last scraped dates
    
class ContentAnalysis(BaseModel):
    url: str
    title: Optional[str] = None
    word_count: int
    image_count: int
    link_count: int
    main_content_length: int
    extracted_links: List[str] = Field(default_factory=list)
    extracted_images: List[str] = Field(default_factory=list)
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)