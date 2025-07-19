from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)

class ScrapingException(Exception):
    """Base exception for scraping operations"""
    pass

class WebsiteNotAccessibleException(ScrapingException):
    """Raised when website is not accessible"""
    pass

class ParsingException(ScrapingException):
    """Raised when content parsing fails"""
    pass

class RateLimitExceededException(ScrapingException):
    """Raised when rate limit is exceeded"""
    pass

def setup_exception_handlers(app: FastAPI):
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Exception",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": "Invalid request data",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(ScrapingException)
    async def scraping_exception_handler(request: Request, exc: ScrapingException):
        logger.error(f"Scraping error: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Scraping Error",
                "message": str(exc)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )