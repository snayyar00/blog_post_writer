"""
Web scraper utility to extract content from websites for context.
"""

import os
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import time
from bs4 import BeautifulSoup
import hashlib
import json
import re
from collections import Counter
from urllib.parse import urljoin

def get_business_type_markers() -> Dict[str, List[str]]:
    """Get regex patterns for detecting business types.
    
    Returns:
        Dict mapping business types to lists of regex patterns
    """
    return {
        'E-commerce': [
            r'(?i)shop|store|cart|checkout|product|inventory|shipping|order',
            r'(?i)price|discount|sale|offer|deal|buy|purchase',
            r'(?i)marketplace|vendor|seller|retail|merchant'
        ],
        'SaaS': [
            r'(?i)software|platform|solution|service|cloud|api|integration',
            r'(?i)subscription|pricing|enterprise|scale|automation',
            r'(?i)dashboard|analytics|monitor|track|report'
        ],
        'Service Business': [
            r'(?i)service|consultation|appointment|booking|schedule',
            r'(?i)client|customer|project|team|expert|professional',
            r'(?i)solution|support|help|assistance|care'
        ],
        'Content Creator': [
            r'(?i)blog|article|content|post|story|guide|tutorial',
            r'(?i)creator|author|writer|editor|publisher',
            r'(?i)media|video|podcast|newsletter|audience'
        ],
        'Agency': [
            r'(?i)agency|marketing|advertising|branding|strategy',
            r'(?i)campaign|creative|design|development|seo',
            r'(?i)client|portfolio|case study|results|roi'
        ]
    }

def get_content_type_markers() -> Dict[str, List[str]]:
    """Get regex patterns for detecting content types.
    
    Returns:
        Dict mapping content types to lists of regex patterns
    """
    return {
        'Educational': [
            r'(?i)learn|guide|tutorial|how to|tips|best practices',
            r'(?i)understand|explain|example|lesson|course'
        ],
    'Product': [
        r'feature|benefit|solution|product|service',
        r'pricing|plan|package|subscription|trial'
    ],
    'Industry': [
        r'industry|market|trend|insight|analysis',
        r'report|study|research|survey|data'
    ],
    'Case Study': [
        r'case study|success story|testimonial|review',
        r'result|impact|achievement|improvement'
    ],
    'Thought Leadership': [
        r'vision|strategy|innovation|future|trend',
        r'expert|leader|perspective|opinion|insight'
    ]
}

