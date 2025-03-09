"""
Manages keyword extraction and selection from context files.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
from src.utils.logging_manager import log_debug, log_info, log_warning

def load_context_files(context_dir: Path) -> Dict[str, str]:
    """Load all context files from the specified directory.
    
    Args:
        context_dir: Path to the context directory
        
    Returns:
        Dict mapping filenames to their content
    """
    context_data = {}
    if not context_dir.exists():
        log_warning(f"Context directory not found: {context_dir}", "CONTEXT")
        return context_data
    
    try:
        for file_path in context_dir.glob("*.md"):
            try:
                content = file_path.read_text()
                context_data[file_path.name] = content
                log_debug(f"Loaded context file: {file_path.name}", "CONTEXT")
            except Exception as e:
                log_warning(f"Error reading {file_path}: {e}", "CONTEXT")
    except Exception as e:
        log_warning(f"Error accessing context directory: {e}", "CONTEXT")
    
    log_info(f"Loaded {len(context_data)} context files", "CONTEXT")
    return context_data

def extract_keywords_from_context(context_data: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract keywords from context files with priority and metadata.
    
    Args:
        context_data: Dict mapping filenames to their content
        
    Returns:
        List of dicts containing keyword info (keyword, priority, source, etc.)
    """
    keywords = []
    
    # First, look for SEO Content.md as it contains high-priority keywords
    if "SEO Content.md" in context_data:
        content = context_data["SEO Content.md"]
        
        # Extract high-value keywords section
        high_value_match = re.search(r'### \*\*High-Value Keywords\*\*\s*(.*?)##', content, re.DOTALL)
        if high_value_match:
            high_value_section = high_value_match.group(1)
            # Extract keywords and their descriptions
            keyword_blocks = re.findall(r'\*\s*\*\*([^:]+):\*\*\s*([^*]+)', high_value_section)
            for keyword, description in keyword_blocks:
                keywords.append({
                    "keyword": keyword.strip(),
                    "priority": "critical",  # Highest priority for explicitly listed high-value keywords
                    "source": "SEO Content.md",
                    "description": description.strip(),
                    "frequency": 10  # Give high weight to these keywords
                })
        
        # Extract keywords from content calendar
        calendar_match = re.search(r'\| Journalist Keywords \|(.*?)##', content, re.DOTALL)
        if calendar_match:
            calendar_section = calendar_match.group(1)
            journalist_keywords = re.findall(r'\| ([^|]+?) \|', calendar_section)
            for kw_group in journalist_keywords[1:]:  # Skip header row
                for kw in kw_group.split(','):
                    if kw.strip() and not kw.strip().startswith('**'):
                        keywords.append({
                            "keyword": kw.strip(),
                            "priority": "high",
                            "source": "SEO Content.md",
                            "frequency": 5
                        })
    
    # Process other context files
    for filename, content in context_data.items():
        if filename == "SEO Content.md":
            continue  # Already processed
            
        log_debug(f"Extracting keywords from {filename}", "CONTEXT")
        
        # Extract explicitly marked keywords (in bold)
        bold_keywords = re.findall(r'\*\*([^\*]+)\*\*', content)
        for kw in bold_keywords:
            keywords.append({
                "keyword": kw.strip(),
                "priority": "high",
                "source": filename,
                "frequency": 1
            })
        
        # Extract keywords from headings
        headings = re.findall(r'#+\s*(.+)', content)
        for heading in headings:
            # Split heading into words and filter
            words = [w.strip() for w in heading.split() if len(w.strip()) > 3]
            for word in words:
                keywords.append({
                    "keyword": word.lower(),
                    "priority": "medium",
                    "source": filename,
                    "frequency": 1
                })
    
    # Count keyword frequencies
    keyword_counts = Counter(k["keyword"].lower() for k in keywords)
    
    # Update frequencies and adjust priorities
    for keyword in keywords:
        kw_lower = keyword["keyword"].lower()
        freq = keyword_counts[kw_lower]
        if keyword["priority"] != "critical":  # Don't modify frequency of critical keywords
            keyword["frequency"] = freq
            
            # Upgrade priority if keyword appears frequently
            if freq > 3 and keyword["priority"] == "medium":
                keyword["priority"] = "high"
    
    log_info(f"Extracted {len(keywords)} keywords from context", "CONTEXT")
    return keywords

