"""Standalone memory functions for storing and retrieving research results."""

from typing import Dict, Any, List
import os
import json
from datetime import datetime
from pathlib import Path

def store_research_results(research_results: Dict[str, Any]) -> bool:
    """
    Store research results in a persistent storage.
    
    Args:
        research_results: Dictionary containing research findings
        
    Returns:
        Boolean indicating success or failure
    """
    # Create memory directory if it doesn't exist
    memory_dir = Path("./memory")
    memory_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_{timestamp}.json"
    file_path = memory_dir / filename
    
    try:
        # Add timestamp to research results
        research_with_meta = {
            **research_results,
            "stored_at": datetime.now().isoformat(),
        }
        
        # Write to file
        with open(file_path, 'w') as f:
            json.dump(research_with_meta, f, indent=2)
            
        print(f"Research results stored at {file_path}")
        return True
        
    except Exception as e:
        print(f"Error storing research results: {str(e)}")
        return False
        
def retrieve_latest_research() -> Dict[str, Any]:
    """
    Retrieve the most recent research results.
    
    Returns:
        Dictionary containing the most recent research results
    """
    memory_dir = Path("./memory")
    
    if not memory_dir.exists():
        return {}
        
    # Find all research files
    research_files = list(memory_dir.glob("research_*.json"))
    
    if not research_files:
        return {}
        
    # Sort by modification time (newest first)
    latest_file = max(research_files, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error retrieving research results: {str(e)}")
        return {}
