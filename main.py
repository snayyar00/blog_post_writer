import os
import csv
import json
import pandas as pd
from typing import Dict, List, Any
from dotenv import load_dotenv
from pathlib import Path
from src.agents.keyword_functions import generate_keywords
from src.agents.research_agent import ResearchAgent
from src.agents.content_functions import humanize_content
from src.agents.memoripy_manager import ResearchMemoryManager

def load_context_files(context_dir: str = "context") -> Dict[str, str]:
    """Load and process context files from the context directory.
    
    Args:
        context_dir: Directory containing context files
        
    Returns:
        Dictionary mapping filenames to their contents
    """
    context_data = {}
    context_path = Path(context_dir)
    
    if not context_path.exists():
        raise FileNotFoundError(f"Context directory {context_dir} not found")
    
    # Process markdown files
    for file_path in context_path.glob("*.md"):
        try:
            context_data[file_path.name] = file_path.read_text()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    # Process CSV files
    for file_path in context_path.glob("*.csv"):
        try:
            df = pd.read_csv(file_path)
            # Convert DataFrame to string representation
            context_data[file_path.name] = df.to_string(index=False)
        except Exception as e:
            print(f"Error reading CSV {file_path}: {e}")
            continue
    
    # Process Excel files
    for file_path in context_path.glob("*.xlsx"):
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheet_data = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_data.append(f"Sheet: {sheet_name}\n{df.to_string(index=False)}")
            
            context_data[file_path.name] = "\n\n".join(sheet_data)
        except Exception as e:
            print(f"Error reading Excel {file_path}: {e}")
            continue
            
    print(f"Loaded {len(context_data)} context files from {context_dir}")
    return context_data

def process_topic(topic: str, context_data: Dict[str, str]) -> str:
    """Process a topic through the agent pipeline.
    
    Args:
        topic: Topic to generate content for
        context_data: Dictionary of context data
        
    Returns:
        Generated blog post content
    """
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
        
    # Initialize memory manager and research agent
    memory_manager = ResearchMemoryManager(api_key)
    research_agent = ResearchAgent(api_key=api_key)
    
    # Step 1: Generate keywords
    print(f"Generating keywords for topic: {topic}")
    keywords = generate_keywords(topic, context_data)
    print(f"Generated keywords: {keywords}")
    
    # Step 2: Research the topic
    print(f"Researching keywords: {', '.join(keywords[:3])}...")
    try:
        research_results = research_agent.research_topic(', '.join(keywords[:5]))
        print(f"Research completed with {len(research_results)} findings")
    except Exception as e:
        print(f"Error during research: {str(e)}")
        research_results = [{"content": f"Error researching {topic}: {str(e)}", "sources": [], "confidence": 0}]
    
    # Step 3: Store research results in memory
    research_data = {
        "topic": topic,
        "keywords": keywords,
        "research": research_results,
        "context_used": list(context_data.keys())
    }
    
    # Store in memory using Memoripy
    memory_manager.store_research_results(research_data, topic)
    
    # Step 4: Humanize the content
    brand_voice = "professional yet conversational"  # Default if not in context
    target_audience = "business professionals"  # Default if not in context
    
    # Try to extract brand voice and target audience from context if available
    for key, value in context_data.items():
        if "brand" in key.lower() or "voice" in key.lower() or "tone" in key.lower():
            brand_voice = value[:100]  # Use first 100 chars as brand voice
        if "audience" in key.lower() or "target" in key.lower():
            target_audience = value[:100]  # Use first 100 chars as target audience
    
    # Extract the actual research content
    research_content = "\n\n".join([item.get("content", "") for item in research_results])
    
    # Humanize the content
    print(f"Humanizing content with brand voice: {brand_voice[:20]}...")
    content = humanize_content(research_content, brand_voice, target_audience)
    
    return content

def main():
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    try:
        # Load context data
        context_data = load_context_files()
        
        # Example topic
        topic = "web accessibility best practices"
        
        # Process topic and generate content
        final_content = process_topic(topic, context_data)
        
        print("Generated content:", final_content)
        
    except Exception as e:
        print(f"Error processing topic: {e}")
        raise

if __name__ == "__main__":
    main()
