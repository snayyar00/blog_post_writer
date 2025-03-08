"""
Enhanced keyword extraction script that analyzes all context files
and extracts a comprehensive set of keywords with metadata.
"""
import asyncio
import os
import re
import json
import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Set, Tuple
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Download required NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Initialize NLTK components
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def load_all_context_files(context_dir: Path) -> Dict[str, str]:
    """
    Load all context files from the context directory.
    
    Args:
        context_dir: Path to the context directory
        
    Returns:
        Dictionary mapping filenames to file contents
    """
    if not context_dir.exists():
        print(f"Context directory {context_dir} does not exist")
        return {}
    
    context_data = {}
    
    # Load all files in the context directory
    for file_path in context_dir.glob("**/*"):
        if file_path.is_file():
            try:
                if file_path.suffix in ['.md', '.txt']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    context_data[str(file_path.relative_to(context_dir))] = content
                elif file_path.suffix == '.csv':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    context_data[str(file_path.relative_to(context_dir))] = content
                elif file_path.suffix == '.json':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    context_data[str(file_path.relative_to(context_dir))] = json.dumps(content)
            except Exception as e:
                print(f"Error loading context file {file_path}: {e}")
    
    print(f"Loaded {len(context_data)} context files")
    return context_data

def extract_ngrams(text: str, n: int = 2) -> List[str]:
    """
    Extract n-grams from text.
    
    Args:
        text: Input text
        n: n-gram size
        
    Returns:
        List of n-grams
    """
    tokens = word_tokenize(text.lower())
    # Filter out stopwords and non-alphabetic tokens
    filtered_tokens = [token for token in tokens if token.isalpha() and token not in stop_words]
    
    # Generate n-grams
    ngrams = []
    for i in range(len(filtered_tokens) - n + 1):
        ngram = ' '.join(filtered_tokens[i:i+n])
        if len(ngram) > 3:  # Skip very short n-grams
            ngrams.append(ngram)
    
    return ngrams

def extract_keywords_from_markdown(content: str) -> List[Tuple[str, str]]:
    """
    Extract keywords from markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        List of (keyword, category) tuples
    """
    keywords = []
    
    # Extract headings
    headings = re.findall(r'#+\s+(.*?)(?:\n|$)', content)
    for heading in headings:
        # Extract potential keywords from headings
        heading_keywords = extract_ngrams(heading, 2)
        for kw in heading_keywords:
            keywords.append((kw, "heading"))
    
    # Extract bold text
    bold_text = re.findall(r'\*\*(.*?)\*\*', content)
    for text in bold_text:
        if 3 <= len(text) <= 50 and not text.startswith("http"):
            keywords.append((text.lower(), "emphasis"))
    
    # Extract bullet points
    bullet_points = re.findall(r'[-*]\s+(.*?)(?:\n|$)', content)
    for point in bullet_points:
        # Extract potential keywords from bullet points
        point_keywords = extract_ngrams(point, 2)
        for kw in point_keywords:
            keywords.append((kw, "bullet_point"))
    
    # Extract from paragraphs
    paragraphs = re.split(r'\n\n+', content)
    for paragraph in paragraphs:
        if len(paragraph) > 100:  # Only process substantial paragraphs
            # Extract potential keywords from paragraphs
            paragraph_keywords = extract_ngrams(paragraph, 2) + extract_ngrams(paragraph, 3)
            for kw in paragraph_keywords:
                keywords.append((kw, "paragraph"))
    
    return keywords

def extract_keywords_from_csv(content: str) -> List[Tuple[str, str]]:
    """
    Extract keywords from CSV content.
    
    Args:
        content: CSV content
        
    Returns:
        List of (keyword, category) tuples
    """
    keywords = []
    
    try:
        lines = content.strip().split('\n')
        reader = csv.reader(lines)
        
        # Skip header
        next(reader, None)
        
        for row in reader:
            if len(row) >= 3:
                # Assume the third column contains keywords
                keyword = row[2].strip().lower()
                if keyword and len(keyword) > 3:
                    keywords.append((keyword, "csv_data"))
                
                # Check for additional columns that might contain relevant data
                for col in row:
                    if col and len(col) > 3:
                        ngrams = extract_ngrams(col, 2)
                        for ngram in ngrams:
                            keywords.append((ngram, "csv_data"))
    except Exception as e:
        print(f"Error processing CSV content: {e}")
    
    return keywords

def extract_keywords_from_json(content: str) -> List[Tuple[str, str]]:
    """
    Extract keywords from JSON content.
    
    Args:
        content: JSON content
        
    Returns:
        List of (keyword, category) tuples
    """
    keywords = []
    
    try:
        data = json.loads(content)
        
        # Process JSON data based on structure
        if isinstance(data, dict):
            # Extract from values
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 3:
                    ngrams = extract_ngrams(value, 2)
                    for ngram in ngrams:
                        keywords.append((ngram, "json_data"))
        elif isinstance(data, list):
            # Extract from list items
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str) and len(value) > 3:
                            ngrams = extract_ngrams(value, 2)
                            for ngram in ngrams:
                                keywords.append((ngram, "json_data"))
    except Exception as e:
        print(f"Error processing JSON content: {e}")
    
    return keywords

