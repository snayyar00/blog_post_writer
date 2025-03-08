"""Scraper for competitor blog content and analysis."""
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field
from pathlib import Path
import json
import re

# Configure logging
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CompetitorBlog(BaseModel):
    """Model for competitor blog post."""
    url: HttpUrl
    title: str = Field(default="")
    content: str = Field(default="")
    headings: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    date_published: Optional[datetime] = None
    competitor: str = Field(default="")

class CompetitorBlogs(BaseModel):
    """Model for a list of competitor blog posts."""
    blogs: List[CompetitorBlog] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def model_dump(self) -> Dict[str, Any]:
        """Custom serialization for CompetitorBlogs."""
        return {
            'blogs': [blog.model_dump() for blog in self.blogs],
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_cache(cls, data: Dict[str, Any]) -> 'CompetitorBlogs':
        """Create CompetitorBlogs instance from cached data."""
        if not isinstance(data, dict):
            raise ValueError("Cache data must be a dictionary")
            
        return cls(
            blogs=[CompetitorBlog(**blog) for blog in data.get('blogs', [])],
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        )

def extract_keywords(text: str) -> List[str]:
    """Extract potential keywords from text using basic NLP."""
    # Remove special characters and convert to lowercase
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    
    # Filter common words and short words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [word for word in words if word not in stopwords and len(word) > 3]
    
    # Get frequency distribution
    freq_dist = {}
    for word in keywords:
        freq_dist[word] = freq_dist.get(word, 0) + 1
    
    # Return top keywords
    sorted_keywords = sorted(freq_dist.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_keywords[:10]]

async def fetch_blog_page(url: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Fetch blog page content."""
    try:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error fetching {url}: {response.status}")
                return None
            return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def parse_blog_page(html: str, url: str, competitor: str) -> Optional[CompetitorBlog]:
    """Parse blog page content."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else ""
        
        # Extract main content
        article = soup.find('article') or soup.find('main')
        if not article:
            return None
            
        # Extract headings
        headings = []
        for tag in ['h1', 'h2', 'h3']:
            headings.extend([h.get_text(strip=True) for h in article.find_all(tag)])
        
        # Extract content
        content = article.get_text(strip=True)
        
        # Extract keywords
        keywords = extract_keywords(content)
        
        # Try to find publication date
        date_elem = soup.find('time') or soup.find(class_=re.compile(r'date|time|publish', re.I))
        date_published = None
        if date_elem:
            date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
            try:
                date_published = datetime.fromisoformat(date_str)
            except:
                pass
        
        return CompetitorBlog(
            url=url,
            title=title,
            content=content,
            headings=headings,
            keywords=keywords,
            date_published=date_published,
            competitor=competitor
        )
    except Exception as e:
        logger.error(f"Error parsing {url}: {e}")
        return None

def get_cache_file_path(cache_dir: Path = Path("context/competitors")) -> Path:
    """Get the path to the cache file, ensuring directory exists."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "competitor_blogs.json"

def is_cache_valid(cache_file: Path, max_age_seconds: int = 86400) -> bool:
    """Check if cache file exists and is not too old."""
    if not cache_file.exists():
        return False
        
    try:
        with cache_file.open('r') as f:
            data = json.load(f)
            blogs = CompetitorBlogs.from_cache(data)
            age = datetime.now() - blogs.last_updated
            return age.total_seconds() < max_age_seconds
    except Exception:
        return False

async def scrape_competitor_blogs(
    competitor_urls: Dict[str, str],
    cache_dir: Path = Path("context/competitors")
) -> CompetitorBlogs:
    """Scrape blogs from competitor websites."""
    cache_file = get_cache_file_path(cache_dir)
    
    # Try loading from cache first
    if cache_file.exists():
        try:
            with cache_file.open('r') as f:
                data = json.load(f)
                blogs = CompetitorBlogs.from_cache(data)
                
                # Return cache if less than 24 hours old
                age = datetime.now() - blogs.last_updated
                if age.total_seconds() < 86400:  # 24 hours
                    return blogs
        except Exception as e:
            print(f"Error loading competitor cache: {e}")
            # Continue with fresh scrape
    
    # Scrape fresh content
    blogs = []
    async with aiohttp.ClientSession() as session:
        for competitor, url in competitor_urls.items():
            html = await fetch_blog_page(url, session)
            if html:
                blog = await parse_blog_page(html, url, competitor)
                if blog:
                    blogs.append(blog)
    
    # Create and cache results
    results = CompetitorBlogs(blogs=blogs)
    try:
        with cache_file.open('w') as f:
            json.dump(results.model_dump(), f, default=str)
    except Exception as e:
        logger.error(f"Error saving competitor cache: {e}")
    
    return results

def get_competitor_urls(business_type: str) -> Dict[str, str]:
    """Get relevant competitor URLs based on business type."""
    url_mapping = {
        'E-commerce': {
            'shopify': 'https://www.shopify.com/blog',
            'bigcommerce': 'https://www.bigcommerce.com/blog',
            'woocommerce': 'https://woocommerce.com/blog'
        },
        'SaaS': {
            'hubspot': 'https://blog.hubspot.com',
            'salesforce': 'https://www.salesforce.com/blog',
            'zendesk': 'https://www.zendesk.com/blog'
        },
        'Service Business': {
            'freshworks': 'https://www.freshworks.com/blog',
            'intercom': 'https://www.intercom.com/blog',
            'drift': 'https://www.drift.com/blog'
        },
        'Content Creator': {
            'buffer': 'https://buffer.com/resources',
            'mailchimp': 'https://mailchimp.com/resources/blog',
            'semrush': 'https://www.semrush.com/blog'
        }
    }
    
    return url_mapping.get(business_type, url_mapping['SaaS'])

async def analyze_competitors(business_type: str) -> Optional[Dict[str, Any]]:
    """Analyze competitor blogs with progress tracking."""
    try:
        # Get competitor URLs based on business type
        competitor_urls = get_competitor_urls(business_type)
        
        # Scrape and analyze blogs
        blogs = await scrape_competitor_blogs(competitor_urls)
        if not blogs or not blogs.blogs:
            return None
            
        # Analyze structure and patterns
        return analyze_competitor_structure(blogs)
            
    except Exception as e:
        logger.error(f"Error analyzing competitors: {e}")
        return None

def analyze_competitor_structure(blogs: CompetitorBlogs) -> Dict[str, Any]:
    """Analyze common patterns in competitor blog structure."""
    if not blogs or not blogs.blogs:
        return {
            'common_headings': [],
            'popular_keywords': [],
            'heading_patterns': [],
            'content_types': [],
            'avg_word_count': 0
        }
        
    analysis = {
        'common_headings': get_common_headings(blogs),
        'popular_keywords': get_popular_keywords(blogs),
        'heading_patterns': get_heading_patterns(blogs),
        'content_types': analyze_content_types(blogs),
        'avg_word_count': calculate_avg_word_count(blogs)
    }
    
    return analysis

def get_common_headings(blogs: CompetitorBlogs) -> List[str]:
    """Extract common headings from competitor blogs."""
    heading_freq = {}
    for blog in blogs.blogs:
        for heading in blog.headings:
            heading_lower = heading.lower()
            heading_freq[heading_lower] = heading_freq.get(heading_lower, 0) + 1
    
    return [h for h, _ in sorted(heading_freq.items(), key=lambda x: x[1], reverse=True)[:5]]

def get_popular_keywords(blogs: CompetitorBlogs) -> List[str]:
    """Extract popular keywords from competitor blogs."""
    keyword_freq = {}
    for blog in blogs.blogs:
        for keyword in blog.keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
    
    return [k for k, _ in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]]

def get_heading_patterns(blogs: CompetitorBlogs) -> List[str]:
    """Analyze common heading patterns."""
    patterns = []
    for blog in blogs.blogs:
        if len(blog.headings) >= 2:
            pattern = [h.split()[0].lower() for h in blog.headings[:2]]
            patterns.append(' '.join(pattern))
    
    pattern_freq = {}
    for pattern in patterns:
        pattern_freq[pattern] = pattern_freq.get(pattern, 0) + 1
    
    return [p for p, _ in sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)[:3]]

def analyze_content_types(blogs: CompetitorBlogs) -> List[str]:
    """Analyze content types based on headings and keywords."""
    content_markers = {
        'how-to': r'how to|guide|tutorial|steps',
        'listicle': r'\d+ ways|top \d+|best \d+',
        'case-study': r'case study|success story|example',
        'industry-news': r'news|announcement|update|release',
        'thought-leadership': r'future|trends|insights|perspective'
    }
    
    content_types = set()
    for blog in blogs.blogs:
        content = f"{blog.title.lower()} {' '.join(blog.headings).lower()}"
        for ctype, pattern in content_markers.items():
            if re.search(pattern, content):
                content_types.add(ctype)
    
    return list(content_types)

def calculate_avg_word_count(blogs: CompetitorBlogs) -> int:
    """Calculate average word count of competitor blogs."""
    if not blogs.blogs:
        return 0
        
    total_words = sum(len(blog.content.split()) for blog in blogs.blogs)
    return round(total_words / len(blogs.blogs))
    
    # Collect all headings and keywords
    all_headings = []
    all_keywords = []
    for blog in blogs.blogs:
        all_headings.extend(blog.headings)
        all_keywords.extend(blog.keywords)
    
    # Find common headings
    heading_freq = {}
    for heading in all_headings:
        heading_lower = heading.lower()
        heading_freq[heading_lower] = heading_freq.get(heading_lower, 0) + 1
    
    # Get most common headings
    sorted_headings = sorted(heading_freq.items(), key=lambda x: x[1], reverse=True)
    analysis['common_headings'] = [h for h, _ in sorted_headings[:5]]
    
    # Find popular keywords
    keyword_freq = {}
    for keyword in all_keywords:
        keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
    
    # Get most popular keywords
    sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
    analysis['popular_keywords'] = [k for k, _ in sorted_keywords[:10]]
    
    # Analyze heading patterns
    heading_patterns = []
    for blog in blogs.blogs:
        if len(blog.headings) >= 2:
            pattern = [h.split()[0].lower() for h in blog.headings[:2]]
            heading_patterns.append(' '.join(pattern))
    
    # Get common patterns
    pattern_freq = {}
    for pattern in heading_patterns:
        pattern_freq[pattern] = pattern_freq.get(pattern, 0) + 1
    
    sorted_patterns = sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)
    analysis['heading_patterns'] = [p for p, _ in sorted_patterns[:3]]
    
    return analysis
