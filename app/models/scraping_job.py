from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScrapingMethod(str, enum.Enum):
    REQUESTS = "requests"
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    SCRAPY = "scrapy"

class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), nullable=False, index=True)
    method = Column(String(20), default=ScrapingMethod.REQUESTS)
    status = Column(String(20), default=JobStatus.PENDING, index=True)
    
    # Job configuration
    selectors = Column(JSON, nullable=True)  # CSS/XPath selectors
    headers = Column(JSON, nullable=True)    # Custom headers
    cookies = Column(JSON, nullable=True)    # Custom cookies
    proxy = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timing and retries
    timeout = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    delay_between_requests = Column(Integer, default=1)
    
    # Results
    scraped_data_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Scheduling
    is_recurring = Column(Boolean, default=False)
    cron_expression = Column(String(100), nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scraped_data = relationship("ScrapedData", back_populates="job", cascade="all, delete-orphan")
    website_config_id = Column(Integer, ForeignKey("website_configs.id"), nullable=True)
    website_config = relationship("WebsiteConfig", back_populates="jobs")