def extract_keywords_from_all_files(context_data: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Extract keywords from all context files.
    
    Args:
        context_data: Dictionary mapping filenames to file contents
        
    Returns:
        List of keyword dictionaries with metadata
    """
    all_keywords = []
    
    for filename, content in context_data.items():
        file_keywords = []
        
        # Process based on file type
        if filename.endswith('.md') or filename.endswith('.txt'):
            file_keywords = extract_keywords_from_markdown(content)
        elif filename.endswith('.csv'):
            file_keywords = extract_keywords_from_csv(content)
        elif filename.endswith('.json'):
            file_keywords = extract_keywords_from_json(content)
        
        # Add source information
        for keyword, category in file_keywords:
            all_keywords.append({
                "keyword": keyword,
                "source": filename,
                "category": category
            })
    
    return all_keywords

def filter_and_rank_keywords(keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter and rank keywords based on frequency and other metrics.
    
    Args:
        keywords: List of keyword dictionaries
        
    Returns:
        Filtered and ranked list of keyword dictionaries
    """
    # Count keyword frequency
    keyword_counter = Counter([kw["keyword"] for kw in keywords])
    
    # Create a set of seen keywords to avoid duplicates
    seen_keywords = set()
    filtered_keywords = []
    
    # Filter out common words and duplicates
    for kw_data in keywords:
        keyword = kw_data["keyword"]
        
        # Skip common words and very short keywords
        if (keyword in stop_words or len(keyword) < 4 or 
            any(common in keyword for common in ["http", "www", "the", "and", "for", "with"])):
            continue
        
        if keyword not in seen_keywords:
            # Add frequency information
            frequency = keyword_counter[keyword]
            
            # Determine priority based on frequency and category
            priority = "low"
            if frequency > 3:
                priority = "high"
            elif frequency > 1:
                priority = "medium"
            
            # Boost priority for keywords from headings or emphasis
            if kw_data["category"] in ["heading", "emphasis"]:
                if priority == "low":
                    priority = "medium"
                elif priority == "medium":
                    priority = "high"
            
            filtered_keywords.append({
                "keyword": keyword,
                "source": kw_data["source"],
                "frequency": frequency,
                "priority": priority,
                "category": kw_data["category"]
            })
            seen_keywords.add(keyword)
    
    # Sort by priority and frequency
    sorted_keywords = sorted(filtered_keywords, key=lambda x: (
        0 if x["priority"] == "high" else 1 if x["priority"] == "medium" else 2,
        -x["frequency"]
    ))
    
    return sorted_keywords

def save_keyword_directory(keywords: List[Dict[str, Any]], directory_path: Path) -> None:
    """
    Save the keyword directory to a JSON file.
    
    Args:
        keywords: List of keyword dictionaries
        directory_path: Path to save the keyword directory file
    """
    # Create directory structure
    directory_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create directory data
    directory_data = {
        "keywords": keywords,
        "total_keywords": len(keywords),
        "high_priority_keywords": len([kw for kw in keywords if kw["priority"] == "high"]),
        "medium_priority_keywords": len([kw for kw in keywords if kw["priority"] == "medium"]),
        "low_priority_keywords": len([kw for kw in keywords if kw["priority"] == "low"]),
        "categories": list(set(kw["category"] for kw in keywords)),
        "sources": list(set(kw["source"] for kw in keywords))
    }
    
    # Save to file
    try:
        with open(directory_path, 'w', encoding='utf-8') as f:
            json.dump(directory_data, f, indent=2)
        print(f"Saved keyword directory to {directory_path}")
    except Exception as e:
        print(f"Error saving keyword directory: {e}")

async def main():
    # Define paths
    context_dir = Path(os.path.join(os.path.dirname(__file__), "context"))
    directory_path = Path(os.path.join(os.path.dirname(__file__), "data", "enhanced_keyword_directory.json"))
    
    print(f"Extracting enhanced keywords from context files in {context_dir}")
    
    # Load all context files
    context_data = load_all_context_files(context_dir)
    
    # Extract keywords from all files
    all_keywords = extract_keywords_from_all_files(context_data)
    print(f"Extracted {len(all_keywords)} raw keywords from context files")
    
    # Filter and rank keywords
    filtered_keywords = filter_and_rank_keywords(all_keywords)
    print(f"Filtered to {len(filtered_keywords)} unique keywords")
    
    # Save keyword directory
    save_keyword_directory(filtered_keywords, directory_path)
    
    # Print top keywords
    top_keywords = [kw["keyword"] for kw in filtered_keywords[:20]]
    print(f"Top 20 keywords: {', '.join(top_keywords)}")
    
    # Print keyword statistics
    high_priority = len([kw for kw in filtered_keywords if kw["priority"] == "high"])
    medium_priority = len([kw for kw in filtered_keywords if kw["priority"] == "medium"])
    low_priority = len([kw for kw in filtered_keywords if kw["priority"] == "low"])
    
    print(f"Keyword statistics:")
    print(f"- High priority: {high_priority}")
    print(f"- Medium priority: {medium_priority}")
    print(f"- Low priority: {low_priority}")
    
    print("Enhanced keyword extraction completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
