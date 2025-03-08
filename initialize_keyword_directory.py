"""
Initialize the keyword directory from context files.
This script should be run once to create the initial keyword directory.
"""
import asyncio
from pathlib import Path
import os
from src.utils.context_keyword_manager import update_keyword_directory

async def main():
    # Define paths
    context_dir = Path(os.path.join(os.path.dirname(__file__), "context"))
    directory_path = Path(os.path.join(os.path.dirname(__file__), "data", "keyword_directory.json"))
    
    print(f"Initializing keyword directory from context files in {context_dir}")
    print(f"Saving to {directory_path}")
    
    # Update the keyword directory
    directory = update_keyword_directory(context_dir, directory_path)
    
    # Print some stats
    print(f"Extracted {len(directory.get('keywords', []))} keywords from context files")
    
    # Print top keywords
    from src.utils.context_keyword_manager import get_top_keywords
    top_keywords = get_top_keywords(directory, count=10)
    print(f"Top 10 keywords: {', '.join(top_keywords)}")
    
    print("Keyword directory initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
