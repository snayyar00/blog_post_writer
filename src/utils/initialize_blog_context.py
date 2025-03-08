"""
Initialize blog context from sitemap entries.
"""
import asyncio
from typing import List, Dict
from pathlib import Path
import json
from .blog_context_manager import BlogPostList, fetch_blogs_from_sitemap, get_relevant_context

def extract_xml_tag_content(line: str, tag: str) -> Optional[str]:
    """Extract content from XML tag."""
    start_tag = f"<{tag}>"
    end_tag = f"</{tag}>"
    if line.startswith(start_tag) and line.endswith(end_tag):
        return line[len(start_tag):-len(end_tag)]
    return None

def parse_sitemap_entries(sitemap_text: str) -> List[Dict[str, str]]:
    """Parse sitemap entries from text."""
    entries = []
    current_entry: Dict[str, str] = {}
    
    for line in sitemap_text.strip().split('\n'):
        line = line.strip()
        
        # Start new entry
        if line == '<url>':
            current_entry = {}
            continue
            
        # End current entry
        if line == '</url>' and current_entry:
            entries.append(current_entry)
            continue
        
        # Extract tag content
        for tag in ['loc', 'lastmod', 'priority']:
            content = extract_xml_tag_content(line, tag)
            if content:
                current_entry[tag] = content
                break
    
    return entries

async def initialize_blog_context(sitemap_text: str, cache_dir: str = "context/blogs") -> BlogPostList:
    """Initialize blog context from sitemap entries."""
    # Parse sitemap entries
    entries = parse_sitemap_entries(sitemap_text)
    
    # Fetch and cache blogs
    return await fetch_blogs_from_sitemap(
        sitemap_entries=entries,
        cache_dir=Path(cache_dir)
    )

def get_cached_blog_context(query: str, blogs: BlogPostList, max_blogs: int = 3) -> str:
    """Get blog context for a query from cached blogs."""
    return get_relevant_context(blogs, query, max_blogs)

# Global blog context cache
_cached_blogs: Optional[BlogPostList] = None

def get_blog_context(query: str, cache_dir: str = "context/blogs", max_blogs: int = 3) -> str:
    """Get blog context for a query using global cache."""
    global _cached_blogs
    
    if not _cached_blogs:
        # Load cached blogs
        cache_path = Path(cache_dir)
        if not cache_path.exists():
            return ""
            
        blog_files = list(cache_path.glob("*.json"))
        blogs = []
        
        for file in blog_files:
            try:
                with file.open('r') as f:
                    data = json.load(f)
                    blogs.append(data)
            except Exception as e:
                print(f"Error loading blog cache {file}: {e}")
        
        _cached_blogs = BlogPostList(root=blogs)
    
    return get_cached_blog_context(query, _cached_blogs, max_blogs)

if __name__ == "__main__":
    # Example usage
    sitemap_text = '''
    <url>
    <loc>https://www.webability.io/blog/cognitive-accessibility-best-practices</loc>
    <lastmod>2025-02-21T01:30:46+00:00</lastmod>
    <priority>0.64</priority>
    </url>
    '''
    
    asyncio.run(initialize_blog_context(sitemap_text))
