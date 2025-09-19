from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Naukri Job Scraper API",
    description="API for scraping job listings from Naukri.com",
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
        
        # Naukri search URLs to try
        naukri_urls = [
            f"https://www.naukri.com/{keyword.replace(' ', '-').lower()}-jobs?k={search_keyword}",
            f"https://www.naukri.com/jobs-by-{keyword.replace(' ', '-').lower()}?k={search_keyword}",
            f"https://www.naukri.com/{keyword.replace(' ', '-').lower()}-jobs-in-india?k={search_keyword}"
        ]
        
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
        
        for naukri_url in naukri_urls:
            try:
                logger.info(f"Trying Naukri URL: {naukri_url}")
                response = requests.get(naukri_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Multiple selectors for job cards
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
                    
                    for selector in job_selectors:
                        job_cards = soup.select(selector)
                        if job_cards:
                            logger.info(f"Found {len(job_cards)} jobs with selector: {selector}")
                            
                            for card in job_cards[:max_jobs]:
                                try:
                                    # Title selectors
                                    title = None
                                    title_selectors = [
                                        'a.title',
                                        'a.title.fw500.ellipsis',
                                        '.job-title',
                                        '.title',
                                        'h2 a',
                                        '[class*="title"] a'
                                    ]
                                    for title_selector in title_selectors:
                                        title_elem = card.select_one(title_selector)
                                        if title_elem and title_elem.get_text(strip=True):
                                            title = title_elem.get_text(strip=True)
                                            break
                                    
                                    # Company selectors
                                    company = None
                                    company_selectors = [
                                        'a.comp-name',
                                        'a.compName',
                                        '.company-name',
                                        '.comp-name',
                                        '[class*="company"]',
                                        '[class*="comp"]'
                                    ]
                                    for company_selector in company_selectors:
                                        company_elem = card.select_one(company_selector)
                                        if company_elem and company_elem.get_text(strip=True):
                                            company = company_elem.get_text(strip=True)
                                            break
                                    
                                    # Location selectors
                                    location = None
                                    location_selectors = [
                                        'span.locWdth',
                                        'span.fleft.grey-text.br2.placeHolderLi.location',
                                        '.location',
                                        '.loc',
                                        '[class*="location"]',
                                        '[class*="loc"]'
                                    ]
                                    for location_selector in location_selectors:
                                        location_elem = card.select_one(location_selector)
                                        if location_elem and location_elem.get_text(strip=True):
                                            location = location_elem.get_text(strip=True)
                                            break
                                    
                                    # Experience selectors
                                    experience = None
                                    exp_selectors = [
                                        'span.expwdth',
                                        'li.experience',
                                        '.exp',
                                        '.experience',
                                        '[class*="exp"]',
                                        '[class*="experience"]'
                                    ]
                                    for exp_selector in exp_selectors:
                                        exp_elem = card.select_one(exp_selector)
                                        if exp_elem and exp_elem.get_text(strip=True):
                                            experience = exp_elem.get_text(strip=True)
                                            break
                                    
                                    # Apply link
                                    apply_link = None
                                    for title_selector in title_selectors:
                                        link_elem = card.select_one(title_selector)
                                        if link_elem and link_elem.get('href'):
                                            apply_link = link_elem.get('href')
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
                            
                            if naukri_jobs:
                                return naukri_jobs[:max_jobs]
                    
            except Exception as e:
                logger.warning(f"Naukri URL {naukri_url} failed: {e}")
                continue
        
        return []
        
    except Exception as e:
        logger.error(f"Naukri scraping failed: {e}")
        return []

def scrape_indeed_jobs(keyword: str, max_jobs: int = 10) -> List[Dict[str, Any]]:
    """Fallback to Indeed scraping"""
    try:
        jobs = []
        search_query = keyword.replace(' ', '+')
        url = f"https://in.indeed.com/jobs?q={search_query}&l=India"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.select('.job_seen_beacon, .cardOutline, .jobsearch-SerpJobCard')
            
            for card in job_cards[:max_jobs]:
                try:
                    title_elem = card.select_one('h2.jobTitle, a.jobTitle, h2.title')
                    company_elem = card.select_one('span.companyName, .companyName')
                    location_elem = card.select_one('.companyLocation, .location')
                    link_elem = card.select_one('a[href*="/viewjob"]')
                    
                    title = title_elem.get_text(strip=True) if title_elem else None
                    company = company_elem.get_text(strip=True) if company_elem else None
                    location = location_elem.get_text(strip=True) if location_elem else None
                    link = link_elem.get('href') if link_elem else None
                    
                    if link and not link.startswith('http'):
                        link = f"https://in.indeed.com{link}"
                    
                    if title and link:
                        jobs.append({
                            'jobTitle': title,
                            'company': company or 'Not specified',
                            'location': location or 'Not specified',
                            'experience': 'Not specified',
                            'applyLink': link,
                            'platform': 'Indeed'
                        })
                        
                except Exception as e:
                    logger.warning(f"Error parsing Indeed job card: {e}")
                    continue
        
        return jobs
        
    except Exception as e:
        logger.error(f"Indeed scraping failed: {e}")
        return []

def scrape_monster_jobs(keyword: str, max_jobs: int = 10) -> List[Dict[str, Any]]:
    """Fallback to Monster scraping"""
    try:
        jobs = []
        search_query = keyword.replace(' ', '-')
        url = f"https://www.monsterindia.com/srp/results?query={search_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.select('.card-apply-content, .job-tile, .srp-jobtuple-wrapper')
            
            for card in job_cards[:max_jobs]:
                try:
                    title_elem = card.select_one('h3.medium, a.job-title, h3.title')
                    company_elem = card.select_one('.company-name, .company')
                    location_elem = card.select_one('.loc, .location')
                    link_elem = card.select_one('a[href*="/job/"]')
                    
                    title = title_elem.get_text(strip=True) if title_elem else None
                    company = company_elem.get_text(strip=True) if company_elem else None
                    location = location_elem.get_text(strip=True) if location_elem else None
                    link = link_elem.get('href') if link_elem else None
                    
                    if link and not link.startswith('http'):
                        link = f"https://www.monsterindia.com{link}"
                    
                    if title and link:
                        jobs.append({
                            'jobTitle': title,
                            'company': company or 'Not specified',
                            'location': location or 'Not specified',
                            'experience': 'Not specified',
                            'applyLink': link,
                            'platform': 'Monster'
                        })
                        
                except Exception as e:
                    logger.warning(f"Error parsing Monster job card: {e}")
                    continue
        
        return jobs
        
    except Exception as e:
        logger.error(f"Monster scraping failed: {e}")
        return []

@app.get("/scrape/", response_model=List[Dict[str, Any]])
async def scrape_data(keyword: str, max_jobs: int = 10):
    """
    Scrape jobs using multiple HTTP-based methods
    Returns empty array if all methods fail
    """
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")
    
    logger.info(f"Scraping jobs for: {keyword}")
    
    # Try Naukri scraping first
    jobs = scrape_naukri_jobs(keyword, max_jobs)
    
    # If Naukri fails, try Indeed
    if not jobs:
        jobs = scrape_indeed_jobs(keyword, max_jobs)
    
    # If Indeed fails, try Monster
    if not jobs:
        jobs = scrape_monster_jobs(keyword, max_jobs)
    
    logger.info(f"Found {len(jobs)} jobs for '{keyword}'")
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