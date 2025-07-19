import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.async_api import async_playwright
import time
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
from fake_useragent import UserAgent
import re

from app.core.config import settings
from app.core.exceptions import WebsiteNotAccessibleException, ParsingException
from app.schemas.scraped_data import ContentAnalysis

logger = logging.getLogger(__name__)

class ScrapingEngine:
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
    
    async def scrape(self, url: str, method: str = "requests", **kwargs) -> Dict[str, Any]:
        """Main scraping method that delegates to specific scrapers"""
        try:
            if method == "requests":
                return await self._scrape_with_requests(url, **kwargs)
            elif method == "selenium":
                return await self._scrape_with_selenium(url, **kwargs)
            elif method == "playwright":
                return await self._scrape_with_playwright(url, **kwargs)
            else:
                raise ValueError(f"Unsupported scraping method: {method}")
        except Exception as e:
            logger.error(f"Scraping failed for {url} with method {method}: {str(e)}")
            raise WebsiteNotAccessibleException(f"Failed to scrape {url}: {str(e)}")
    
    async def _scrape_with_requests(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using requests and BeautifulSoup"""
        headers = kwargs.get('headers', {})
        cookies = kwargs.get('cookies', {})
        timeout = kwargs.get('timeout', settings.DEFAULT_REQUEST_TIMEOUT)
        proxy = kwargs.get('proxy')
        user_agent = kwargs.get('user_agent', self.ua.random)
        
        # Set default headers
        if 'User-Agent' not in headers:
            headers['User-Agent'] = user_agent
        
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url, headers=headers, cookies=cookies, proxy=proxy) as response:
                    content = await response.text()
                    
                    result = {
                        'url': url,
                        'status_code': response.status,
                        'content_type': response.headers.get('Content-Type', ''),
                        'content_length': len(content),
                        'raw_html': content,
                        'response_headers': dict(response.headers)
                    }
                    
                    # Parse content with BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    result.update(self._extract_content(soup, url, kwargs.get('selectors', {})))
                    
                    return result
                    
        except asyncio.TimeoutError:
            raise WebsiteNotAccessibleException(f"Request timeout for {url}")
        except Exception as e:
            raise WebsiteNotAccessibleException(f"Request failed for {url}: {str(e)}")
    
    async def _scrape_with_selenium(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using Selenium WebDriver"""
        timeout = kwargs.get('timeout', settings.DEFAULT_REQUEST_TIMEOUT)
        wait_for_element = kwargs.get('wait_for_element')
        headers = kwargs.get('headers', {})
        user_agent = kwargs.get('user_agent', self.ua.random)
        
        options = ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={user_agent}')
        
        # Add custom headers (limited support in Selenium)
        for key, value in headers.items():
            if key.lower() in ['accept-language', 'accept-encoding']:
                options.add_argument(f'--lang={value}' if key.lower() == 'accept-language' else f'--accept-encoding={value}')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(timeout)
            
            # Navigate to URL
            driver.get(url)
            
            # Wait for specific element if specified
            if wait_for_element:
                wait = WebDriverWait(driver, timeout)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element)))
            
            # Get page source
            content = driver.page_source
            
            result = {
                'url': url,
                'status_code': 200,  # Selenium doesn't provide HTTP status
                'content_type': 'text/html',
                'content_length': len(content),
                'raw_html': content,
                'response_headers': {}
            }
            
            # Parse content with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            result.update(self._extract_content(soup, url, kwargs.get('selectors', {})))
            
            return result
            
        except Exception as e:
            raise WebsiteNotAccessibleException(f"Selenium scraping failed for {url}: {str(e)}")
        finally:
            if driver:
                driver.quit()
    
    async def _scrape_with_playwright(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using Playwright"""
        timeout = kwargs.get('timeout', settings.DEFAULT_REQUEST_TIMEOUT) * 1000  # Playwright uses milliseconds
        wait_for_element = kwargs.get('wait_for_element')
        headers = kwargs.get('headers', {})
        user_agent = kwargs.get('user_agent', self.ua.random)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.HEADLESS_BROWSER)
            context = await browser.new_context(
                user_agent=user_agent,
                extra_http_headers=headers
            )
            
            try:
                page = await context.new_page()
                
                # Navigate to URL
                response = await page.goto(url, timeout=timeout)
                
                # Wait for specific element if specified
                if wait_for_element:
                    await page.wait_for_selector(wait_for_element, timeout=timeout)
                
                # Get page content
                content = await page.content()
                
                result = {
                    'url': url,
                    'status_code': response.status if response else 200,
                    'content_type': 'text/html',
                    'content_length': len(content),
                    'raw_html': content,
                    'response_headers': response.headers if response else {}
                }
                
                # Parse content with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                result.update(self._extract_content(soup, url, kwargs.get('selectors', {})))
                
                return result
                
            except Exception as e:
                raise WebsiteNotAccessibleException(f"Playwright scraping failed for {url}: {str(e)}")
            finally:
                await browser.close()
    
    def _extract_content(self, soup: BeautifulSoup, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract content from BeautifulSoup object using selectors"""
        try:
            result = {}
            
            # Extract title
            title_tag = soup.find('title')
            result['title'] = title_tag.get_text().strip() if title_tag else None
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc.get('content', '').strip() if meta_desc else None
            
            # Extract main content
            content_selectors = [
                'article', 'main', '.content', '#content', 
                '.post-content', '.entry-content', '.article-content'
            ]
            
            main_content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = element.get_text(strip=True)
                    break
            
            if not main_content:
                # Fallback to body content
                body = soup.find('body')
                if body:
                    # Remove script and style elements
                    for script in body(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                    main_content = body.get_text(strip=True)
            
            result['content'] = main_content
            
            # Extract structured data based on custom selectors
            structured_data = {}
            for key, selector in selectors.items():
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        structured_data[key] = elements[0].get_text(strip=True)
                    else:
                        structured_data[key] = [el.get_text(strip=True) for el in elements]
            
            result['structured_data'] = structured_data if structured_data else None
            
            # Content analysis
            word_count = len(main_content.split()) if main_content else 0
            images = soup.find_all('img')
            links = soup.find_all('a', href=True)
            
            # Extract image URLs
            image_urls = []
            for img in images[:10]:  # Limit to first 10 images
                src = img.get('src')
                if src:
                    image_urls.append(urljoin(url, src))
            
            # Extract link URLs
            link_urls = []
            for link in links[:20]:  # Limit to first 20 links
                href = link.get('href')
                if href and not href.startswith('#'):
                    link_urls.append(urljoin(url, href))
            
            # Extract meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            keywords = []
            if meta_keywords:
                keywords = [kw.strip() for kw in meta_keywords.get('content', '').split(',')]
            
            result.update({
                'word_count': word_count,
                'image_count': len(images),
                'link_count': len(links),
                'extracted_images': image_urls,
                'extracted_links': link_urls,
                'meta_description': meta_description,
                'meta_keywords': keywords
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Content extraction failed: {str(e)}")
            raise ParsingException(f"Failed to extract content: {str(e)}")
    
    def analyze_content(self, html: str, url: str) -> ContentAnalysis:
        """Analyze content and return structured analysis"""
        soup = BeautifulSoup(html, 'html.parser')
        content_data = self._extract_content(soup, url, {})
        
        return ContentAnalysis(
            url=url,
            title=content_data.get('title'),
            word_count=content_data.get('word_count', 0),
            image_count=content_data.get('image_count', 0),
            link_count=content_data.get('link_count', 0),
            main_content_length=len(content_data.get('content', '')),
            extracted_links=content_data.get('extracted_links', []),
            extracted_images=content_data.get('extracted_images', []),
            meta_description=content_data.get('meta_description'),
            meta_keywords=content_data.get('meta_keywords', [])
        )