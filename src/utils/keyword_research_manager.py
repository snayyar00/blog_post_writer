"""
Keyword research manager that maintains freshness and tracks long-term keyword plans.
Uses functional programming patterns and maintains research logs.
"""
from typing import List, Dict, Optional, Set
from datetime import datetime
import json
from pathlib import Path
import random
from pydantic import BaseModel

class KeywordResearch(BaseModel):
    """Model for keyword research data."""
    timestamp: str
    primary_keyword: str
    related_keywords: List[str]
    search_volume: Optional[int] = None
    competition_level: Optional[float] = None
    content_gaps: List[str] = []
    research_notes: str = ""

def load_research_history(research_dir: Path) -> List[KeywordResearch]:
    """Load all previous keyword research records."""
    if not research_dir.exists():
        research_dir.mkdir(parents=True)
        return []
    
    research_files = list(research_dir.glob("research_*.json"))
    research_history = []
    
    for file in research_files:
        try:
            with open(file) as f:
                data = json.load(f)
                research_history.append(KeywordResearch(**data))
        except Exception as e:
            print(f"Error loading research file {file}: {e}")
    
    return sorted(research_history, key=lambda x: x.timestamp, reverse=True)

def get_used_keywords(history: List[KeywordResearch]) -> Set[str]:
    """Extract all previously used keywords."""
    used_keywords = set()
    for research in history:
        used_keywords.add(research.primary_keyword)
        used_keywords.update(research.related_keywords)
    return used_keywords

def generate_fresh_keywords(
    seed_keywords: List[str],
    used_keywords: Set[str],
    num_keywords: int = 5
) -> List[str]:
    """Generate fresh keyword ideas avoiding previously used ones."""
    fresh_keywords = [k for k in seed_keywords if k not in used_keywords]
    if not fresh_keywords:
        return random.sample(seed_keywords, min(num_keywords, len(seed_keywords)))
    return random.sample(fresh_keywords, min(num_keywords, len(fresh_keywords)))

def save_research(research: KeywordResearch, research_dir: Path) -> Path:
    """Save keyword research to a timestamped file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    research_file = research_dir / f"research_{timestamp}.json"
    
    with open(research_file, "w") as f:
        json.dump(research.model_dump(), f, indent=2)
    
    return research_file

def analyze_keyword_trends(history: List[KeywordResearch]) -> Dict[str, List[str]]:
    """Analyze keyword research history for trends and patterns."""
    if not history:
        return {
            "popular_topics": [],
            "underexplored_areas": [],
            "successful_keywords": []
        }
    
    # Count keyword frequencies
    keyword_counts = {}
    for research in history:
        keyword_counts[research.primary_keyword] = keyword_counts.get(research.primary_keyword, 0) + 1
        for kw in research.related_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
    
    # Sort keywords by frequency
    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Identify patterns
    popular_topics = [k for k, v in sorted_keywords[:5]]
    underexplored = [k for k, v in sorted_keywords if v == 1][:5]
    successful = [k for k, v in sorted_keywords if v >= 2][:5]
    
    return {
        "popular_topics": popular_topics,
        "underexplored_areas": underexplored,
        "successful_keywords": successful
    }

def plan_keyword_strategy(
    history: List[KeywordResearch],
    seed_keywords: List[str],
    num_keywords: int = 5
) -> List[str]:
    """Plan next keywords based on history and fresh ideas."""
    # Get used keywords
    used = get_used_keywords(history)
    
    # Generate fresh keywords
    fresh = generate_fresh_keywords(seed_keywords, used, num_keywords)
    
    # Analyze trends
    trends = analyze_keyword_trends(history)
    
    # Mix fresh keywords with successful ones
    successful = trends["successful_keywords"]
    if successful:
        # Take 70% fresh keywords and 30% successful ones
        num_successful = max(1, int(num_keywords * 0.3))
        num_fresh = num_keywords - num_successful
        
        selected_successful = random.sample(successful, min(num_successful, len(successful)))
        selected_fresh = random.sample(fresh, min(num_fresh, len(fresh)))
        
        return selected_fresh + selected_successful
    
    return fresh

def create_research_log(
    primary_keyword: str,
    related_keywords: List[str],
    research_dir: Path,
    notes: str = ""
) -> Path:
    """Create and save a new keyword research log."""
    research = KeywordResearch(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        primary_keyword=primary_keyword,
        related_keywords=related_keywords,
        research_notes=notes
    )
    
    return save_research(research, research_dir)

def get_keyword_suggestions(
    seed_keywords: List[str],
    research_dir: Path = Path("research"),
    num_keywords: int = 5
) -> Dict[str, List[str]]:
    """Get keyword suggestions with analysis of history."""
    # Load research history
    history = load_research_history(research_dir)
    
    # Plan keyword strategy
    planned_keywords = plan_keyword_strategy(history, seed_keywords, num_keywords)
    
    # Analyze trends
    trends = analyze_keyword_trends(history)
    
    return {
        "suggested_keywords": planned_keywords,
        "trends": trends
    }