async def scrape_blog_posts(blog_url: str, keyword: str, max_posts: int = 5) -> List[Dict[str, Any]]:
    """
    Scrape blog posts from a competitor's blog that are relevant to the given keyword.
    
    Args:
        blog_url: URL of the competitor's blog
        keyword: Keyword to filter relevant posts
        max_posts: Maximum number of posts to return
        
    Returns:
        List of dictionaries containing blog post information
    """
    try:
        # Fetch the blog page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(blog_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find blog post links
        blog_posts = []
        
        # Common selectors for blog posts
        article_selectors = [
            'article', '.post', '.blog-post', '.entry', 
            '.article', '.blog-entry', '.post-item', '.blog-item'
        ]
        
        # Try to find articles using common selectors
        articles = []
        for selector in article_selectors:
            found_articles = soup.select(selector)
            if found_articles:
                articles.extend(found_articles)
                break
        
        # If no articles found with selectors, look for generic links
        if not articles:
            # Find all links
            links = soup.find_all('a', href=True)
            
            # Filter links that might be blog posts
            blog_link_patterns = [
                r'/blog/', r'/article/', r'/post/', 
                r'\d{4}/\d{2}/', r'/news/'
            ]
            
            for link in links:
                href = link.get('href', '')
                
                # Check if href matches blog patterns
                if any(re.search(pattern, href) for pattern in blog_link_patterns):
                    # Ensure it's a full URL
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            base_url = '/'.join(blog_url.split('/')[:3])  # Get domain
                            href = f"{base_url}{href}"
                        else:
                            href = f"{blog_url.rstrip('/')}/{href}"
                    
                    # Get title from link text
                    title = link.get_text().strip()
                    if title and len(title) > 5:  # Ensure it's not just a short label
                        blog_posts.append({
                            'title': title,
                            'url': href,
                            'summary': '',
                            'date': ''
                        })
        
        # Process found articles
        for article in articles:
            # Extract title
            title_elem = article.find(['h1', 'h2', 'h3', 'h4', '.title', '.post-title'])
            title = title_elem.get_text().strip() if title_elem else ''
            
            # Extract link
            link_elem = article.find('a', href=True)
            href = link_elem.get('href', '') if link_elem else ''
            
            # Ensure it's a full URL
            if href and not href.startswith('http'):
                if href.startswith('/'):
                    base_url = '/'.join(blog_url.split('/')[:3])  # Get domain
                    href = f"{base_url}{href}"
                else:
                    href = f"{blog_url.rstrip('/')}/{href}"
            
            # Extract date
            date_elem = article.find(['time', '.date', '.post-date', '.published', '.meta-date'])
            date = date_elem.get_text().strip() if date_elem else ''
            
            # Extract summary
            summary_elem = article.find(['p', '.excerpt', '.summary', '.post-excerpt', '.entry-summary'])
            summary = summary_elem.get_text().strip() if summary_elem else ''
            
            if title and href:
                blog_posts.append({
                    'title': title,
                    'url': href,
                    'summary': summary,
                    'date': date
                })
        
        # Filter posts by keyword relevance
        keyword_lower = keyword.lower()
        relevant_posts = []
        
        for post in blog_posts:
            # Check if keyword is in title or summary
            if keyword_lower in post['title'].lower() or keyword_lower in post['summary'].lower():
                relevant_posts.append(post)
                continue
                
            # If we don't have enough posts yet, try to fetch the content
            if len(relevant_posts) < max_posts and post['url']:
                try:
                    # Fetch post content
                    post_response = requests.get(post['url'], headers=headers, timeout=10)
                    post_response.raise_for_status()
                    
                    post_soup = BeautifulSoup(post_response.text, 'html.parser')
                    
                    # Extract main content
                    content_elem = post_soup.find(['article', '.post-content', '.entry-content', '.content'])
                    content = content_elem.get_text() if content_elem else post_soup.get_text()
                    
                    # Check if keyword is in content
                    if keyword_lower in content.lower():
                        # Generate a summary if we don't have one
                        if not post['summary']:
                            # Find first paragraph that contains the keyword
                            paragraphs = post_soup.find_all('p')
                            for p in paragraphs:
                                p_text = p.get_text().strip()
                                if keyword_lower in p_text.lower() and len(p_text) > 50:
                                    post['summary'] = p_text
                                    break
                            
                            # If still no summary, use first paragraph
                            if not post['summary'] and paragraphs:
                                post['summary'] = paragraphs[0].get_text().strip()
                        
                        relevant_posts.append(post)
                except Exception as e:
                    print(f"Error fetching post content: {e}")
        
        # Limit to max_posts
        return relevant_posts[:max_posts]
        
    except Exception as e:
        print(f"Error scraping blog posts: {e}")
        return []

