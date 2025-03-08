"""
Cost tracker for monitoring API usage and associated costs.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class CostTracker:
    """Track API usage costs for various providers."""
    
    def __init__(self, log_file: str = "api_cost_log.md"):
        """
        Initialize the cost tracker.
        
        Args:
            log_file: Path to the log file (relative to project root)
        """
        self.log_file = Path(log_file)
        self.cost_rates = {
            # OpenAI models
            "gpt-4": 0.03,  # $0.03 per 1K input tokens
            "gpt-4-output": 0.06,  # $0.06 per 1K output tokens
            "gpt-4-turbo": 0.01,  # $0.01 per 1K input tokens
            "gpt-4-turbo-output": 0.03,  # $0.03 per 1K output tokens
            "gpt-4o-mini": 0.005,  # $0.005 per 1K input tokens
            "gpt-4o-mini-output": 0.015,  # $0.015 per 1K output tokens
            "gpt-3.5-turbo": 0.0015,  # $0.0015 per 1K input tokens
            "gpt-3.5-turbo-output": 0.002,  # $0.002 per 1K output tokens
            "text-embedding-ada-002": 0.0001,  # $0.0001 per 1K tokens
            
            # Anthropic models
            "claude-3-opus": 0.015,  # $0.015 per 1K input tokens
            "claude-3-opus-output": 0.075,  # $0.075 per 1K output tokens
            "claude-3-sonnet": 0.003,  # $0.003 per 1K input tokens
            "claude-3-sonnet-output": 0.015,  # $0.015 per 1K output tokens
            "claude-3-haiku": 0.00025,  # $0.00025 per 1K input tokens
            "claude-3-haiku-output": 0.00125,  # $0.00125 per 1K output tokens
            
            # Perplexity models
            "sonar-small-online": 0.0008,  # $0.0008 per 1K tokens
            "sonar-medium-online": 0.0024,  # $0.0024 per 1K tokens
            "sonar-large-online": 0.0080,  # $0.0080 per 1K tokens
            "sonar-deep-research": 0.0080,  # $0.0080 per 1K tokens
        }
        
        # Initialize log file if it doesn't exist
        if not self.log_file.exists():
            self._initialize_log_file()
    
    def _initialize_log_file(self) -> None:
        """Initialize the log file with header."""
        header = """# API Cost Tracking Log

This file tracks API usage and associated costs for various providers.

