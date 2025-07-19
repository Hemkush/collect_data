from fastapi import APIRouter

from app.api.v1.endpoints import jobs, scraped_data, website_configs, scraping

api_router = APIRouter()

api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scraped_data.router, prefix="/scraped-data", tags=["scraped-data"])
api_router.include_router(website_configs.router, prefix="/website-configs", tags=["website-configs"])
api_router.include_router(scraping.router, prefix="/scraping", tags=["scraping"])