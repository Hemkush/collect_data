from celery import current_task
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import logging

from app.celery_app import celery_app
from app.core.config import settings
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

# Create async engine for tasks
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@celery_app.task(bind=True)
def execute_scraping_job(self, job_id: int):
    """Execute a scraping job in background"""
    try:
        # Update task state
        self.update_state(state='PROGRESS', meta={'job_id': job_id, 'status': 'starting'})
        
        async def _execute():
            async with AsyncSessionLocal() as db:
                job_service = JobService(db)
                job = await job_service.execute_job(job_id)
                return job.id
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_execute())
        loop.close()
        
        return {'job_id': result, 'status': 'completed'}
        
    except Exception as e:
        logger.error(f"Task failed for job {job_id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'job_id': job_id, 'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def process_bulk_urls(self, urls: list, config: dict):
    """Process multiple URLs in bulk"""
    try:
        results = []
        total_urls = len(urls)
        
        for i, url in enumerate(urls):
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': total_urls,
                    'status': f'Processing {url}'
                }
            )
            
            async def _process_url():
                async with AsyncSessionLocal() as db:
                    from app.schemas.scraping_job import ScrapingJobCreate
                    
                    job_service = JobService(db)
                    job_data = ScrapingJobCreate(
                        url=url,
                        method=config.get('method', 'requests'),
                        **config
                    )
                    job = await job_service.create_job(job_data)
                    executed_job = await job_service.execute_job(job.id)
                    return executed_job.id
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            job_id = loop.run_until_complete(_process_url())
            loop.close()
            
            results.append({'url': url, 'job_id': job_id})
        
        return {
            'total_processed': len(results),
            'results': results,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Bulk processing failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task
def cleanup_old_data():
    """Clean up old scraped data"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import delete
        from app.models.scraped_data import ScrapedData
        from app.models.scraping_job import ScrapingJob
        
        async def _cleanup():
            async with AsyncSessionLocal() as db:
                # Delete scraped data older than 30 days
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                # Delete old scraped data
                await db.execute(
                    delete(ScrapedData).where(ScrapedData.created_at < cutoff_date)
                )
                
                # Delete old completed jobs
                await db.execute(
                    delete(ScrapingJob).where(
                        ScrapingJob.completed_at < cutoff_date,
                        ScrapingJob.status == 'completed'
                    )
                )
                
                await db.commit()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_cleanup())
        loop.close()
        
        return {'status': 'completed', 'message': 'Old data cleaned up successfully'}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise

# Periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-data': {
        'task': 'app.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}
celery_app.conf.timezone = 'UTC'