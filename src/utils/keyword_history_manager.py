"""
Manages keyword history and usage tracking to prevent duplicate content generation.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.logging_manager import log_debug, log_info, log_warning

class KeywordHistoryManager:
    def __init__(self, cooldown_days: int = 1):
        """Initialize the keyword history manager.
        
        Args:
            cooldown_days: Number of days before a keyword can be reused
        """
        self.cooldown_days = cooldown_days
        self.history_file = Path("data/keyword_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.keyword_history: Dict[str, List[str]] = self._load_history()
        log_debug("Keyword history manager initialized", "KEYWORD")
    
    def _load_history(self) -> Dict[str, List[str]]:
        """Load keyword usage history from file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    history = json.load(f)
                log_info(f"Loaded {len(history)} keywords from history", "KEYWORD")
                return history
        except Exception as e:
            log_warning(f"Error loading keyword history: {e}", "KEYWORD")
        return {}
    
    def _save_history(self) -> None:
        """Save keyword usage history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.keyword_history, f, indent=2)
            log_debug("Keyword history saved successfully", "KEYWORD")
        except Exception as e:
            log_warning(f"Error saving keyword history: {e}", "KEYWORD")
    
    def record_keyword_use(self, keyword: str) -> None:
        """Record the use of a keyword with current timestamp.
        
        Args:
            keyword: The keyword that was used
        """
        timestamp = datetime.now().isoformat()
        if keyword not in self.keyword_history:
            self.keyword_history[keyword] = []
        self.keyword_history[keyword].append(timestamp)
        log_info(f"Recorded use of keyword: {keyword}", "KEYWORD")
        self._save_history()
    
    def is_keyword_available(self, keyword: str) -> bool:
        """Check if a keyword is available for use.
        
        Args:
            keyword: The keyword to check
            
        Returns:
            bool: True if the keyword can be used, False if in cooldown
        """
        if keyword not in self.keyword_history:
            log_debug(f"Keyword '{keyword}' has never been used", "KEYWORD")
            return True
        
        if not self.keyword_history[keyword]:
            log_debug(f"Keyword '{keyword}' has no usage history", "KEYWORD")
            return True
        
        last_used = datetime.fromisoformat(self.keyword_history[keyword][-1])
        cooldown_period = timedelta(days=self.cooldown_days)
        is_available = datetime.now() - last_used > cooldown_period
        
        if not is_available:
            hours_remaining = ((last_used + cooldown_period - datetime.now()).total_seconds() / 3600)
            log_debug(f"Keyword '{keyword}' in cooldown for {hours_remaining:.1f} more hours", "KEYWORD")
        else:
            log_debug(f"Keyword '{keyword}' is available for use", "KEYWORD")
        
        return is_available
    
    def get_keyword_usage(self, keyword: str) -> List[str]:
        """Get usage history for a specific keyword.
        
        Args:
            keyword: The keyword to get history for
            
        Returns:
            List[str]: List of timestamps when the keyword was used
        """
        return self.keyword_history.get(keyword, [])
    
    def get_all_keywords(self) -> List[str]:
        """Get list of all tracked keywords.
        
        Returns:
            List[str]: List of all keywords that have been used
        """
        return list(self.keyword_history.keys())
    
    def clear_history(self) -> None:
        """Clear all keyword history."""
        self.keyword_history = {}
        self._save_history()
        log_info("Keyword history cleared", "KEYWORD")
    
    def remove_keyword(self, keyword: str) -> bool:
        """Remove a keyword and its history.
        
        Args:
            keyword: The keyword to remove
            
        Returns:
            bool: True if keyword was removed, False if not found
        """
        if keyword in self.keyword_history:
            del self.keyword_history[keyword]
            self._save_history()
            log_info(f"Removed keyword: {keyword}", "KEYWORD")
            return True
        log_warning(f"Keyword not found: {keyword}", "KEYWORD")
        return False
