"""
Initialize blog context from sitemap entries.
"""
import asyncio
from pathlib import Path
from src.utils.initialize_blog_context import initialize_blog_context, BlogPostList

async def read_sitemap_file(sitemap_path: Path) -> Optional[str]:
    """Read sitemap entries from file with error handling."""
    try:
        if not sitemap_path.exists():
            print(f"Error: Sitemap file not found at {sitemap_path}")
            return None
            
        with open(sitemap_path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading sitemap file: {e}")
        return None

async def initialize_blogs(sitemap_text: str) -> Optional[BlogPostList]:
    """Initialize blogs from sitemap text with error handling."""
    try:
        return await initialize_blog_context(sitemap_text)
    except Exception as e:
        print(f"Error initializing blog context: {e}")
        return None

async def main():
    """Initialize blog context from sitemap entries."""
    sitemap_path = Path("context/sitemap_entries.xml")
    
    # Read sitemap entries
    sitemap_text = await read_sitemap_file(sitemap_path)
    if not sitemap_text:
        return
    
    print("Initializing blog context...")
    blogs = await initialize_blogs(sitemap_text)
    
    if blogs:
        print(f"Successfully initialized {len(blogs.posts)} blog posts!")
        print("\nExample blog titles:")
        for blog in blogs.posts[:3]:
            print(f"- {blog.title}")
    else:
        print("Failed to initialize blog context.")

if __name__ == "__main__":
    asyncio.run(main())