async def detect_blog_url(base_url: str) -> Optional[str]:
    """
    Detect the blog URL for a given website by examining the homepage and sitemap.
    
    Args:
        base_url: Base URL of the website
        
    Returns:
        Detected blog URL or None if not found
    """
    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to fetch the homepage
        print(f"Detecting blog URL for {base_url}")
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for common blog link patterns in the navigation
        blog_keywords = ['blog', 'news', 'articles', 'insights', 'resources']
        
        # Check navigation links
        nav_elements = soup.find_all(['nav', 'header', '.navigation', '.menu', '.navbar'])
        
        for nav in nav_elements:
            links = nav.find_all('a')
            for link in links:
                # Check link text
                if link.get_text() and any(keyword in link.get_text().lower() for keyword in blog_keywords):
                    if link.has_attr('href'):
                        blog_url = urljoin(base_url, link['href'])
                        print(f"Found blog URL from navigation: {blog_url}")
                        return blog_url
        
        # Check all links on the page
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            text = link.get_text().strip().lower()
            
            # Check if the link text or URL contains blog keywords
            if any(keyword in text for keyword in blog_keywords) or any(f'/{keyword}' in href.lower() for keyword in blog_keywords):
                blog_url = urljoin(base_url, href)
                print(f"Found blog URL from page links: {blog_url}")
                return blog_url
        
        # Try common blog URL patterns
        blog_patterns = ["/blog", "/news", "/articles", "/insights", "/resources"]
        
        for pattern in blog_patterns:
            test_url = f"{base_url}{pattern}"
            try:
                test_response = requests.head(test_url, headers=headers, timeout=5, allow_redirects=True)
                if test_response.status_code < 400:  # Valid URL if status code is 2xx or 3xx
                    print(f"Found blog URL from common patterns: {test_url}")
                    return test_url
            except Exception:
                continue
        
        # Check sitemap for blog URLs
        try:
            sitemap_url = f"{base_url}/sitemap.xml"
            sitemap_response = requests.get(sitemap_url, headers=headers, timeout=5)
            if sitemap_response.status_code == 200:
                sitemap_urls = fetch_sitemap(sitemap_url)
                
                # Look for blog URLs in the sitemap
                for url in sitemap_urls:
                    if any(f'/{keyword}' in url.lower() for keyword in blog_keywords):
                        # Extract the blog base URL
                        for keyword in blog_keywords:
                            if f'/{keyword}' in url.lower():
                                parts = url.split(f'/{keyword}')
                                if len(parts) > 1:
                                    blog_base = f"{parts[0]}/{keyword}"
                                    print(f"Found blog URL from sitemap: {blog_base}")
                                    return blog_base
        except Exception as e:
            print(f"Error checking sitemap: {e}")
        
        return None
    except Exception as e:
        print(f"Error detecting blog URL: {e}")
        return None

def fetch_sitemap(sitemap_url: str) -> List[str]:
    """
    Fetch URLs from a sitemap.xml file.
    
    Args:
        sitemap_url: URL to the sitemap.xml file
        
    Returns:
        List of URLs found in the sitemap
    """
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        
        # Parse the XML
        root = ET.fromstring(response.content)
        
        # Extract URLs (handle different XML namespaces)
        urls = []
        
        # Default namespace
        for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None and loc.text:
                urls.append(loc.text)
                
        # If no URLs found, try without namespace
        if not urls:
            for url in root.findall('.//url'):
                loc = url.find('.//loc')
                if loc is not None and loc.text:
                    urls.append(loc.text)
        
        return urls
    
    except Exception as e:
        print(f"Error fetching sitemap: {str(e)}")
        return []

def analyze_text_patterns(text: str, pattern_dict: Dict[str, List[str]]) -> Tuple[str, float]:
    """Analyze text against pattern dictionary to find best match.
    
    Uses regex pattern matching with context-aware scoring to determine
    the best matching category and confidence level.
    
    Args:
        text: Text content to analyze
        pattern_dict: Dictionary mapping categories to regex patterns
        
    Returns:
        Tuple of (best matching category, confidence score between 0 and 1)
        
    Example:
        >>> patterns = {'Business': [r'(?i)company|enterprise']}
        >>> analyze_text_patterns('Our company provides...', patterns)
        ('Business', 0.85)
    """
    # Early validation
    if not text or not pattern_dict:
        return ('Unknown', 0.0)
        
    # Normalize text and get word count for context
    text_lower = text.lower()
    word_count = len(text_lower.split())
    
    # Initialize scores with context
    scores: Dict[str, Dict[str, int]] = {
        category: {'matches': 0, 'unique_patterns': 0}
        for category in pattern_dict
    }
    
    # Analyze patterns with context
    for category, patterns in pattern_dict.items():
        unique_matches = set()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                scores[category]['matches'] += len(matches)
                unique_matches.update(matches)
        scores[category]['unique_patterns'] = len(unique_matches)
    
    # Early return if no matches
    total_matches = sum(s['matches'] for s in scores.values())
    if total_matches == 0:
        return ('Unknown', 0.0)
    
    # Calculate weighted scores
    weighted_scores = {
        category: (
            data['matches'] * 0.6 +  # Weight for total matches
            data['unique_patterns'] * 0.4  # Weight for pattern diversity
        ) / word_count  # Normalize by text length
        for category, data in scores.items()
    }
    
    # Find best category
    best_category = max(weighted_scores.items(), key=lambda x: x[1])[0]
    
    # Calculate confidence score
    confidence = min(
        weighted_scores[best_category] * 2,  # Scale up for better distribution
        1.0  # Cap at 1.0
    )
    
    # Return Unknown if confidence is too low
    return (best_category, confidence) if confidence > 0.15 else ('Unknown', 0.0)

