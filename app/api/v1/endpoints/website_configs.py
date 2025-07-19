from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import List, Optional
import math

from app.core.database import get_db
from app.models.website_config import WebsiteConfig
from app.schemas.website_config import (
    WebsiteConfigCreate,
    WebsiteConfigUpdate, 
    WebsiteConfigResponse,
    WebsiteConfigList
)

router = APIRouter()

@router.post("/", response_model=WebsiteConfigResponse)
async def create_website_config(
    config_data: WebsiteConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new website configuration"""
    try:
        # Check if config with same name or domain already exists
        existing_result = await db.execute(
            select(WebsiteConfig).where(
                (WebsiteConfig.name == config_data.name) |
                (WebsiteConfig.domain == config_data.domain)
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            if existing.name == config_data.name:
                raise HTTPException(status_code=400, detail="Website config with this name already exists")
            if existing.domain == config_data.domain:
                raise HTTPException(status_code=400, detail="Website config with this domain already exists")
        
        # Create new config
        config = WebsiteConfig(
            name=config_data.name,
            domain=config_data.domain,
            base_url=str(config_data.base_url),
            default_method=config_data.default_method,
            default_selectors=config_data.default_selectors,
            default_headers=config_data.default_headers,
            default_cookies=config_data.default_cookies,
            rate_limit_delay=config_data.rate_limit_delay,
            max_concurrent_requests=config_data.max_concurrent_requests,
            respect_robots_txt=config_data.respect_robots_txt,
            requires_js=config_data.requires_js,
            wait_for_element=config_data.wait_for_element,
            page_load_timeout=config_data.page_load_timeout,
            needs_proxy=config_data.needs_proxy,
            rotate_user_agents=config_data.rotate_user_agents,
            custom_user_agents=config_data.custom_user_agents,
            pagination_selector=config_data.pagination_selector,
            max_pages=config_data.max_pages,
            content_filters=config_data.content_filters,
            required_elements=config_data.required_elements,
            blocked_keywords=config_data.blocked_keywords,
            description=config_data.description,
            notes=config_data.notes
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        return WebsiteConfigResponse.from_orm(config)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create website config: {str(e)}")

@router.get("/", response_model=WebsiteConfigList)
async def get_website_configs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    active_only: bool = Query(False, description="Show only active configurations"),
    db: AsyncSession = Depends(get_db)
):
    """Get website configurations with pagination and filters"""
    query = select(WebsiteConfig)
    count_query = select(func.count(WebsiteConfig.id))
    
    # Apply filters
    filters = []
    if domain:
        filters.append(WebsiteConfig.domain.contains(domain))
    if active_only:
        filters.append(WebsiteConfig.is_active == True)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get configs with pagination
    skip = (page - 1) * size
    query = query.order_by(desc(WebsiteConfig.created_at)).offset(skip).limit(size)
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return WebsiteConfigList(
        configs=[WebsiteConfigResponse.from_orm(config) for config in configs],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0
    )

@router.get("/{config_id}", response_model=WebsiteConfigResponse)
async def get_website_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific website configuration by ID"""
    result = await db.execute(
        select(WebsiteConfig).where(WebsiteConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Website configuration not found")
    
    return WebsiteConfigResponse.from_orm(config)

@router.get("/domain/{domain}", response_model=WebsiteConfigResponse)
async def get_config_by_domain(domain: str, db: AsyncSession = Depends(get_db)):
    """Get website configuration by domain"""
    result = await db.execute(
        select(WebsiteConfig).where(WebsiteConfig.domain == domain)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Website configuration not found for this domain")
    
    return WebsiteConfigResponse.from_orm(config)

@router.put("/{config_id}", response_model=WebsiteConfigResponse)
async def update_website_config(
    config_id: int,
    config_update: WebsiteConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a website configuration"""
    try:
        # Get existing config
        result = await db.execute(
            select(WebsiteConfig).where(WebsiteConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="Website configuration not found")
        
        # Check for name/domain conflicts if being updated
        update_data = config_update.dict(exclude_unset=True)
        
        if 'name' in update_data and update_data['name'] != config.name:
            existing_name_result = await db.execute(
                select(WebsiteConfig).where(WebsiteConfig.name == update_data['name'])
            )
            existing_name = existing_name_result.scalar_one_or_none()
            if existing_name:
                raise HTTPException(status_code=400, detail="Website config with this name already exists")
        
        if 'domain' in update_data and update_data['domain'] != config.domain:
            existing_domain_result = await db.execute(
                select(WebsiteConfig).where(WebsiteConfig.domain == update_data['domain'])
            )
            existing_domain = existing_domain_result.scalar_one_or_none()
            if existing_domain:
                raise HTTPException(status_code=400, detail="Website config with this domain already exists")
        
        # Update fields
        for field, value in update_data.items():
            if field == 'base_url' and value:
                setattr(config, field, str(value))
            else:
                setattr(config, field, value)
        
        await db.commit()
        await db.refresh(config)
        
        return WebsiteConfigResponse.from_orm(config)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update website config: {str(e)}")

@router.delete("/{config_id}")
async def delete_website_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a website configuration"""
    try:
        result = await db.execute(
            select(WebsiteConfig).where(WebsiteConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="Website configuration not found")
        
        await db.delete(config)
        await db.commit()
        
        return {"message": "Website configuration deleted successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete website config: {str(e)}")

@router.patch("/{config_id}/toggle-active")
async def toggle_config_active(config_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle the active status of a website configuration"""
    try:
        result = await db.execute(
            select(WebsiteConfig).where(WebsiteConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="Website configuration not found")
        
        config.is_active = not config.is_active
        await db.commit()
        await db.refresh(config)
        
        return {
            "message": f"Website configuration {'activated' if config.is_active else 'deactivated'}",
            "is_active": config.is_active
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to toggle config status: {str(e)}")

@router.get("/{config_id}/test")
async def test_website_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Test a website configuration by performing a sample scrape"""
    from app.services.scraping_engine import ScrapingEngine
    
    # Get config
    result = await db.execute(
        select(WebsiteConfig).where(WebsiteConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Website configuration not found")
    
    try:
        # Prepare scraping parameters
        scrape_kwargs = {
            'headers': config.default_headers or {},
            'cookies': config.default_cookies or {},
            'timeout': config.page_load_timeout,
            'selectors': config.default_selectors or {}
        }
        
        if config.wait_for_element:
            scrape_kwargs['wait_for_element'] = config.wait_for_element
        
        if config.custom_user_agents:
            scrape_kwargs['user_agent'] = config.custom_user_agents[0]
        
        # Perform test scrape
        engine = ScrapingEngine()
        result = await engine.scrape(
            config.base_url,
            config.default_method,
            **scrape_kwargs
        )
        
        # Return test results (limited data for safety)
        return {
            "status": "success",
            "url": result['url'],
            "status_code": result.get('status_code'),
            "content_type": result.get('content_type'),
            "content_length": result.get('content_length'),
            "title": result.get('title'),
            "word_count": result.get('word_count'),
            "structured_data_keys": list(result.get('structured_data', {}).keys()) if result.get('structured_data') else []
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }