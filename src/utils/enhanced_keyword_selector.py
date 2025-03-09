"""
Enhanced keyword selector with core topic rotation and variation management.
Uses OpenAI for smart keyword selection and validation.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os
from openai import AsyncOpenAI
from src.utils.logging_manager import log_info, log_warning, log_error, log_debug

# Core topics that should be regularly rotated
CORE_TOPICS = {
    "web_accessibility": {
        "main": "Web Accessibility",
        "variations": ["Website Accessibility", "Digital Accessibility"],
        "frequency": 4  # Use every 4th post
    },
    "wcag": {
        "main": "WCAG Compliance",
        "variations": ["WCAG Guidelines", "WCAG Standards"],
        "frequency": 4
    },
    "ada": {
        "main": "ADA Compliance",
        "variations": ["ADA Requirements", "ADA Standards"],
        "frequency": 4
    }
}

class EnhancedKeywordSelector:
    def __init__(self, data_dir: Path = Path("data"), context_dir: Path = Path("context")):
        """Initialize the enhanced keyword selector.
        
        Args:
            data_dir: Directory for storing keyword data
            context_dir: Directory containing context files
        """
        self.data_dir = data_dir
        self.context_dir = context_dir
        self.history_file = data_dir / "enhanced_keyword_history.json"
        self.metrics_file = data_dir / "keyword_metrics.json"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load history and metrics
        self.history = self._load_history()
        self.metrics = self._load_metrics()
        
        log_debug("Enhanced keyword selector initialized", "KEYWORD")
    
    def _load_history(self) -> Dict[str, List[str]]:
        """Load keyword usage history."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            log_warning(f"Error loading keyword history: {e}", "KEYWORD")
        return {}
    
    def _save_history(self) -> None:
        """Save keyword usage history."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            log_error(f"Error saving keyword history: {e}", "KEYWORD")
    
    def _load_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Load keyword metrics."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            log_warning(f"Error loading keyword metrics: {e}", "KEYWORD")
        return {}
    
    def _save_metrics(self) -> None:
        """Save keyword metrics."""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            log_error(f"Error saving keyword metrics: {e}", "KEYWORD")
    
    def is_core_topic(self, keyword: str) -> bool:
        """Check if a keyword is a core topic.
        
        Args:
            keyword: Keyword to check
            
        Returns:
            bool: True if keyword is a core topic
        """
        return any(
            keyword in [topic["main"]] + topic["variations"]
            for topic in CORE_TOPICS.values()
        )
    
    def is_core_topic_due(self) -> bool:
        """Check if it's time for a core topic based on history.
        
        Returns:
            bool: True if a core topic should be used next
        """
        if not self.history:
            return True  # Start with a core topic
        
        # Get the last 4 used keywords
        all_uses = []
        for keyword, timestamps in self.history.items():
            all_uses.extend((keyword, ts) for ts in timestamps)
        
        # Sort by timestamp (newest first)
        all_uses.sort(key=lambda x: x[1], reverse=True)
        recent_keywords = [kw for kw, _ in all_uses[:4]]
        
        # If no core topics in last 3 posts, it's time for one
        core_topics_used = sum(1 for kw in recent_keywords[:3] if self.is_core_topic(kw))
        return core_topics_used == 0
    
    async def get_next_keyword(self) -> str:
        """Get the next keyword to use, considering core topic rotation.
        
        Returns:
            str: Selected keyword
        """
        try:
            if self.is_core_topic_due():
                # Get least recently used core topic
                core_topics = []
                for topic in CORE_TOPICS.values():
                    main_keyword = topic["main"]
                    last_used = max(self.history.get(main_keyword, []) + ["1970-01-01"])
                    core_topics.append((main_keyword, last_used))
                
                # Sort by last used (oldest first)
                core_topics.sort(key=lambda x: x[1])
                return core_topics[0][0]
            
            # Get a variation topic
            # First, load all potential keywords from context
            keywords = await self._get_context_keywords()
            
            # Filter out recently used keywords
            available_keywords = [
                kw for kw in keywords
                if not self.history.get(kw) or  # Never used
                datetime.fromisoformat(max(self.history[kw])) < datetime.now() - timedelta(days=7)  # Not used in last 7 days
            ]
            
            if not available_keywords:
                # If no keywords available, use least recently used one
                all_keywords = []
                for kw, timestamps in self.history.items():
                    last_used = max(timestamps)
                    all_keywords.append((kw, last_used))
                all_keywords.sort(key=lambda x: x[1])  # Sort by last used
                return all_keywords[0][0]
            
            # Use OpenAI to pick the best keyword
            selected = await self._validate_with_openai(available_keywords)
            return selected
            
        except Exception as e:
            log_error(f"Error getting next keyword: {e}", "KEYWORD")
            # Fallback to a core topic
            return CORE_TOPICS["web_accessibility"]["main"]
    
    async def _get_context_keywords(self) -> List[str]:
        """Extract keywords from context files."""
        keywords = []
        
        try:
            # First check SEO Content file
            seo_file = self.context_dir / "SEO Content.md"
            if seo_file.exists():
                content = seo_file.read_text()
                # Extract keywords from high-value section
                import re
                matches = re.findall(r'\*\*([^\*]+)\*\*', content)
                keywords.extend(matches)
            
            # Get keywords from other context files
            for file_path in self.context_dir.glob("*.md"):
                if file_path.name == "SEO Content.md":
                    continue
                try:
                    content = file_path.read_text()
                    # Extract bold text as keywords
                    matches = re.findall(r'\*\*([^\*]+)\*\*', content)
                    keywords.extend(matches)
                except Exception as e:
                    log_warning(f"Error reading {file_path}: {e}", "KEYWORD")
            
        except Exception as e:
            log_warning(f"Error extracting context keywords: {e}", "KEYWORD")
        
        return list(set(keywords))  # Remove duplicates
    
    async def _validate_with_openai(self, keywords: List[str]) -> str:
        """Use OpenAI to validate and select the best keyword.
        
        Args:
            keywords: List of potential keywords
            
        Returns:
            str: Selected keyword
        """
        try:
            # Get recently used keywords for context
            recent = []
            for kw, timestamps in self.history.items():
                if timestamps:  # If keyword has been used
                    last_used = max(timestamps)
                    if datetime.fromisoformat(last_used) > datetime.now() - timedelta(days=14):
                        recent.append(kw)
            
            # Create prompt for OpenAI
            prompt = f"""Given these potential keywords for a web accessibility blog post:
{', '.join(keywords)}

And these recently used topics:
{', '.join(recent)}

Select the BEST keyword to write about next, considering:
1. SEO value and search intent
2. Avoiding topics too similar to recent posts
3. Logical progression of content
4. Current relevance

Return ONLY the selected keyword, nothing else."""
            
            # Get OpenAI's selection
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=50
            )
            
            selected = response.choices[0].message.content.strip()
            
            # Validate selection is in our keyword list
            if selected in keywords:
                return selected
            else:
                # If OpenAI returned invalid keyword, use first available
                return keywords[0]
                
        except Exception as e:
            log_error(f"Error validating with OpenAI: {e}", "KEYWORD")
            # Fallback to first keyword
            return keywords[0]
    
    def record_keyword_use(self, keyword: str) -> None:
        """Record the use of a keyword.
        
        Args:
            keyword: The keyword that was used
        """
        timestamp = datetime.now().isoformat()
        
        # Update history
        if keyword not in self.history:
            self.history[keyword] = []
        self.history[keyword].append(timestamp)
        self._save_history()
        
        # Update metrics
        if keyword not in self.metrics:
            self.metrics[keyword] = {
                "use_count": 0,
                "variations": [],
                "last_used": None
            }
        
        self.metrics[keyword]["use_count"] += 1
        self.metrics[keyword]["last_used"] = timestamp
        self._save_metrics()
        
        log_info(f"Recorded use of keyword: {keyword}", "KEYWORD")
    
    def get_keyword_history(self, keyword: str) -> List[str]:
        """Get usage history for a keyword.
        
        Args:
            keyword: Keyword to get history for
            
        Returns:
            List[str]: List of timestamps when keyword was used
        """
        return self.history.get(keyword, [])
    
    def get_keyword_metrics(self, keyword: str) -> Dict[str, Any]:
        """Get metrics for a keyword.
        
        Args:
            keyword: Keyword to get metrics for
            
        Returns:
            Dict containing keyword metrics
        """
        return self.metrics.get(keyword, {
            "use_count": 0,
            "variations": [],
            "last_used": None
        })
    
    async def get_keyword_variations(self, keyword: str) -> List[str]:
        """Get variations of a keyword using OpenAI.
        
        Args:
            keyword: Base keyword to get variations for
            
        Returns:
            List[str]: List of keyword variations
        """
        try:
            # First check if it's a core topic
            for topic in CORE_TOPICS.values():
                if keyword == topic["main"]:
                    return topic["variations"]
            
            # If not a core topic, ask OpenAI for variations
            prompt = f"""Generate 3 variations of the keyword "{keyword}" that:
1. Maintain the same search intent
2. Use different but related phrasing
3. Are natural and commonly searched

Return ONLY a comma-separated list of variations, nothing else."""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            variations = [v.strip() for v in response.choices[0].message.content.split(",")]
            
            # Update metrics
            if keyword in self.metrics:
                self.metrics[keyword]["variations"] = variations
                self._save_metrics()
            
            return variations
            
        except Exception as e:
            log_error(f"Error getting keyword variations: {e}", "KEYWORD")
            return []
