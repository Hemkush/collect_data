from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any
import validators

from app.core.database import get_db
from app.services.scraping_engine import ScrapingEngine
from app.schemas.scraped_data import ContentAnalysis

router = APIRouter()

class QuickScrapeRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL to scrape")
    method: str = Field(default="requests", description="Scraping method")
    selectors: Optional[Dict[str, str]] = Field(None, description="CSS selectors for data extraction")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout")
    user_agent: Optional[str] = Field(None, description="Custom user agent")

class QuickScrapeResponse(BaseModel):
    url: str
    status_code: Optional[int]
    title: Optional[str]
    content: Optional[str]
    structured_data: Optional[Dict[str, Any]]
    content_length: Optional[int]
    word_count: Optional[int]
    image_count: Optional[int]
    link_count: Optional[int]
    meta_description: Optional[str]

class UrlValidationResponse(BaseModel):
    url: str
    is_valid: bool
    is_reachable: bool
    status_code: Optional[int]
    content_type: Optional[str]
    response_time_ms: Optional[float]
    error: Optional[str]

@router.post("/quick-scrape", response_model=QuickScrapeResponse)
async def quick_scrape(request: QuickScrapeRequest):
    """Perform a quick scrape without creating a job"""
    try:
        engine = ScrapingEngine()
        
        # Prepare scraping parameters
        scrape_kwargs = {
            'headers': request.headers or {},
            'timeout': request.timeout,
            'selectors': request.selectors or {}
        }
        
        if request.user_agent:
            scrape_kwargs['user_agent'] = request.user_agent
        
        # Perform scraping
        result = await engine.scrape(str(request.url), request.method, **scrape_kwargs)
        
        return QuickScrapeResponse(
            url=result['url'],
            status_code=result.get('status_code'),
            title=result.get('title'),
            content=result.get('content'),
            structured_data=result.get('structured_data'),
            content_length=result.get('content_length'),
            word_count=result.get('word_count'),
            image_count=result.get('image_count'),
            link_count=result.get('link_count'),
            meta_description=result.get('meta_description')
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scraping failed: {str(e)}")

@router.get("/validate-url", response_model=UrlValidationResponse)
async def validate_url(url: str = Query(..., description="URL to validate")):
    """Validate if a URL is accessible for scraping"""
    import aiohttp
    import time
    
    # Basic URL validation
    if not validators.url(url):
        return UrlValidationResponse(
            url=url,
            is_valid=False,
            is_reachable=False,
            error="Invalid URL format"
        )
    
    # Check if URL is reachable
    try:
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.head(url) as response:
                response_time = (time.time() - start_time) * 1000
                
                return UrlValidationResponse(
                    url=url,
                    is_valid=True,
                    is_reachable=response.status < 400,
                    status_code=response.status,
                    content_type=response.headers.get('Content-Type'),
                    response_time_ms=round(response_time, 2)
                )
                
    except Exception as e:
        return UrlValidationResponse(
            url=url,
            is_valid=True,
            is_reachable=False,
            error=str(e)
        )

@router.post("/analyze-content", response_model=ContentAnalysis)
async def analyze_html_content(
    html: str = Field(..., description="HTML content to analyze"),
    url: str = Field(..., description="URL of the content")
):
    """Analyze HTML content and extract structured information"""
    try:
        engine = ScrapingEngine()
        analysis = engine.analyze_content(html, url)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")

@router.get("/extract-links")
async def extract_links(
    url: str = Query(..., description="URL to extract links from"),
    method: str = Query("requests", description="Scraping method"),
    internal_only: bool = Query(False, description="Only return internal links")
):
    """Extract all links from a webpage"""
    try:
        from urllib.parse import urlparse, urljoin
        
        engine = ScrapingEngine()
        result = await engine.scrape(url, method)
        
        links = result.get('extracted_links', [])
        
        if internal_only:
            base_domain = urlparse(url).netloc
            links = [link for link in links if urlparse(link).netloc == base_domain]
        
        return {
            "url": url,
            "total_links": len(links),
            "links": links[:100]  # Limit to first 100 links
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Link extraction failed: {str(e)}")

@router.get("/extract-images")
async def extract_images(
    url: str = Query(..., description="URL to extract images from"),
    method: str = Query("requests", description="Scraping method")
):
    """Extract all images from a webpage"""
    try:
        engine = ScrapingEngine()
        result = await engine.scrape(url, method)
        
        images = result.get('extracted_images', [])
        
        return {
            "url": url,
            "total_images": len(images),
            "images": images[:50]  # Limit to first 50 images
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image extraction failed: {str(e)}")

@router.get("/supported-methods")
async def get_supported_methods():
    """Get list of supported scraping methods"""
    return {
        "methods": [
            {
                "name": "requests",
                "description": "Fast HTTP requests with BeautifulSoup parsing",
                "pros": ["Fast", "Low resource usage", "Good for static content"],
                "cons": ["Cannot handle JavaScript", "Limited interaction capability"]
            },
            {
                "name": "selenium",
                "description": "Browser automation with Selenium WebDriver",
                "pros": ["Full JavaScript support", "Real browser rendering", "Can interact with elements"],
                "cons": ["Slower", "Higher resource usage", "Requires browser installation"]
            },
            {
                "name": "playwright",
                "description": "Modern browser automation with Playwright",
                "pros": ["Fast browser automation", "Better reliability", "Modern web standards"],
                "cons": ["Higher resource usage", "Requires browser installation"]
            }
        ]
    }

@router.get("/robots-txt")
async def check_robots_txt(
    url: str = Query(..., description="Website URL to check robots.txt")
):
    """Check robots.txt for a website"""
    try:
        from urllib.parse import urljoin, urlparse
        import aiohttp
        
        # Construct robots.txt URL
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    return {
                        "url": robots_url,
                        "exists": True,
                        "status_code": response.status,
                        "content": content[:2000]  # Limit content length
                    }
                else:
                    return {
                        "url": robots_url,
                        "exists": False,
                        "status_code": response.status,
                        "content": None
                    }
                    
    except Exception as e:
        return {
            "url": robots_url if 'robots_url' in locals() else url,
            "exists": False,
            "error": str(e)
        }