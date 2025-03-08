"""
Competitor analysis agent for analyzing blogs from competitors in the accessibility space.
"""

import os
import requests
import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, urljoin
import hashlib
import json
from pathlib import Path

# List of top competitors in the accessibility space
COMPETITOR_SITES = [
    "https://accessibe.com/blog",
    "https://userway.org/blog",
    "https://www.levelaccess.com/blog",
    "https://www.deque.com/blog",
    "https://www.accessibilityassociation.org/blog"
]

def fetch_competitor_blogs(competitor_url: str, max_posts: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch blog posts from a competitor's website.
    
    Args:
        competitor_url: URL of the competitor's blog
        max_posts: Maximum number of posts to fetch
        
    Returns:
        List of blog post data
    """
    try:
        # Fetch the blog index page
        response = requests.get(competitor_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract blog post links (common patterns)
        blog_links = []
        
        # Look for article elements
        articles = soup.find_all(['article', 'div'], class_=lambda c: c and ('post' in c.lower() or 'blog' in c.lower() or 'article' in c.lower()))
        
        for article in articles:
            # Find links within articles
            links = article.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                
                # Skip social media links, categories, tags
                if any(skip in href.lower() for skip in ['twitter.com', 'facebook.com', 'linkedin.com', 'category', 'tag', 'author']):
                    continue
                
                # Make sure it's a full URL
                if not href.startswith(('http://', 'https://')):
                    base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(competitor_url))
                    href = urljoin(base_url, href)
                
                # Get title if available
                title = link.get_text().strip()
                if not title and link.find('h1') or link.find('h2'):
                    title_elem = link.find('h1') or link.find('h2')
                    if title_elem:
                        title = title_elem.get_text().strip()
                
                if href not in [b['url'] for b in blog_links]:
                    blog_links.append({
                        'url': href,
                        'title': title or "Untitled Blog Post"
                    })
        
        # If no articles found, look for generic blog post links
        if not blog_links:
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Look for links that might be blog posts
                if any(pattern in href.lower() for pattern in ['/blog/', '/post/', '/article/', '.html', '.php']) and \
                   not any(skip in href.lower() for skip in ['twitter.com', 'facebook.com', 'linkedin.com', 'category', 'tag', 'author']):
                    
                    # Make sure it's a full URL
                    if not href.startswith(('http://', 'https://')):
                        base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(competitor_url))
                        href = urljoin(base_url, href)
                    
                    # Get title if available
                    title = link.get_text().strip()
                    
                    if href not in [b['url'] for b in blog_links]:
                        blog_links.append({
                            'url': href,
                            'title': title or "Untitled Blog Post"
                        })
        
        # Limit the number of posts
        blog_links = blog_links[:max_posts]
        
        # Fetch content for each blog post
        blog_posts = []
        
        for blog in blog_links:
            try:
                # Wait to be nice to the server
                time.sleep(1)
                
                # Fetch the blog post
                post_response = requests.get(blog['url'], timeout=10)
                post_response.raise_for_status()
                
                post_soup = BeautifulSoup(post_response.content, 'html.parser')
                
                # Extract main content
                content = ""
                
                # Try to find main content area
                main_content = post_soup.find('main') or post_soup.find('article') or post_soup.find('div', class_=lambda c: c and ('post' in c.lower() or 'content' in c.lower()))
                
                if main_content:
                    # Remove script and style elements
                    for script in main_content(["script", "style"]):
                        script.extract()
                    
                    # Get text
                    content = main_content.get_text(separator="\n").strip()
                else:
                    # Fallback: get all text from body
                    body = post_soup.find('body')
                    if body:
                        for script in body(["script", "style"]):
                            script.extract()
                        content = body.get_text(separator="\n").strip()
                
                # Clean up content (remove excessive whitespace)
                content = "\n".join(line.strip() for line in content.splitlines() if line.strip())
                
                # Extract headings for structure analysis
                headings = []
                for h in post_soup.find_all(['h1', 'h2', 'h3']):
                    headings.append({
                        'level': int(h.name[1]),
                        'text': h.get_text().strip()
                    })
                
                # Get word count
                words = re.findall(r'\b\w+\b', content)
                word_count = len(words)
                
                # Get paragraphs
                paragraphs = [p for p in re.split(r'\n\s*\n', content) if p.strip()]
                
                # Calculate average paragraph length
                if paragraphs:
                    avg_paragraph_length = sum(len(re.findall(r'\b\w+\b', p)) for p in paragraphs) / len(paragraphs)
                else:
                    avg_paragraph_length = 0
                
                blog_posts.append({
                    'url': blog['url'],
                    'title': blog['title'],
                    'content': content[:5000],  # Limit content size
                    'word_count': word_count,
                    'headings': headings,
                    'paragraph_count': len(paragraphs),
                    'avg_paragraph_length': avg_paragraph_length,
                    'domain': urlparse(blog['url']).netloc
                })
                
            except Exception as e:
                print(f"Error fetching blog post {blog['url']}: {str(e)}")
                continue
        
        return blog_posts
        
    except Exception as e:
        print(f"Error fetching competitor blogs from {competitor_url}: {str(e)}")
        return []

def analyze_competitor_blogs(topic: str, max_competitors: int = 3, max_posts_per_competitor: int = 3) -> Dict[str, Any]:
    """
    Analyze competitor blogs related to a specific topic.
    
    Args:
        topic: Topic to analyze
        max_competitors: Maximum number of competitors to analyze
        max_posts_per_competitor: Maximum number of posts per competitor
        
    Returns:
        Analysis of competitor blogs
    """
    results = {
        'topic': topic,
        'competitors': [],
        'insights': {
            'avg_word_count': 0,
            'avg_paragraph_length': 0,
            'common_headings': [],
            'structure_patterns': []
        }
    }
    
    # Limit the number of competitors
    competitors = COMPETITOR_SITES[:max_competitors]
    
    all_posts = []
    all_headings = []
    total_word_count = 0
    total_paragraph_length = 0
    paragraph_count = 0
    
    # Fetch blogs from each competitor
    for competitor_url in competitors:
        competitor_name = urlparse(competitor_url).netloc
        
        print(f"Analyzing competitor: {competitor_name}")
        
        # Fetch blog posts
        posts = fetch_competitor_blogs(competitor_url, max_posts=max_posts_per_competitor)
        
        if posts:
            # Calculate competitor-specific metrics
            competitor_word_count = sum(post['word_count'] for post in posts)
            competitor_paragraph_count = sum(post['paragraph_count'] for post in posts)
            competitor_paragraph_length = sum(post['avg_paragraph_length'] * post['paragraph_count'] for post in posts) / competitor_paragraph_count if competitor_paragraph_count > 0 else 0
            
            # Add to results
            results['competitors'].append({
                'name': competitor_name,
                'url': competitor_url,
                'posts': posts,
                'avg_word_count': competitor_word_count / len(posts) if posts else 0,
                'avg_paragraph_length': competitor_paragraph_length
            })
            
            # Add to overall metrics
            all_posts.extend(posts)
            all_headings.extend([h for post in posts for h in post['headings']])
            total_word_count += competitor_word_count
            total_paragraph_length += competitor_paragraph_length * competitor_paragraph_count
            paragraph_count += competitor_paragraph_count
    
    # Calculate overall metrics
    if all_posts:
        results['insights']['avg_word_count'] = total_word_count / len(all_posts)
        results['insights']['avg_paragraph_length'] = total_paragraph_length / paragraph_count if paragraph_count > 0 else 0
        
        # Analyze common headings
        heading_texts = [h['text'].lower() for h in all_headings]
        heading_patterns = []
        
        # Look for common patterns in headings
        for heading in heading_texts:
            # Check for common patterns
            if re.search(r'\b\d+\s+(?:ways|steps|tips|strategies|tactics)\b', heading, re.IGNORECASE):
                heading_patterns.append('numbered_list')
            elif re.search(r'\bhow\s+to\b', heading, re.IGNORECASE):
                heading_patterns.append('how_to')
            elif re.search(r'\bwhy\b', heading, re.IGNORECASE):
                heading_patterns.append('why_explanation')
            elif re.search(r'\bvs\.?|versus\b', heading, re.IGNORECASE):
                heading_patterns.append('comparison')
            elif re.search(r'\bguide\b|\btutorial\b', heading, re.IGNORECASE):
                heading_patterns.append('guide')
            elif re.search(r'\bcase\s+study\b|\bexample\b', heading, re.IGNORECASE):
                heading_patterns.append('case_study')
        
        # Count pattern frequencies
        from collections import Counter
        pattern_counts = Counter(heading_patterns)
        results['insights']['structure_patterns'] = [{'pattern': pattern, 'count': count} for pattern, count in pattern_counts.most_common()]
        
        # Extract common heading phrases
        common_phrases = []
        for heading in heading_texts:
            words = re.findall(r'\b\w+\b', heading.lower())
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) > 5:  # Minimum length
                    common_phrases.append(phrase)
        
        phrase_counts = Counter(common_phrases)
        results['insights']['common_headings'] = [{'phrase': phrase, 'count': count} for phrase, count in phrase_counts.most_common(10)]
    
    return results

def save_competitor_analysis(analysis: Dict[str, Any], output_dir: str = "context") -> str:
    """
    Save competitor analysis to a file.
    
    Args:
        analysis: Competitor analysis data
        output_dir: Directory to save the file
        
    Returns:
        Path to saved file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create a filename based on the topic
    topic_hash = hashlib.md5(analysis['topic'].encode()).hexdigest()[:8]
    filename = f"competitor_analysis_{topic_hash}.json"
    
    # Save to file
    file_path = output_path / filename
    with open(file_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    return str(file_path)

if __name__ == "__main__":
    # Example usage
    topic = "web accessibility best practices"
    analysis = analyze_competitor_blogs(topic)
    file_path = save_competitor_analysis(analysis)
    print(f"Competitor analysis saved to {file_path}")
