"""
Context keyword manager that extracts keywords from context files and maintains a keyword directory.
Uses functional programming patterns and follows RORO principles.
"""
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import json
import csv
import re
import os
from collections import Counter
from datetime import datetime

def load_context_files(context_dir: Path) -> Dict[str, str]:
    """
    Load all context files from the context directory.
    
    Args:
        context_dir: Path to the context directory
        
    Returns:
        Dictionary mapping filenames to file contents
    """
    if not context_dir.exists():
        return {}
    
    context_data = {}
    
    # Load all text files in the context directory
    for file_path in context_dir.glob("**/*"):
        if file_path.is_file() and file_path.suffix in ['.md', '.txt', '.csv']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                context_data[file_path.name] = content
            except Exception as e:
                print(f"Error loading context file {file_path}: {e}")
    
    return context_data

def extract_keywords_from_context(context_data: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Extract keywords from context files.
    
    Args:
        context_data: Dictionary mapping filenames to file contents
        
    Returns:
        List of keyword dictionaries with metadata
    """
    keywords = []
    
    # Look for keyword files specifically
    keyword_files = ["Webability_Updated Keyword Research.xlsx - webability.csv", "SEO Content.md"]
    keyword_candidates = []
    
    for filename, content in context_data.items():
        # Check if this is a keyword research file
        if any(kf in filename for kf in keyword_files):
            if filename.endswith(".csv") and isinstance(content, str):
                # Parse CSV content
                lines = content.strip().split("\n")
                for line in lines[1:]:  # Skip header row
                    parts = line.split(",")
                    if len(parts) >= 3 and parts[2].strip():
                        keyword = parts[2].strip().lower()
                        search_volume = int(parts[3]) if len(parts) > 3 and parts[3].strip().isdigit() else 0
                        keyword_candidates.append({
                            "keyword": keyword,
                            "source": filename,
                            "search_volume": search_volume,
                            "priority": "high" if search_volume > 100 else "medium"
                        })
            elif filename.endswith(".md") and isinstance(content, str):
                # Extract keywords from markdown content
                # Look for sections with keywords
                if "High-Value Keywords" in content:
                    section = content.split("High-Value Keywords")[1].split("##")[0]
                    # Extract keywords from bullet points
                    bullet_points = re.findall(r'\*\s*\*\*([^:]+):\*\*', section)
                    for kw in bullet_points:
                        keyword_candidates.append({
                            "keyword": kw.strip().lower(),
                            "source": filename,
                            "search_volume": 0,
                            "priority": "high"
                        })
                
                # Look for other keyword mentions
                keyword_matches = re.findall(r'\*\*([^\*]+)\*\*', content)
                potential_keywords = [match.strip().lower() for match in keyword_matches 
                                    if 3 <= len(match.strip()) <= 50 and not match.strip().startswith("http")]
                for kw in potential_keywords:
                    keyword_candidates.append({
                        "keyword": kw,
                        "source": filename,
                        "search_volume": 0,
                        "priority": "medium"
                    })
        
        # Extract keywords from business context files
        if "business_competitors.md" in filename and isinstance(content, str):
            # Extract competitor names and features
            competitor_names = re.findall(r'###\s+([^\n]+)', content)
            for name in competitor_names:
                keyword_candidates.append({
                    "keyword": name.strip().lower(),
                    "source": filename,
                    "search_volume": 0,
                    "priority": "medium",
                    "category": "competitor"
                })
            
            # Extract features
            features = re.findall(r'\*\*Unique Features\*\*:\s+([^\n]+)', content)
            for feature_list in features:
                feature_keywords = feature_list.split(",")
                for kw in feature_keywords:
                    keyword_candidates.append({
                        "keyword": kw.strip().lower(),
                        "source": filename,
                        "search_volume": 0,
                        "priority": "medium",
                        "category": "feature"
                    })
        
        # Extract keywords from WebAbility.io info
        if "WebAbility.io" in filename and isinstance(content, str):
            # Extract key phrases related to web accessibility
            phrases = ["web accessibility", "ADA compliance", "WCAG", "accessibility standards",
                      "digital accessibility", "inclusive design", "screen readers", "assistive technology"]
            
            for phrase in phrases:
                keyword_candidates.append({
                    "keyword": phrase.lower(),
                    "source": filename,
                    "search_volume": 0,
                    "priority": "high",
                    "category": "core"
                })
    
    # Count keyword frequency and prioritize
    keyword_counter = Counter([k["keyword"] for k in keyword_candidates])
    
    # Create final keyword list with metadata
    seen_keywords = set()
    for kw_data in keyword_candidates:
        keyword = kw_data["keyword"]
        if keyword not in seen_keywords and len(keyword) > 3:
            # Adjust priority based on frequency
            frequency = keyword_counter[keyword]
            if frequency > 2:
                kw_data["priority"] = "high"
            
            keywords.append({
                "keyword": keyword,
                "source": kw_data["source"],
                "search_volume": kw_data.get("search_volume", 0),
                "frequency": frequency,
                "priority": kw_data.get("priority", "medium"),
                "category": kw_data.get("category", "general")
            })
            seen_keywords.add(keyword)
    
    # Sort by priority and frequency
    return sorted(keywords, key=lambda x: (
        0 if x["priority"] == "high" else 1 if x["priority"] == "medium" else 2,
        -x["frequency"],
        -x["search_volume"]
    ))

def load_keyword_directory(directory_path: Path) -> Dict[str, Any]:
    """
    Load the keyword directory from a JSON file.
    
    Args:
        directory_path: Path to the keyword directory file
        
    Returns:
        Dictionary containing keyword directory data
    """
    if not directory_path.exists():
        return {"keywords": [], "last_updated": datetime.now().isoformat()}
    
    try:
        with open(directory_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading keyword directory: {e}")
        return {"keywords": [], "last_updated": datetime.now().isoformat()}

def save_keyword_directory(directory: Dict[str, Any], directory_path: Path) -> None:
    """
    Save the keyword directory to a JSON file.
    
    Args:
        directory: Dictionary containing keyword directory data
        directory_path: Path to save the keyword directory file
    """
    directory["last_updated"] = datetime.now().isoformat()
    
    # Ensure directory exists
    directory_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(directory_path, 'w', encoding='utf-8') as f:
            json.dump(directory, f, indent=2)
    except Exception as e:
        print(f"Error saving keyword directory: {e}")

def update_keyword_directory(context_dir: Path, directory_path: Path) -> Dict[str, Any]:
    """
    Update the keyword directory with keywords from context files.
    
    Args:
        context_dir: Path to the context directory
        directory_path: Path to the keyword directory file
        
    Returns:
        Updated keyword directory dictionary
    """
    # Load existing directory
    directory = load_keyword_directory(directory_path)
    
    # Load context files
    context_data = load_context_files(context_dir)
    
    # Extract keywords from context
    new_keywords = extract_keywords_from_context(context_data)
    
    # Create a set of existing keywords
    existing_keywords = {kw["keyword"] for kw in directory.get("keywords", [])}
    
    # Add new keywords
    for kw_data in new_keywords:
        if kw_data["keyword"] not in existing_keywords:
            directory.setdefault("keywords", []).append(kw_data)
            existing_keywords.add(kw_data["keyword"])
    
    # Save updated directory
    save_keyword_directory(directory, directory_path)
    
    return directory

def get_top_keywords(directory: Dict[str, Any], count: int = 10, category: Optional[str] = None) -> List[str]:
    """
    Get top keywords from the directory.
    
    Args:
        directory: Keyword directory dictionary
        count: Number of keywords to return
        category: Optional category filter
        
    Returns:
        List of top keywords
    """
    keywords = directory.get("keywords", [])
    
    # Filter by category if specified
    if category:
        keywords = [kw for kw in keywords if kw.get("category") == category]
    
    # Sort by priority, frequency, and search volume
    sorted_keywords = sorted(keywords, key=lambda x: (
        0 if x.get("priority") == "high" else 1 if x.get("priority") == "medium" else 2,
        -x.get("frequency", 0),
        -x.get("search_volume", 0)
    ))
    
    # Return top keywords
    return [kw["keyword"] for kw in sorted_keywords[:count]]

def get_random_keyword(directory: Dict[str, Any], category: Optional[str] = None) -> str:
    """
    Get a random keyword from the directory.
    
    Args:
        directory: Keyword directory dictionary
        category: Optional category filter
        
    Returns:
        Random keyword string
    """
    import random
    
    keywords = directory.get("keywords", [])
    
    # Filter by category if specified
    if category:
        keywords = [kw for kw in keywords if kw.get("category") == category]
    
    # Filter to high priority keywords
    high_priority = [kw for kw in keywords if kw.get("priority") == "high"]
    
    # Use high priority if available, otherwise use all
    keyword_pool = high_priority if high_priority else keywords
    
    if not keyword_pool:
        return "web accessibility"  # Default fallback
    
    # Select random keyword
    selected = random.choice(keyword_pool)
    return selected["keyword"]

def get_initial_keyword() -> str:
    """
    Get an initial keyword from the context files.
    
    Returns:
        Initial keyword string
    """
    context_dir = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "context"))
    directory_path = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "keyword_directory.json"))
    
    # Update directory if it doesn't exist or is older than 1 day
    if not directory_path.exists() or (datetime.now() - datetime.fromtimestamp(directory_path.stat().st_mtime)).days > 0:
        directory = update_keyword_directory(context_dir, directory_path)
    else:
        directory = load_keyword_directory(directory_path)
    
    # Get a random high-priority keyword
    return get_random_keyword(directory)
