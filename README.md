# Web Scraping API

A scalable backend system for web scraping built with FastAPI. This system provides a REST API for creating, managing, and executing web scraping jobs with support for multiple scraping methods and persistent data storage.

## 🚀 Features

- **Multiple Scraping Methods**: Support for requests, Selenium, and Playwright
- **Async Support**: Built with FastAPI and async/await for high performance
- **Database Storage**: PostgreSQL with SQLAlchemy for persistent data storage
- **Background Tasks**: Celery integration for async job processing
- **Website Configurations**: Reusable configurations for different websites
- **Rate Limiting**: Built-in rate limiting and anti-bot measures
- **Content Analysis**: Automatic content extraction and analysis
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Docker Support**: Ready-to-use Docker containers

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Chrome/Chromium (for Selenium/Playwright)

## 🛠️ Installation

### Option 1: Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd web-scraping-api
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start with Docker Compose:
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

### Option 2: Manual Installation

1. Clone and navigate to the project:
```bash
git clone <repository-url>
cd web-scraping-api
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up database:
```bash
# Create PostgreSQL database
createdb webscraperdb

# Run the application (tables will be created automatically)
uvicorn app.main:app --reload
```

6. Start Celery worker (optional, for background tasks):
```bash
celery -A app.celery_app worker --loglevel=info
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔧 Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/webscraperdb

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=["*"]

# Scraping
DEFAULT_REQUEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10
RATE_LIMIT_PER_MINUTE=60
```

## 🎯 Quick Start

### 1. Create a Simple Scraping Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "method": "requests"
     }'
```

### 2. Execute the Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/1/execute"
```

### 3. Get Scraped Data

```bash
curl "http://localhost:8000/api/v1/scraped-data/?job_id=1"
```

### 4. Quick Scrape (No Job Creation)

```bash
curl -X POST "http://localhost:8000/api/v1/scraping/quick-scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "method": "requests",
       "selectors": {
         "title": "h1",
         "description": "meta[name=description]"
       }
     }'
```

## 🏗️ API Endpoints

### Jobs Management
- `POST /api/v1/jobs/` - Create a new scraping job
- `GET /api/v1/jobs/` - List jobs with pagination and filters
- `GET /api/v1/jobs/{job_id}` - Get specific job details
- `PUT /api/v1/jobs/{job_id}` - Update job
- `DELETE /api/v1/jobs/{job_id}` - Delete job
- `POST /api/v1/jobs/{job_id}/execute` - Execute job synchronously
- `POST /api/v1/jobs/{job_id}/execute-async` - Execute job in background

### Scraped Data
- `GET /api/v1/scraped-data/` - List scraped data with filters
- `GET /api/v1/scraped-data/{data_id}` - Get specific scraped item
- `GET /api/v1/scraped-data/job/{job_id}/summary` - Get job data summary
- `GET /api/v1/scraped-data/export/job/{job_id}` - Export job data

### Website Configurations
- `POST /api/v1/website-configs/` - Create website configuration
- `GET /api/v1/website-configs/` - List configurations
- `GET /api/v1/website-configs/{config_id}` - Get configuration
- `PUT /api/v1/website-configs/{config_id}` - Update configuration
- `GET /api/v1/website-configs/{config_id}/test` - Test configuration

### Scraping Utilities
- `POST /api/v1/scraping/quick-scrape` - Quick scrape without job creation
- `GET /api/v1/scraping/validate-url` - Validate URL accessibility
- `GET /api/v1/scraping/extract-links` - Extract links from URL
- `GET /api/v1/scraping/supported-methods` - Get supported scraping methods

## 🎨 Frontend Integration

### Example: React Integration

```javascript
// Create a scraping job
const createJob = async (url, method = 'requests') => {
  const response = await fetch('/api/v1/jobs/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url: url,
      method: method,
      selectors: {
        title: 'h1',
        content: 'article, .content'
      }
    })
  });
  return response.json();
};

// Execute job and get results
const executeJob = async (jobId) => {
  const response = await fetch(`/api/v1/jobs/${jobId}/execute`, {
    method: 'POST'
  });
  return response.json();
};

// Get scraped data
const getScrapedData = async (jobId) => {
  const response = await fetch(`/api/v1/scraped-data/?job_id=${jobId}`);
  return response.json();
};
```

### Example: JavaScript Fetch

```javascript
// Quick scrape example
const quickScrape = async (url) => {
  try {
    const response = await fetch('/api/v1/scraping/quick-scrape', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: url,
        method: 'requests',
        selectors: {
          title: 'h1',
          description: 'meta[name="description"]',
          links: 'a'
        }
      })
    });
    
    const data = await response.json();
    console.log('Scraped data:', data);
    return data;
  } catch (error) {
    console.error('Scraping failed:', error);
  }
};
```

## 🔍 Advanced Usage

### Website Configuration

Create reusable configurations for specific websites:

```json
{
  "name": "example-site",
  "domain": "example.com",
  "base_url": "https://example.com",
  "default_method": "requests",
  "default_selectors": {
    "title": "h1.title",
    "content": ".article-content",
    "author": ".author-name"
  },
  "default_headers": {
    "User-Agent": "Custom Bot 1.0"
  },
  "rate_limit_delay": 2,
  "requires_js": false
}
```

### Custom Selectors

Use CSS selectors to extract specific data:

```json
{
  "url": "https://example.com/article",
  "method": "requests",
  "selectors": {
    "title": "h1",
    "author": ".author",
    "publish_date": "time[datetime]",
    "paragraphs": "p",
    "images": "img[src]"
  }
}
```

### Browser-based Scraping

For JavaScript-heavy sites:

```json
{
  "url": "https://spa-example.com",
  "method": "playwright",
  "timeout": 60,
  "selectors": {
    "dynamic_content": ".loaded-content"
  }
}
```

## 🔒 Security Considerations

- Always validate URLs before scraping
- Respect robots.txt files
- Implement rate limiting
- Use proxies when necessary
- Be mindful of website terms of service
- Consider using the `respect_robots_txt` option in website configurations

## 🚀 Deployment

### Production Deployment

1. Use environment-specific settings
2. Set up proper database connections
3. Configure Redis for production
4. Use reverse proxy (nginx)
5. Set up monitoring and logging
6. Configure SSL/HTTPS

### Example nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🛠️ Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black app/

# Check types
mypy app/

# Lint
flake8 app/
```

## 📈 Monitoring

The API provides several monitoring endpoints:

- `GET /health` - Health check
- `GET /api/v1/jobs/statistics/overview` - Job statistics
- Application logs for debugging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Check database connectivity
4. Verify environment configuration

## 🔮 Roadmap

- [ ] Authentication and authorization
- [ ] Rate limiting per API key
- [ ] Webhook notifications
- [ ] Data export in multiple formats
- [ ] Real-time scraping status updates via WebSockets
- [ ] Machine learning-based content extraction
- [ ] Distributed scraping across multiple workers
