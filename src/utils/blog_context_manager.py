"""
Blog context manager to fetch and store content from previous blogs.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field

class BlogPost(BaseModel):
    """Model for blog post metadata and content."""
    url: HttpUrl
    title: str = Field(default="", description="Blog post title")
    content: str = Field(default="", description="Blog post content")
    last_modified: datetime = Field(default_factory=datetime.now)
    priority: float = Field(default=0.5, ge=0, le=1)
    categories: List[str] = Field(default_factory=list)

class BlogPostList(BaseModel):
    """Model for a list of blog posts."""
    posts: List[BlogPost] = Field(default_factory=list)
    
    def model_dump(self) -> List[Dict]:
        return [post.model_dump() for post in self.posts]

def format_blog_context(post: BlogPost) -> str:
    """Format blog post as context string."""
    return f"""Title: {post.title}
URL: {post.url}
Last Modified: {post.last_modified.isoformat()}
Categories: {', '.join(post.categories)}

{post.content}
"""

async def fetch_blog_content(url: str) -> Optional[tuple[str, str]]:
    """Fetch blog content from URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract main content - adjust selectors based on site structure
                title = soup.title.string if soup.title else ""
                article = soup.find('article') or soup.find('main')
                content = article.get_text(strip=True) if article else ""
                
                return title, content
    except Exception as e:
        print(f"Error fetching blog content from {url}: {e}")
        return None

async def load_cached_blog(cache_file: Path) -> Optional[BlogPost]:
    """Load blog post from cache file."""
    if not cache_file.exists():
        return None
        
    try:
        with cache_file.open('r') as f:
            data = json.load(f)
            return BlogPost(**data)
    except Exception as e:
        print(f"Error loading cached blog {cache_file}: {e}")
        return None

async def save_blog_to_cache(blog: BlogPost, cache_file: Path) -> bool:
    """Save blog post to cache file."""
    try:
        with cache_file.open('w') as f:
            json.dump(blog.model_dump(), f, default=str)
        return True
    except Exception as e:
        print(f"Error saving blog {blog.url} to cache: {e}")
        return False

async def fetch_or_load_blog(url: str, last_modified: str, priority: float = 0.5, cache_dir: Path = Path("context/blogs")) -> Optional[BlogPost]:
    """Fetch blog from URL or load from cache."""
    # Handle invalid inputs early
    if not url or not last_modified:
        return None
    
    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{hash(url)}.json"
    
    # Try loading from cache first
    cached_blog = await load_cached_blog(cache_file)
    if cached_blog:
        return cached_blog
    
    # Fetch new content if needed
    content = await fetch_blog_content(url)
    if not content:
        return None
    
    title, content = content
    blog = BlogPost(
        url=url,
        title=title,
        content=content,
        last_modified=datetime.fromisoformat(last_modified),
        priority=priority
    )
    
    # Cache the blog
    if await save_blog_to_cache(blog, cache_file):
        return blog
    
    # Return blog even if caching failed
    return blog

async def fetch_blogs_from_sitemap(sitemap_entries: List[Dict[str, str]], cache_dir: Path = Path("context/blogs")) -> BlogPostList:
    """Fetch multiple blogs from sitemap entries."""
    tasks = [
        fetch_or_load_blog(
            url=entry['loc'],
            last_modified=entry['lastmod'],
            priority=float(entry.get('priority', 0.5)),
            cache_dir=cache_dir
        )
        for entry in sitemap_entries
    ]
    
    results = await asyncio.gather(*tasks)
    return BlogPostList(posts=[r for r in results if r is not None])

def get_relevant_context(blogs: BlogPostList, query: str, max_blogs: int = 3) -> str:
    """Get relevant blog context based on query."""
    # Filter blogs by keyword matching
    relevant_blogs = [
        blog for blog in blogs.posts
        if any(kw.lower() in blog.content.lower() for kw in query.split())
    ]
    
    # Sort by priority and recency
    relevant_blogs.sort(
        key=lambda x: (x.priority, x.last_modified),
        reverse=True
    )
    
    # Format context from top blogs
    blog_contexts = [
        format_blog_context(blog)
        for blog in relevant_blogs[:max_blogs]
    ]
    
    return "\n---\n".join(blog_contexts) if blog_contexts else ""