def get_initial_keyword() -> str:
    """Get an initial keyword when no context is available."""
    from src.utils.keyword_history_manager import KeywordHistoryManager
    keyword_history = KeywordHistoryManager()
    
    # Default keywords with their priorities
    default_keywords = [
        ("Web Accessibility", "high"),
        ("WCAG Guidelines", "high"),
        ("ADA Compliance", "high"),
        ("Digital Inclusion", "medium"),
        ("Screen Reader Optimization", "medium"),
        ("Accessibility Testing", "medium"),
        ("Keyboard Navigation", "medium"),
        ("Color Contrast", "medium"),
        ("Alt Text Best Practices", "medium"),
        ("Accessible Forms", "medium")
    ]
    
    # First try to get keywords from context
    context_dir = Path("./context")
    if context_dir.exists():
        context_data = load_context_files(context_dir)
        if context_data:
            keywords = extract_keywords_from_context(context_data)
            if keywords:
                # Sort by priority and frequency
                priority_scores = {"critical": 3, "high": 2, "medium": 1}
                sorted_keywords = sorted(
                    keywords,
                    key=lambda x: (priority_scores.get(x["priority"], 0), x["frequency"]),
                    reverse=True
                )
                
                # Try each keyword until we find one that's not recently used
                for kw in sorted_keywords:
                    if keyword_history.is_keyword_available(kw["keyword"]):
                        log_info(f"Selected available keyword from context: {kw['keyword']}", "CONTEXT")
                        return kw["keyword"]
    
    # If no context keywords are available, try default keywords
    from random import shuffle
    shuffled_keywords = default_keywords.copy()
    shuffle(shuffled_keywords)
    
    # Try each default keyword until we find one that's not recently used
    for keyword, _ in shuffled_keywords:
        if keyword_history.is_keyword_available(keyword):
            log_info(f"Selected available default keyword: {keyword}", "CONTEXT")
            return keyword
    
    # If all keywords are in cooldown, force use the least recently used one
    least_used = min(shuffled_keywords, key=lambda x: keyword_history.get_keyword_usage(x[0])[-1] if keyword_history.get_keyword_usage(x[0]) else "")[0]
    log_warning(f"All keywords in cooldown, using least recently used: {least_used}", "CONTEXT")
    return least_used

def filter_keywords(keywords: List[Dict[str, Any]], min_frequency: int = 2) -> List[Dict[str, Any]]:
    """Filter keywords based on frequency and other criteria.
    
    Args:
        keywords: List of keyword dictionaries
        min_frequency: Minimum frequency threshold
        
    Returns:
        Filtered list of keywords
    """
    filtered = []
    seen = set()
    
    # First add all critical keywords regardless of frequency
    for kw in keywords:
        if kw["priority"] == "critical" and kw["keyword"].lower() not in seen:
            filtered.append(kw)
            seen.add(kw["keyword"].lower())
    
    # Then add other keywords that meet criteria
    for kw in keywords:
        keyword = kw["keyword"].lower()
        if (
            keyword not in seen and
            kw["priority"] != "critical" and  # Skip critical keywords as they're already added
            kw["frequency"] >= min_frequency and
            len(keyword) > 3  # Skip very short keywords
        ):
            filtered.append(kw)
            seen.add(keyword)
    
    log_info(f"Filtered {len(keywords)} keywords to {len(filtered)}", "CONTEXT")
    return filtered

def rank_keywords(keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank keywords by priority and frequency.
    
    Args:
        keywords: List of keyword dictionaries
        
    Returns:
        Sorted list of keywords
    """
    # Define priority scores
    priority_scores = {
        "critical": 4,  # Highest priority
        "high": 3,
        "medium": 2,
        "low": 1
    }
    
    # Sort by priority score (high to low) then frequency (high to low)
    ranked = sorted(
        keywords,
        key=lambda x: (
            priority_scores.get(x.get("priority", "low"), 0),
            x.get("frequency", 0)
        ),
        reverse=True
    )
    
    log_debug(f"Ranked {len(keywords)} keywords", "CONTEXT")
    return ranked

def get_keyword_suggestions(context_data: Dict[str, str], count: int = 5) -> List[str]:
    """Get top keyword suggestions from context.
    
    Args:
        context_data: Dict mapping filenames to their content
        count: Number of keywords to return
        
    Returns:
        List of top keywords
    """
    # Extract and process keywords
    keywords = extract_keywords_from_context(context_data)
    filtered = filter_keywords(keywords)
    ranked = rank_keywords(filtered)
    
    # Get top keywords
    suggestions = []
    seen = set()
    for kw in ranked:
        if len(suggestions) >= count:
            break
        keyword = kw["keyword"].lower()
        if keyword not in seen:
            suggestions.append(kw["keyword"])
            seen.add(keyword)
    
    log_info(f"Generated {len(suggestions)} keyword suggestions", "CONTEXT")
    return suggestions
