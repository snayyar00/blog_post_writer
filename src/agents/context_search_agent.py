"""
Context search agent for finding relevant information in context files.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re
from collections import Counter

def search_context_files(query: str, context_data: Dict[str, str], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Search through context files for relevant information.
    
    Args:
        query: Search query
        context_data: Dictionary of context files
        top_n: Number of top results to return
        
    Returns:
        List of relevant context snippets with metadata
    """
    if not query or not context_data:
        return []
    
    # Normalize query
    query_terms = set(re.findall(r'\b\w+\b', query.lower()))
    
    # Search results
    results = []
    
    for filename, content in context_data.items():
        # Skip empty content
        if not content:
            continue
            
        # Calculate relevance score based on term frequency
        content_lower = content.lower()
        
        # Simple term frequency scoring
        score = sum(content_lower.count(term) for term in query_terms)
        
        # Boost score for files with query terms in filename
        filename_lower = filename.lower()
        filename_score = sum(3 for term in query_terms if term in filename_lower)
        score += filename_score
        
        # If score is positive, extract relevant snippets
        if score > 0:
            # Find paragraphs containing query terms
            paragraphs = re.split(r'\n\s*\n', content)
            
            for paragraph in paragraphs:
                paragraph_lower = paragraph.lower()
                paragraph_score = sum(paragraph_lower.count(term) for term in query_terms)
                
                if paragraph_score > 0:
                    # Clean up paragraph
                    clean_paragraph = paragraph.strip()
                    if len(clean_paragraph) > 30:  # Minimum length to be considered
                        results.append({
                            "filename": filename,
                            "content": clean_paragraph,
                            "score": paragraph_score + (filename_score * 0.5),  # Weight filename less for snippets
                            "type": "paragraph"
                        })
    
    # Sort by score (descending)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top N results
    return results[:top_n]

def extract_blog_titles(context_data: Dict[str, str]) -> List[str]:
    """
    Extract blog titles from context files.
    
    Args:
        context_data: Dictionary of context files
        
    Returns:
        List of blog titles
    """
    titles = []
    
    for filename, content in context_data.items():
        # Skip empty content
        if not content:
            continue
            
        # Look for titles in markdown format (# Title)
        title_matches = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
        titles.extend(title_matches)
        
        # Look for titles in HTML format (<h1>Title</h1>)
        html_title_matches = re.findall(r'<h1[^>]*>([^<]+)</h1>', content, re.IGNORECASE)
        titles.extend(html_title_matches)
        
        # If file starts with "web_", extract title from filename
        if filename.startswith("web_"):
            parts = filename.split("_", 2)
            if len(parts) > 2:
                # Convert underscores to spaces and clean up
                file_title = parts[2].replace("_", " ").replace(".md", "").replace(".txt", "")
                if file_title:
                    titles.append(file_title)
    
    # Remove duplicates and empty titles
    return [title.strip() for title in titles if title.strip()]

def extract_keywords_from_context(context_data: Dict[str, str], min_length: int = 4, min_count: int = 2) -> List[Tuple[str, int]]:
    """
    Extract common keywords from context files.
    
    Args:
        context_data: Dictionary of context files
        min_length: Minimum length of keywords to consider
        min_count: Minimum count of keywords to include
        
    Returns:
        List of (keyword, count) tuples
    """
    # Combine all content
    all_content = " ".join(content for content in context_data.values())
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z][a-zA-Z-]+\b', all_content.lower())
    
    # Filter out common stop words
    stop_words = {
        "the", "and", "a", "to", "of", "in", "is", "that", "it", "with", "for", "as", "are", 
        "on", "be", "this", "was", "by", "not", "or", "from", "an", "but", "what", "all", 
        "were", "we", "when", "your", "can", "said", "there", "use", "have", "each", "which", 
        "their", "will", "other", "about", "how", "been", "if", "some", "them"
    }
    
    filtered_words = [word for word in words if word not in stop_words and len(word) >= min_length]
    
    # Count occurrences
    word_counts = Counter(filtered_words)
    
    # Get words that appear at least min_count times
    common_words = [(word, count) for word, count in word_counts.items() if count >= min_count]
    
    # Sort by count (descending)
    common_words.sort(key=lambda x: x[1], reverse=True)
    
    return common_words

def find_related_content(topic: str, context_data: Dict[str, str], top_n: int = 5) -> Dict[str, Any]:
    """
    Find content related to a topic in context files.
    
    Args:
        topic: Topic to find related content for
        context_data: Dictionary of context files
        top_n: Number of top results to return
        
    Returns:
        Dictionary with related content
    """
    # Search for relevant paragraphs
    relevant_paragraphs = search_context_files(topic, context_data, top_n=top_n)
    
    # Extract blog titles
    blog_titles = extract_blog_titles(context_data)
    
    # Extract common keywords
    common_keywords = extract_keywords_from_context(context_data)
    
    return {
        "relevant_paragraphs": relevant_paragraphs,
        "blog_titles": blog_titles[:10],  # Limit to 10 titles
        "common_keywords": common_keywords[:20],  # Limit to 20 keywords
        "topic": topic
    }

if __name__ == "__main__":
    # Example usage
    context_dir = Path("./context")
    context_data = {}
    
    for file_path in context_dir.glob("*"):
        if file_path.is_file():
            try:
                context_data[file_path.name] = file_path.read_text()
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    results = find_related_content("web accessibility", context_data)
    print(json.dumps(results, indent=2))
