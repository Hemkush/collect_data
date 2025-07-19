from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models.scraping_job import ScrapingJob, JobStatus
from app.models.scraped_data import ScrapedData
from app.models.website_config import WebsiteConfig
from app.schemas.scraping_job import ScrapingJobCreate, ScrapingJobUpdate, ScrapingJobResponse
from app.services.scraping_engine import ScrapingEngine
from app.core.exceptions import ScrapingException

logger = logging.getLogger(__name__)

class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraping_engine = ScrapingEngine()
    
    async def create_job(self, job_data: ScrapingJobCreate) -> ScrapingJob:
        """Create a new scraping job"""
        try:
            # Get website config if specified
            website_config = None
            if job_data.website_config_id:
                result = await self.db.execute(
                    select(WebsiteConfig).where(WebsiteConfig.id == job_data.website_config_id)
                )
                website_config = result.scalar_one_or_none()
                if not website_config:
                    raise ValueError(f"Website config with ID {job_data.website_config_id} not found")
            
            # Create job with data from schema
            job = ScrapingJob(
                url=str(job_data.url),
                method=job_data.method.value,
                selectors=job_data.selectors,
                headers=job_data.headers,
                cookies=job_data.cookies,
                proxy=job_data.proxy,
                user_agent=job_data.user_agent,
                timeout=job_data.timeout,
                max_retries=job_data.max_retries,
                delay_between_requests=job_data.delay_between_requests,
                is_recurring=job_data.is_recurring,
                cron_expression=job_data.cron_expression,
                website_config_id=job_data.website_config_id
            )
            
            # Apply website config defaults if available
            if website_config:
                if not job.headers and website_config.default_headers:
                    job.headers = website_config.default_headers
                if not job.selectors and website_config.default_selectors:
                    job.selectors = website_config.default_selectors
                if not job.cookies and website_config.default_cookies:
                    job.cookies = website_config.default_cookies
                if not job.user_agent and website_config.custom_user_agents:
                    job.user_agent = website_config.custom_user_agents[0]
                
                # Override method if website requires specific method
                if website_config.requires_js and job.method == "requests":
                    job.method = website_config.default_method
            
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)
            
            logger.info(f"Created scraping job {job.id} for URL: {job.url}")
            return job
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create job: {str(e)}")
            raise ScrapingException(f"Failed to create job: {str(e)}")
    
    async def get_job(self, job_id: int) -> Optional[ScrapingJob]:
        """Get a specific job by ID"""
        result = await self.db.execute(
            select(ScrapingJob)
            .options(selectinload(ScrapingJob.scraped_data))
            .where(ScrapingJob.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_jobs(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[str] = None,
        method: Optional[str] = None
    ) -> tuple[List[ScrapingJob], int]:
        """Get jobs with pagination and filters"""
        query = select(ScrapingJob)
        count_query = select(func.count(ScrapingJob.id))
        
        # Apply filters
        filters = []
        if status:
            filters.append(ScrapingJob.status == status)
        if method:
            filters.append(ScrapingJob.method == method)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get jobs with pagination
        query = query.order_by(desc(ScrapingJob.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        return jobs, total
    
    async def update_job(self, job_id: int, job_update: ScrapingJobUpdate) -> Optional[ScrapingJob]:
        """Update a job"""
        try:
            # Get the job
            job = await self.get_job(job_id)
            if not job:
                return None
            
            # Update fields
            update_data = job_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(job, field, value)
            
            job.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(job)
            
            return job
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update job {job_id}: {str(e)}")
            raise ScrapingException(f"Failed to update job: {str(e)}")
    
    async def delete_job(self, job_id: int) -> bool:
        """Delete a job and its associated data"""
        try:
            job = await self.get_job(job_id)
            if not job:
                return False
            
            # Delete associated scraped data (cascade should handle this)
            await self.db.delete(job)
            await self.db.commit()
            
            logger.info(f"Deleted job {job_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete job {job_id}: {str(e)}")
            raise ScrapingException(f"Failed to delete job: {str(e)}")
    
    async def execute_job(self, job_id: int) -> ScrapingJob:
        """Execute a scraping job"""
        try:
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            if job.status != JobStatus.PENDING:
                raise ValueError(f"Job {job_id} is not in pending status")
            
            # Update job status to running
            await self.update_job(job_id, ScrapingJobUpdate(status=JobStatus.RUNNING))
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            try:
                # Execute scraping
                scrape_kwargs = {
                    'headers': job.headers or {},
                    'cookies': job.cookies or {},
                    'timeout': job.timeout,
                    'proxy': job.proxy,
                    'user_agent': job.user_agent,
                    'selectors': job.selectors or {}
                }
                
                # Add website config specific settings
                if job.website_config:
                    config = job.website_config
                    if config.wait_for_element:
                        scrape_kwargs['wait_for_element'] = config.wait_for_element
                
                scraped_result = await self.scraping_engine.scrape(
                    job.url, 
                    job.method, 
                    **scrape_kwargs
                )
                
                # Save scraped data
                scraped_data = ScrapedData(
                    job_id=job.id,
                    url=scraped_result['url'],
                    title=scraped_result.get('title'),
                    content=scraped_result.get('content'),
                    raw_html=scraped_result.get('raw_html'),
                    structured_data=scraped_result.get('structured_data'),
                    content_type=scraped_result.get('content_type'),
                    content_length=scraped_result.get('content_length'),
                    status_code=scraped_result.get('status_code'),
                    response_headers=scraped_result.get('response_headers'),
                    word_count=scraped_result.get('word_count'),
                    image_count=scraped_result.get('image_count'),
                    link_count=scraped_result.get('link_count')
                )
                
                self.db.add(scraped_data)
                
                # Update job status to completed
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.scraped_data_count = 1
                job.error_message = None
                
                # Update website config success
                if job.website_config:
                    job.website_config.last_successful_scrape = datetime.utcnow()
                    job.website_config.failure_count = 0
                
                await self.db.commit()
                logger.info(f"Successfully executed job {job_id}")
                
            except Exception as scrape_error:
                # Update job status to failed
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_message = str(scrape_error)
                job.retry_count += 1
                
                # Update website config failure
                if job.website_config:
                    job.website_config.failure_count += 1
                
                await self.db.commit()
                logger.error(f"Job {job_id} failed: {str(scrape_error)}")
                raise ScrapingException(f"Job execution failed: {str(scrape_error)}")
            
            return job
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to execute job {job_id}: {str(e)}")
            raise ScrapingException(f"Failed to execute job: {str(e)}")
    
    async def get_pending_jobs(self) -> List[ScrapingJob]:
        """Get all pending jobs"""
        result = await self.db.execute(
            select(ScrapingJob)
            .where(ScrapingJob.status == JobStatus.PENDING)
            .order_by(ScrapingJob.created_at)
        )
        return result.scalars().all()
    
    async def get_failed_jobs_for_retry(self) -> List[ScrapingJob]:
        """Get failed jobs that can be retried"""
        result = await self.db.execute(
            select(ScrapingJob)
            .where(
                and_(
                    ScrapingJob.status == JobStatus.FAILED,
                    ScrapingJob.retry_count < ScrapingJob.max_retries
                )
            )
            .order_by(ScrapingJob.updated_at)
        )
        return result.scalars().all()
    
    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get job statistics"""
        # Get status counts
        status_result = await self.db.execute(
            select(ScrapingJob.status, func.count(ScrapingJob.id))
            .group_by(ScrapingJob.status)
        )
        status_counts = dict(status_result.all())
        
        # Get method counts
        method_result = await self.db.execute(
            select(ScrapingJob.method, func.count(ScrapingJob.id))
            .group_by(ScrapingJob.method)
        )
        method_counts = dict(method_result.all())
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_result = await self.db.execute(
            select(func.count(ScrapingJob.id))
            .where(ScrapingJob.created_at >= yesterday)
        )
        recent_jobs = recent_result.scalar()
        
        # Get total scraped data count
        total_data_result = await self.db.execute(
            select(func.count(ScrapedData.id))
        )
        total_scraped_items = total_data_result.scalar()
        
        return {
            'total_jobs': sum(status_counts.values()),
            'status_counts': status_counts,
            'method_counts': method_counts,
            'recent_jobs_24h': recent_jobs,
            'total_scraped_items': total_scraped_items
        }