from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import math

from app.core.database import get_db
from app.services.job_service import JobService
from app.schemas.scraping_job import (
    ScrapingJobCreate, 
    ScrapingJobUpdate, 
    ScrapingJobResponse, 
    ScrapingJobList
)

router = APIRouter()

@router.post("/", response_model=ScrapingJobResponse)
async def create_job(
    job_data: ScrapingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scraping job"""
    job_service = JobService(db)
    job = await job_service.create_job(job_data)
    
    # Optionally start job immediately in background
    # background_tasks.add_task(job_service.execute_job, job.id)
    
    return ScrapingJobResponse.from_orm(job)

@router.get("/", response_model=ScrapingJobList)
async def get_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    method: Optional[str] = Query(None, description="Filter by scraping method"),
    db: AsyncSession = Depends(get_db)
):
    """Get jobs with pagination and filters"""
    job_service = JobService(db)
    skip = (page - 1) * size
    
    jobs, total = await job_service.get_jobs(
        skip=skip, 
        limit=size, 
        status=status, 
        method=method
    )
    
    return ScrapingJobList(
        jobs=[ScrapingJobResponse.from_orm(job) for job in jobs],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0
    )

@router.get("/{job_id}", response_model=ScrapingJobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific job by ID"""
    job_service = JobService(db)
    job = await job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return ScrapingJobResponse.from_orm(job)

@router.put("/{job_id}", response_model=ScrapingJobResponse)
async def update_job(
    job_id: int, 
    job_update: ScrapingJobUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Update a job"""
    job_service = JobService(db)
    job = await job_service.update_job(job_id, job_update)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return ScrapingJobResponse.from_orm(job)

@router.delete("/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a job"""
    job_service = JobService(db)
    success = await job_service.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job deleted successfully"}

@router.post("/{job_id}/execute", response_model=ScrapingJobResponse)
async def execute_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Execute a job immediately"""
    job_service = JobService(db)
    try:
        job = await job_service.execute_job(job_id)
        return ScrapingJobResponse.from_orm(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{job_id}/execute-async")
async def execute_job_async(
    job_id: int, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Execute a job in background"""
    job_service = JobService(db)
    
    # Check if job exists
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Add to background tasks
    background_tasks.add_task(job_service.execute_job, job_id)
    
    return {"message": "Job execution started in background", "job_id": job_id}

@router.get("/statistics/overview")
async def get_job_statistics(db: AsyncSession = Depends(get_db)):
    """Get job statistics overview"""
    job_service = JobService(db)
    stats = await job_service.get_job_statistics()
    return stats

@router.get("/pending/list", response_model=List[ScrapingJobResponse])
async def get_pending_jobs(db: AsyncSession = Depends(get_db)):
    """Get all pending jobs"""
    job_service = JobService(db)
    jobs = await job_service.get_pending_jobs()
    return [ScrapingJobResponse.from_orm(job) for job in jobs]

@router.get("/failed/retry", response_model=List[ScrapingJobResponse])
async def get_failed_jobs_for_retry(db: AsyncSession = Depends(get_db)):
    """Get failed jobs that can be retried"""
    job_service = JobService(db)
    jobs = await job_service.get_failed_jobs_for_retry()
    return [ScrapingJobResponse.from_orm(job) for job in jobs]