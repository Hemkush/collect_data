from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import List, Optional
import math

from app.core.database import get_db
from app.models.scraped_data import ScrapedData
from app.models.scraping_job import ScrapingJob
from app.schemas.scraped_data import (
    ScrapedDataResponse, 
    ScrapedDataList, 
    ScrapedDataSummary,
    ContentAnalysis
)
from app.services.scraping_engine import ScrapingEngine

router = APIRouter()

@router.get("/", response_model=ScrapedDataList)
async def get_scraped_data(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    url_contains: Optional[str] = Query(None, description="Filter URLs containing this text"),
    db: AsyncSession = Depends(get_db)
):
    """Get scraped data with pagination and filters"""
    query = select(ScrapedData)
    count_query = select(func.count(ScrapedData.id))
    
    # Apply filters
    filters = []
    if job_id:
        filters.append(ScrapedData.job_id == job_id)
    if url_contains:
        filters.append(ScrapedData.url.contains(url_contains))
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get data with pagination
    skip = (page - 1) * size
    query = query.order_by(desc(ScrapedData.scraped_at)).offset(skip).limit(size)
    result = await db.execute(query)
    data = result.scalars().all()
    
    return ScrapedDataList(
        data=[ScrapedDataResponse.from_orm(item) for item in data],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0
    )

@router.get("/{data_id}", response_model=ScrapedDataResponse)
async def get_scraped_data_item(data_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific scraped data item by ID"""
    result = await db.execute(
        select(ScrapedData).where(ScrapedData.id == data_id)
    )
    data = result.scalar_one_or_none()
    
    if not data:
        raise HTTPException(status_code=404, detail="Scraped data not found")
    
    return ScrapedDataResponse.from_orm(data)

@router.get("/job/{job_id}/summary", response_model=ScrapedDataSummary)
async def get_job_data_summary(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get summary statistics for scraped data of a specific job"""
    # Check if job exists
    job_result = await db.execute(
        select(ScrapingJob).where(ScrapingJob.id == job_id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get summary statistics
    stats_result = await db.execute(
        select(
            func.count(ScrapedData.id).label('total_items'),
            func.avg(ScrapedData.content_length).label('avg_content_length'),
            func.sum(ScrapedData.word_count).label('total_words'),
            func.count(func.distinct(ScrapedData.url)).label('unique_urls'),
            func.min(ScrapedData.scraped_at).label('first_scraped'),
            func.max(ScrapedData.scraped_at).label('last_scraped')
        ).where(ScrapedData.job_id == job_id)
    )
    stats = stats_result.first()
    
    # Count unique domains
    domain_result = await db.execute(
        select(func.count(func.distinct(func.regexp_replace(
            ScrapedData.url, 
            r'^https?://([^/]+).*', 
            r'\1'
        )))).where(ScrapedData.job_id == job_id)
    )
    unique_domains = domain_result.scalar() or 0
    
    return ScrapedDataSummary(
        job_id=job_id,
        total_items=stats.total_items or 0,
        avg_content_length=float(stats.avg_content_length) if stats.avg_content_length else None,
        total_words=stats.total_words or 0,
        unique_domains=unique_domains,
        scraped_at_range={
            "first": stats.first_scraped,
            "last": stats.last_scraped
        } if stats.first_scraped else {}
    )

@router.get("/{data_id}/content")
async def get_raw_content(data_id: int, db: AsyncSession = Depends(get_db)):
    """Get raw HTML content of a scraped data item"""
    result = await db.execute(
        select(ScrapedData.raw_html, ScrapedData.url)
        .where(ScrapedData.id == data_id)
    )
    data = result.first()
    
    if not data:
        raise HTTPException(status_code=404, detail="Scraped data not found")
    
    return {
        "url": data.url,
        "raw_html": data.raw_html
    }

@router.get("/{data_id}/analyze", response_model=ContentAnalysis)
async def analyze_content(data_id: int, db: AsyncSession = Depends(get_db)):
    """Analyze content of a scraped data item"""
    result = await db.execute(
        select(ScrapedData.raw_html, ScrapedData.url)
        .where(ScrapedData.id == data_id)
    )
    data = result.first()
    
    if not data:
        raise HTTPException(status_code=404, detail="Scraped data not found")
    
    if not data.raw_html:
        raise HTTPException(status_code=400, detail="No HTML content available for analysis")
    
    # Analyze content using scraping engine
    scraping_engine = ScrapingEngine()
    analysis = scraping_engine.analyze_content(data.raw_html, data.url)
    
    return analysis

@router.delete("/{data_id}")
async def delete_scraped_data(data_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a scraped data item"""
    result = await db.execute(
        select(ScrapedData).where(ScrapedData.id == data_id)
    )
    data = result.scalar_one_or_none()
    
    if not data:
        raise HTTPException(status_code=404, detail="Scraped data not found")
    
    await db.delete(data)
    await db.commit()
    
    return {"message": "Scraped data deleted successfully"}

@router.get("/export/job/{job_id}")
async def export_job_data(
    job_id: int, 
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    db: AsyncSession = Depends(get_db)
):
    """Export scraped data for a specific job"""
    # Check if job exists
    job_result = await db.execute(
        select(ScrapingJob).where(ScrapingJob.id == job_id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get all scraped data for the job
    result = await db.execute(
        select(ScrapedData).where(ScrapedData.job_id == job_id)
        .order_by(ScrapedData.scraped_at)
    )
    data = result.scalars().all()
    
    if format == "json":
        return {
            "job_id": job_id,
            "job_url": job.url,
            "total_items": len(data),
            "data": [ScrapedDataResponse.from_orm(item).dict() for item in data]
        }
    elif format == "csv":
        # For CSV, we'll return a simplified structure
        # In a real application, you'd want to use a proper CSV library
        csv_data = []
        for item in data:
            csv_data.append({
                "id": item.id,
                "url": item.url,
                "title": item.title,
                "content_length": item.content_length,
                "word_count": item.word_count,
                "scraped_at": item.scraped_at.isoformat() if item.scraped_at else None
            })
        return {"format": "csv", "data": csv_data}