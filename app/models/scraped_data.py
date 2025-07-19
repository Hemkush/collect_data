from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class ScrapedData(Base):
    __tablename__ = "scraped_data"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("scraping_jobs.id"), nullable=False, index=True)
    
    # Content data
    url = Column(String(2048), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    raw_html = Column(Text, nullable=True)
    
    # Structured data (JSON format)
    structured_data = Column(JSON, nullable=True)
    
    # Metadata
    content_type = Column(String(100), nullable=True)
    content_length = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    
    # Content analysis
    word_count = Column(Integer, nullable=True)
    image_count = Column(Integer, nullable=True)
    link_count = Column(Integer, nullable=True)
    
    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("ScrapingJob", back_populates="scraped_data")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_scraped_data_job_created', job_id, created_at),
        Index('idx_scraped_data_url_scraped', url, scraped_at),
    )