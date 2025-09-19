from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Naukri Job Scraper API",
    description="API for scraping job listings exclusively from Naukri.com",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Naukri Job Scraper API",
        "endpoints": {
            "scrape_jobs": "/scrape/?keyword=python",
            "health_check": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

def scrape_naukri_jobs(keyword: str, max_jobs: int = 10) -> List[Dict[str, Any]]:
    """Scrape Naukri jobs using HTTP requests only"""
    try:
        naukri_jobs = []
        search_keyword = keyword.replace(' ', '%20')
        
        # Naukri search URL
        naukri_url = f"https://www.naukri.com/{keyword.replace(' ', '-').lower()}-jobs?k={search_keyword}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        logger.info(f"Scraping Naukri for keyword: {keyword}")
        logger.info(f"URL: {naukri_url}")
        
        try:
            response = requests.get(naukri_url, headers=headers, timeout=15)
            logger.info(f"Naukri response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"Naukri returned status code: {response.status_code}")
                return []

            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for job cards (Naukri frequently changes their CSS)
            job_selectors = [
                '.srp-jobtuple-wrapper',
                '.jobTuple.bgWhite.br4.mb-8',
                '.jobTuple',
                '.list',
                '.row',
                '.job-tuple',
                '[data-job-id]',
                '.cust-job-tuple',
                '.srp-jobtuple'
            ]
            
            job_cards = []
            for selector in job_selectors:
                found_cards = soup.select(selector)
                if found_cards:
                    job_cards.extend(found_cards)
                    logger.info(f"Found {len(found_cards)} jobs using selector: {selector}")
                    break
            
            if not job_cards:
                logger.warning("No job cards found with any selector")
                # Try alternative approach - look for common patterns
                job_cards = soup.find_all('div', class_=lambda x: x and ('job' in x.lower() or 'tuple' in x.lower()))
                logger.info(f"Found {len(job_cards)} jobs using alternative approach")
            
            for job in job_cards[:max_jobs]:
                try:
                    # Try multiple selectors for each field (Naukri changes these frequently)
                    title_selectors = [
                        'a.title',
                        'a.title.fw500.ellipsis',
                        '.job-title',
                        '.title',
                        'h2 a',
                        '[class*="title"] a'
                    ]
                    
                    company_selectors = [
                        'a.comp-name',
                        'a.compName',
                        '.company-name',
                        '.comp-name',
                        '[class*="company"]',
                        '[class*="comp"]'
                    ]
                    
                    location_selectors = [
                        'span.locWdth',
                        'span.fleft.grey-text.br2.placeHolderLi.location',
                        '.location',
                        '.loc',
                        '[class*="location"]',
                        '[class*="loc"]'
                    ]
                    
                    exp_selectors = [
                        'span.expwdth',
                        'li.experience',
                        '.exp',
                        '.experience',
                        '[class*="exp"]',
                        '[class*="experience"]'
                    ]
                    
                    # Extract title
                    title = None
                    for selector in title_selectors:
                        title_elem = job.select_one(selector)
                        if title_elem and title_elem.get_text(strip=True):
                            title = title_elem.get_text(strip=True)
                            break
                    
                    # Extract company
                    company = None
                    for selector in company_selectors:
                        company_elem = job.select_one(selector)
                        if company_elem and company_elem.get_text(strip=True):
                            company = company_elem.get_text(strip=True)
                            break
                    
                    # Extract location
                    location = None
                    for selector in location_selectors:
                        location_elem = job.select_one(selector)
                        if location_elem and location_elem.get_text(strip=True):
                            location = location_elem.get_text(strip=True)
                            break
                    
                    # Extract experience
                    experience = None
                    for selector in exp_selectors:
                        exp_elem = job.select_one(selector)
                        if exp_elem and exp_elem.get_text(strip=True):
                            experience = exp_elem.get_text(strip=True)
                            break
                    
                    # Extract apply link
                    apply_link = None
                    for selector in title_selectors:
                        link_elem = job.select_one(selector)
                        if link_elem and link_elem.get('href'):
                            apply_link = link_elem.get('href')
                            # Ensure full URL
                            if apply_link and not apply_link.startswith('http'):
                                apply_link = f"https://www.naukri.com{apply_link}"
                            break
                    
                    if title and apply_link:
                        naukri_jobs.append({
                            'jobTitle': title,
                            'company': company or 'Not specified',
                            'location': location or 'Not specified',
                            'experience': experience or 'Not specified',
                            'applyLink': apply_link,
                            'platform': 'Naukri'
                        })
                        
                except Exception as e:
                    logger.warning(f"Error parsing job card: {e}")
                    continue

            logger.info(f"Naukri jobs found: {len(naukri_jobs)}")
            return naukri_jobs[:max_jobs]
            
        except Exception as e:
            logger.error(f"Error scraping Naukri: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

@app.get("/scrape/", response_model=List[Dict[str, Any]])
async def scrape_data(keyword: str, max_jobs: int = 10):
    """
    Scrape jobs from Naukri.com only
    Returns empty array if scraping fails
    """
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")
    
    logger.info(f"Scraping Naukri jobs for: {keyword}")
    
    # Scrape only from Naukri
    jobs = scrape_naukri_jobs(keyword, max_jobs)
    
    logger.info(f"Found {len(jobs)} Naukri jobs for '{keyword}'")
    return jobs

@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)