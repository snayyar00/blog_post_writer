"""
Logging manager for tracking and displaying debug information.
"""
from typing import List, Dict, Any
import time
from datetime import datetime

class LoggingManager:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
        
    def add_log(self, message: str, level: str = "INFO") -> None:
        """Add a new log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Add emoji indicators for better visibility
        level_emoji = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅",
            "PROGRESS": "🔄",
            "CONTEXT": "📚",
            "RESEARCH": "🔬",
            "KEYWORD": "🔑",
            "CONTENT": "📝",
            "QUALITY": "✨",
            "HUMANIZER": "🎨",
            "ANALYSIS": "📊",
            "MEMORY": "💾",
            "STATE": "🔄",
            "APP": "🚀"
        }
        
        # Get emoji based on level or message content
        emoji = level_emoji.get(level, None)
        if not emoji:
            # Try to determine emoji from message content
            if "context" in message.lower():
                emoji = level_emoji["CONTEXT"]
            elif "research" in message.lower():
                emoji = level_emoji["RESEARCH"]
            elif "keyword" in message.lower():
                emoji = level_emoji["KEYWORD"]
            elif "content" in message.lower():
                emoji = level_emoji["CONTENT"]
            elif "quality" in message.lower():
                emoji = level_emoji["QUALITY"]
            elif "humaniz" in message.lower():
                emoji = level_emoji["HUMANIZER"]
            elif "analy" in message.lower():
                emoji = level_emoji["ANALYSIS"]
            elif "memory" in message.lower():
                emoji = level_emoji["MEMORY"]
            elif "state" in message.lower():
                emoji = level_emoji["STATE"]
            elif "app" in message.lower():
                emoji = level_emoji["APP"]
            else:
                emoji = "📝"  # Default emoji
        
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level,
            "emoji": emoji
        }
        
        # Print to console with formatting
        print(f"{emoji} [{timestamp}] {level}: {message}")
        
        self.logs.append(log_entry)
        
        # Keep only last 5000 logs for better history
        if len(self.logs) > 5000:
            self.logs = self.logs[-5000:]
            
        # Force flush stdout to ensure logs appear immediately
        import sys
        sys.stdout.flush()
        
        # Add special system.out log processing to capture all terminal output
        try:
            # Also capture anything printed to stdout/stderr
            if "HTTP Request:" not in message and message.strip():
                # Only add it to logs if it's not already there
                if not any(log["message"] == message for log in self.logs[-10:]):
                    self.logs.append(log_entry)
        except Exception:
            pass
    
    def get_recent_logs(self, count: int = 500, level: str = None, include_empty: bool = False) -> List[Dict[str, Any]]:
        """
        Get the most recent logs with optional level filtering.
        
        Args:
            count: Number of logs to return
            level: Optional level to filter by
        """
        filtered_logs = self.logs
        
        # Filter by level if specified
        if level:
            filtered_logs = [log for log in filtered_logs if log["level"] == level.upper()]
            
        # Filter out empty messages unless explicitly included
        if not include_empty:
            filtered_logs = [log for log in filtered_logs if log.get("message", "").strip()]
            
        # Return most recent logs up to count
        return filtered_logs[-count:]
    
    def clear_logs(self) -> None:
        """Clear all logs."""
        self.logs = []

# Global logging manager instance
logging_manager = LoggingManager()

def log_debug(message: str, level: str = "DEBUG") -> None:
    """Add a debug log entry."""
    logging_manager.add_log(message, level)

def log_info(message: str, level: str = "INFO") -> None:
    """Add an info log entry with optional level type."""
    logging_manager.add_log(message, level)

def log_error(message: str, level: str = "ERROR") -> None:
    """Add an error log entry."""
    logging_manager.add_log(message, level)

def log_warning(message: str, level: str = "WARNING") -> None:
    """Add a warning log entry."""
    logging_manager.add_log(message, level)

def get_logs(count: int = 10, level: str = None) -> List[Dict[str, Any]]:
    """Get recent logs with optional level filtering."""
    logs = logging_manager.get_recent_logs(count)
    if level:
        logs = [log for log in logs if log["level"] == level.upper()]
    return logs

def clear_logs() -> None:
    """Clear all logs."""
    logging_manager.clear_logs()
