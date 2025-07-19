from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class WebsiteConfig(Base):
    __tablename__ = "website_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    base_url = Column(String(2048), nullable=False)
    
    # Default scraping configuration
    default_method = Column(String(20), default="requests")
    default_selectors = Column(JSON, nullable=True)
    default_headers = Column(JSON, nullable=True)
    default_cookies = Column(JSON, nullable=True)
    
    # Rate limiting and behavior
    rate_limit_delay = Column(Integer, default=1)  # seconds between requests
    max_concurrent_requests = Column(Integer, default=1)
    respect_robots_txt = Column(Boolean, default=True)
    
    # Browser-specific settings
    requires_js = Column(Boolean, default=False)
    wait_for_element = Column(String(500), nullable=True)  # CSS selector to wait for
    page_load_timeout = Column(Integer, default=30)
    
    # Anti-bot measures
    needs_proxy = Column(Boolean, default=False)
    rotate_user_agents = Column(Boolean, default=False)
    custom_user_agents = Column(JSON, nullable=True)
    
    # Content parsing rules
    pagination_selector = Column(String(500), nullable=True)
    max_pages = Column(Integer, default=1)
    content_filters = Column(JSON, nullable=True)  # Filters to clean content
    
    # Validation rules
    required_elements = Column(JSON, nullable=True)  # Elements that must be present
    blocked_keywords = Column(JSON, nullable=True)   # Keywords that indicate failure
    
    # Status
    is_active = Column(Boolean, default=True)
    last_successful_scrape = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)
    
    # Description and notes
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    jobs = relationship("ScrapingJob", back_populates="website_config")