def extract_common_topics(text: str, stop_words: Optional[Set[str]] = None) -> List[str]:
    """Extract common topics from text content.
    
    Args:
        text: Content to analyze
        stop_words: Optional set of words to exclude
        
    Returns:
        List of common topics found in content
    """
    if not text:
        return []
        
    # Default stop words
    default_stops = {
        'this', 'that', 'with', 'from', 'have', 'has', 'had',
        'what', 'when', 'where', 'who', 'which', 'why', 'how',
        'the', 'and', 'but', 'for', 'nor', 'yet', 'so'
    }
    stops = stop_words | default_stops if stop_words else default_stops
    
    # Extract and clean words
    words = re.findall(r'\b\w+\b', text.lower())
    filtered_words = [w for w in words if len(w) > 3 and w not in stops]
    
    # Count frequencies
    return [word for word, _ in Counter(filtered_words).most_common(10)]

def analyze_business_context(content: str) -> Dict[str, Any]:
    """Analyze content to determine business type and content focus.
    
    Performs comprehensive analysis of website content to determine:
    - Business type (e.g., E-commerce, SaaS)
    - Content focus (e.g., Educational, Product)
    - Common topics and themes
    - Suggested content goals
    
    Args:
        content: Website content to analyze
        
    Returns:
        Dict containing analysis results including business type,
        content type, confidence scores, topics, and content goals
        
    Example:
        >>> content = "Our e-commerce platform helps businesses..."
        >>> result = analyze_business_context(content)
        >>> result['business_type']
        'E-commerce'
    """
    # Early validation
    if not content:
        return {
            'business_type': 'Unknown',
            'content_type': 'Unknown',
            'business_confidence': 0.0,
            'content_confidence': 0.0,
            'common_topics': [],
            'content_goals': ['Build Authority']
        }
    
    # Get pattern dictionaries
    business_patterns = get_business_type_markers()
    content_patterns = get_content_type_markers()
    
    # Analyze patterns
    business_type, business_confidence = analyze_text_patterns(
        content, business_patterns
    )
    content_type, content_confidence = analyze_text_patterns(
        content, content_patterns
    )
    
    # Extract topics
    common_topics = extract_common_topics(content)
    
    # Map business types to recommended content goals
    content_goals = {
        'E-commerce': ['Drive Sales', 'Generate Leads'],
        'SaaS': ['Build Authority', 'Educate Users'],
        'Service Business': ['Generate Leads', 'Build Authority'],
        'Content Creator': ['Increase Brand Awareness', 'Build Authority'],
        'Agency': ['Generate Leads', 'Build Authority']
    }.get(business_type, ['Build Authority'])
    
    return {
        'business_type': business_type,
        'content_type': content_type,
        'business_confidence': round(business_confidence, 2),
        'content_confidence': round(content_confidence, 2),
        'common_topics': common_topics,
        'content_goals': content_goals
    }

