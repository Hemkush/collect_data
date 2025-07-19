from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class ScrapingMethodEnum(str, Enum):
    REQUESTS = "requests"
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    SCRAPY = "scrapy"

class JobStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScrapingJobCreate(BaseModel):
    url: HttpUrl = Field(..., description="URL to scrape")
    method: ScrapingMethodEnum = Field(default=ScrapingMethodEnum.REQUESTS, description="Scraping method to use")
    
    # Optional configuration
    selectors: Optional[Dict[str, str]] = Field(None, description="CSS/XPath selectors for data extraction")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers")
    cookies: Optional[Dict[str, str]] = Field(None, description="Custom cookies")
    proxy: Optional[str] = Field(None, description="Proxy URL")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    
    # Timing configuration
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    delay_between_requests: int = Field(default=1, ge=0, le=60, description="Delay between requests in seconds")
    
    # Scheduling
    is_recurring: bool = Field(default=False, description="Whether this is a recurring job")
    cron_expression: Optional[str] = Field(None, description="Cron expression for recurring jobs")
    
    # Website configuration
    website_config_id: Optional[int] = Field(None, description="ID of website configuration to use")
    
    @validator('cron_expression')
    def validate_cron_expression(cls, v, values):
        if values.get('is_recurring') and not v:
            raise ValueError('cron_expression is required for recurring jobs')
        return v

class ScrapingJobUpdate(BaseModel):
    status: Optional[JobStatusEnum] = None
    error_message: Optional[str] = None
    scraped_data_count: Optional[int] = None

class ScrapingJobResponse(BaseModel):
    id: int
    url: str
    method: str
    status: str
    
    # Configuration
    selectors: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None
    cookies: Optional[Dict[str, Any]] = None
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Timing
    timeout: int
    max_retries: int
    retry_count: int
    delay_between_requests: int
    
    # Results
    scraped_data_count: int
    error_message: Optional[str] = None
    
    # Scheduling
    is_recurring: bool
    cron_expression: Optional[str] = None
    next_run_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    
    # Website config
    website_config_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class ScrapingJobList(BaseModel):
    jobs: List[ScrapingJobResponse]
    total: int
    page: int
    size: int
    pages: int