| Timestamp | Provider | Model | Operation | Input Tokens | Output Tokens | Cost ($) | Cumulative Cost ($) |
|-----------|----------|-------|-----------|--------------|---------------|----------|---------------------|
"""
        self.log_file.write_text(header)
    
    def log_api_call(self, 
                    provider: str, 
                    model: str, 
                    operation: str, 
                    input_tokens: int, 
                    output_tokens: int = 0) -> float:
        """
        Log an API call and calculate its cost.
        
        Args:
            provider: API provider (e.g., "openai", "anthropic", "perplexity")
            model: Model name (e.g., "gpt-4", "claude-3-opus")
            operation: Operation type (e.g., "completion", "embedding")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (for completion operations)
            
        Returns:
            float: Cost of the API call in dollars
        """
        # Calculate cost
        input_cost_rate = self.cost_rates.get(model, 0)
        output_cost_rate = self.cost_rates.get(f"{model}-output", input_cost_rate * 2)  # Default to 2x input cost
        
        input_cost = (input_tokens / 1000) * input_cost_rate
        output_cost = (output_tokens / 1000) * output_cost_rate
        total_cost = input_cost + output_cost
        
        # Get current cumulative cost
        cumulative_cost = self._get_cumulative_cost() + total_cost
        
        # Format log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"| {timestamp} | {provider} | {model} | {operation} | {input_tokens} | {output_tokens} | ${total_cost:.4f} | ${cumulative_cost:.4f} |\n"
        
        # Append to log file
        with open(self.log_file, "a") as f:
            f.write(log_entry)
        
        return total_cost
    
    def _get_cumulative_cost(self) -> float:
        """Get the current cumulative cost from the log file."""
        if not self.log_file.exists():
            return 0.0
            
        content = self.log_file.read_text()
        lines = content.strip().split("\n")
        
        # If only header is present
        if len(lines) <= 3:
            return 0.0
            
        # Get the last line and extract cumulative cost
        last_line = lines[-1]
        parts = last_line.split("|")
        
        if len(parts) >= 8:
            try:
                return float(parts[7].strip().replace("$", ""))
            except (ValueError, IndexError):
                return 0.0
        
        return 0.0
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get a summary of API usage costs.
        
        Returns:
            Dict containing cost summary by provider and model
        """
        if not self.log_file.exists():
            return {"total_cost": 0.0, "providers": {}, "models": {}}
            
        content = self.log_file.read_text()
        lines = content.strip().split("\n")[3:]  # Skip header rows
        
        summary = {
            "total_cost": 0.0,
            "providers": {},
            "models": {},
            "operations": {}
        }
        
        for line in lines:
            if not line.strip() or "|" not in line:
                continue
                
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 8:
                continue
                
            try:
                provider = parts[2]
                model = parts[3]
                operation = parts[4]
                cost = float(parts[6].replace("$", ""))
                
                # Update total cost
                summary["total_cost"] += cost
                
                # Update provider costs
                if provider not in summary["providers"]:
                    summary["providers"][provider] = 0.0
                summary["providers"][provider] += cost
                
                # Update model costs
                if model not in summary["models"]:
                    summary["models"][model] = 0.0
                summary["models"][model] += cost
                
                # Update operation costs
                if operation not in summary["operations"]:
                    summary["operations"][operation] = 0.0
                summary["operations"][operation] += cost
                
            except (ValueError, IndexError):
                continue
        
        return summary
    
    def generate_cost_report(self) -> str:
        """
        Generate a detailed cost report in markdown format.
        
        Returns:
            str: Markdown formatted cost report
        """
        summary = self.get_cost_summary()
        
        report = [
            "# API Cost Usage Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"## Total Cost: ${summary['total_cost']:.4f}",
            "",
            "## Cost by Provider",
            ""
        ]
        
        # Add provider costs
        for provider, cost in summary["providers"].items():
            report.append(f"- **{provider}**: ${cost:.4f}")
        
        report.extend([
            "",
            "## Cost by Model",
            ""
        ])
        
        # Add model costs
        for model, cost in summary["models"].items():
            report.append(f"- **{model}**: ${cost:.4f}")
        
        report.extend([
            "",
            "## Cost by Operation",
            ""
        ])
        
        # Add operation costs
        for operation, cost in summary["operations"].items():
            report.append(f"- **{operation}**: ${cost:.4f}")
        
        return "\n".join(report)
    
    def save_cost_report(self, output_file: str = "api_cost_report.md") -> str:
        """
        Generate and save a cost report to a file.
        
        Args:
            output_file: Path to save the report
            
        Returns:
            str: Path to the saved report
        """
        report = self.generate_cost_report()
        output_path = Path(output_file)
        output_path.write_text(report)
        return str(output_path)


# Singleton instance for global use
_cost_tracker = None

def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker

def log_api_call(provider: str, model: str, operation: str, 
                input_tokens: int, output_tokens: int = 0) -> float:
    """
    Log an API call using the global cost tracker.
    
    Args:
        provider: API provider (e.g., "openai", "anthropic", "perplexity")
        model: Model name (e.g., "gpt-4", "claude-3-opus")
        operation: Operation type (e.g., "completion", "embedding")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens (for completion operations)
        
    Returns:
        float: Cost of the API call in dollars
    """
    tracker = get_cost_tracker()
    return tracker.log_api_call(provider, model, operation, input_tokens, output_tokens)

def generate_cost_report() -> str:
    """Generate a cost report using the global cost tracker."""
    tracker = get_cost_tracker()
    return tracker.generate_cost_report()

def save_cost_report(output_file: str = "api_cost_report.md") -> str:
    """Save a cost report using the global cost tracker."""
    tracker = get_cost_tracker()
    return tracker.save_cost_report(output_file)