from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class WebsiteConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Unique name for the website configuration")
    domain: str = Field(..., description="Domain of the website")
    base_url: HttpUrl = Field(..., description="Base URL of the website")
    
    # Default scraping configuration
    default_method: str = Field(default="requests", description="Default scraping method")
    default_selectors: Optional[Dict[str, str]] = Field(None, description="Default CSS/XPath selectors")
    default_headers: Optional[Dict[str, str]] = Field(None, description="Default HTTP headers")
    default_cookies: Optional[Dict[str, str]] = Field(None, description="Default cookies")
    
    # Rate limiting and behavior
    rate_limit_delay: int = Field(default=1, ge=0, le=60, description="Delay between requests in seconds")
    max_concurrent_requests: int = Field(default=1, ge=1, le=10, description="Maximum concurrent requests")
    respect_robots_txt: bool = Field(default=True, description="Whether to respect robots.txt")
    
    # Browser-specific settings
    requires_js: bool = Field(default=False, description="Whether the site requires JavaScript")
    wait_for_element: Optional[str] = Field(None, description="CSS selector to wait for")
    page_load_timeout: int = Field(default=30, ge=5, le=120, description="Page load timeout in seconds")
    
    # Anti-bot measures
    needs_proxy: bool = Field(default=False, description="Whether proxy is required")
    rotate_user_agents: bool = Field(default=False, description="Whether to rotate user agents")
    custom_user_agents: Optional[List[str]] = Field(None, description="List of custom user agents")
    
    # Content parsing rules
    pagination_selector: Optional[str] = Field(None, description="CSS selector for pagination")
    max_pages: int = Field(default=1, ge=1, le=1000, description="Maximum pages to scrape")
    content_filters: Optional[Dict[str, Any]] = Field(None, description="Content filtering rules")
    
    # Validation rules
    required_elements: Optional[List[str]] = Field(None, description="Required CSS selectors that must be present")
    blocked_keywords: Optional[List[str]] = Field(None, description="Keywords that indicate scraping failure")
    
    # Description and notes
    description: Optional[str] = Field(None, description="Description of the website")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('default_method')
    def validate_default_method(cls, v):
        allowed_methods = ['requests', 'selenium', 'playwright', 'scrapy']
        if v not in allowed_methods:
            raise ValueError(f'Method must be one of: {allowed_methods}')
        return v

class WebsiteConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    domain: Optional[str] = None
    base_url: Optional[HttpUrl] = None
    
    # Default scraping configuration
    default_method: Optional[str] = None
    default_selectors: Optional[Dict[str, str]] = None
    default_headers: Optional[Dict[str, str]] = None
    default_cookies: Optional[Dict[str, str]] = None
    
    # Rate limiting and behavior
    rate_limit_delay: Optional[int] = Field(None, ge=0, le=60)
    max_concurrent_requests: Optional[int] = Field(None, ge=1, le=10)
    respect_robots_txt: Optional[bool] = None
    
    # Browser-specific settings
    requires_js: Optional[bool] = None
    wait_for_element: Optional[str] = None
    page_load_timeout: Optional[int] = Field(None, ge=5, le=120)
    
    # Anti-bot measures
    needs_proxy: Optional[bool] = None
    rotate_user_agents: Optional[bool] = None
    custom_user_agents: Optional[List[str]] = None
    
    # Content parsing rules
    pagination_selector: Optional[str] = None
    max_pages: Optional[int] = Field(None, ge=1, le=1000)
    content_filters: Optional[Dict[str, Any]] = None
    
    # Validation rules
    required_elements: Optional[List[str]] = None
    blocked_keywords: Optional[List[str]] = None
    
    # Status
    is_active: Optional[bool] = None
    
    # Description and notes
    description: Optional[str] = None
    notes: Optional[str] = None

class WebsiteConfigResponse(BaseModel):
    id: int
    name: str
    domain: str
    base_url: str
    
    # Default scraping configuration
    default_method: str
    default_selectors: Optional[Dict[str, Any]] = None
    default_headers: Optional[Dict[str, Any]] = None
    default_cookies: Optional[Dict[str, Any]] = None
    
    # Rate limiting and behavior
    rate_limit_delay: int
    max_concurrent_requests: int
    respect_robots_txt: bool
    
    # Browser-specific settings
    requires_js: bool
    wait_for_element: Optional[str] = None
    page_load_timeout: int
    
    # Anti-bot measures
    needs_proxy: bool
    rotate_user_agents: bool
    custom_user_agents: Optional[List[str]] = None
    
    # Content parsing rules
    pagination_selector: Optional[str] = None
    max_pages: int
    content_filters: Optional[Dict[str, Any]] = None
    
    # Validation rules
    required_elements: Optional[List[str]] = None
    blocked_keywords: Optional[List[str]] = None
    
    # Status
    is_active: bool
    last_successful_scrape: Optional[datetime] = None
    failure_count: int
    
    # Description and notes
    description: Optional[str] = None
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WebsiteConfigList(BaseModel):
    configs: List[WebsiteConfigResponse]
    total: int
    page: int
    size: int
    pages: int