def extract_content_from_url(url: str) -> Dict[str, Any]:
    """
    Extract content from a URL.
    
    Args:
        url: URL to extract content from
        
    Returns:
        Dictionary with extracted content
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No title"
        
        # Extract main content (adjust selectors based on website structure)
        content = ""
        
        # Try to find main content area (common patterns)
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        
        if main_content:
            # Remove script and style elements
            for script in main_content(["script", "style"]):
                script.extract()
            
            # Get text
            content = main_content.get_text(separator="\n").strip()
        else:
            # Fallback: get all text from body
            body = soup.find('body')
            if body:
                for script in body(["script", "style"]):
                    script.extract()
                content = body.get_text(separator="\n").strip()
        
        # Clean up content (remove excessive whitespace)
        content = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "timestamp": time.time(),
            "business_context": business_context
        }
    
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return {
            "url": url,
            "title": "Error",
            "content": f"Failed to extract content: {str(e)}",
            "timestamp": time.time()
        }

def save_content_to_context(content: Dict[str, Any], context_dir: str = "context") -> str:
    """
    Save extracted content to a context file.
    
    Args:
        content: Dictionary with extracted content
        context_dir: Directory to save context files
        
    Returns:
        Path to saved file
    """
    # Create context directory if it doesn't exist
    context_path = Path(context_dir)
    context_path.mkdir(exist_ok=True)
    
    # Create a filename based on the URL
    url_hash = hashlib.md5(content["url"].encode()).hexdigest()[:8]
    filename = f"web_{url_hash}_{content['title'][:30].replace(' ', '_')}.md"
    filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    
    # Create file content
    file_content = f"""# {content['title']}

URL: {content['url']}
Extracted: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(content['timestamp']))}

## Content

{content['content']}
"""
    
    # Save to file
    file_path = context_path / filename
    file_path.write_text(file_content)
    
    return str(file_path)

def scrape_website_to_context(sitemap_url: str, max_urls: int = 10) -> List[str]:
    """
    Scrape a website using its sitemap and save content to context files.
    
    Args:
        sitemap_url: URL to the sitemap.xml file
        max_urls: Maximum number of URLs to scrape
        
    Returns:
        List of paths to saved context files
    """
    # Fetch URLs from sitemap
    urls = fetch_sitemap(sitemap_url)
    
    # Limit the number of URLs
    urls = urls[:max_urls]
    
    saved_files = []
    
    # Process each URL
    for url in urls:
        print(f"Scraping {url}...")
        content = extract_content_from_url(url)
        file_path = save_content_to_context(content)
        saved_files.append(file_path)
        
        # Be nice to the server
        time.sleep(1)
    
    return saved_files

def load_context_files(context_dir: str = "context") -> Dict[str, str]:
    """
    Load and process context files from the context directory.
    
    Args:
        context_dir: Directory containing context files
        
    Returns:
        Dictionary mapping filenames to content
    """
    context_data = {}
    context_path = Path(context_dir)
    
    if not context_path.exists():
        print(f"Context directory {context_dir} not found")
        return {}
    
    # Process all files in the directory
    for file_path in context_path.glob("*"):
        try:
            # Skip directories
            if file_path.is_dir():
                continue
                
            # Process based on file extension
            if file_path.suffix.lower() in ['.md', '.txt']:
                # Text files
                context_data[file_path.name] = file_path.read_text()
            elif file_path.suffix.lower() in ['.json']:
                # JSON files
                try:
                    data = json.loads(file_path.read_text())
                    # Convert JSON to string representation
                    context_data[file_path.name] = json.dumps(data, indent=2)
                except json.JSONDecodeError:
                    context_data[file_path.name] = f"Error: Invalid JSON in {file_path.name}"
            elif file_path.suffix.lower() in ['.csv']:
                # CSV files - simple text representation
                context_data[file_path.name] = file_path.read_text()
            elif file_path.suffix.lower() in ['.html', '.htm']:
                # HTML files - extract text content
                try:
                    soup = BeautifulSoup(file_path.read_text(), 'html.parser')
                    for script in soup(["script", "style"]):
                        script.extract()
                    context_data[file_path.name] = soup.get_text(separator="\n").strip()
                except Exception as e:
                    context_data[file_path.name] = f"Error parsing HTML: {str(e)}"
            else:
                # Other file types - read as text if possible
                try:
                    context_data[file_path.name] = file_path.read_text()
                except UnicodeDecodeError:
                    context_data[file_path.name] = f"Binary file: {file_path.name}"
        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    return context_data

if __name__ == "__main__":
    # Example usage
    sitemap_url = "https://www.webability.io/sitemap.xml"
    saved_files = scrape_website_to_context(sitemap_url, max_urls=5)
    print(f"Saved {len(saved_files)} context files")
