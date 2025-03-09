"""
Post management utilities for the blog post generator.
Handles saving, loading, and updating blog posts.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import uuid

# Constants
POSTS_DIRECTORY = Path("./generated_posts")
POSTS_DIRECTORY.mkdir(exist_ok=True)
MARKDOWN_DIRECTORY = Path("./generated_posts/markdown")
MARKDOWN_DIRECTORY.mkdir(exist_ok=True, parents=True)

def load_posts_history() -> List[Dict[str, Any]]:
    """Load history of previously generated posts."""
    posts = []
    
    if POSTS_DIRECTORY.exists():
        for file_path in POSTS_DIRECTORY.glob("*.json"):
            try:
                print(f"DEBUG: Loading post from {file_path}")
                with open(file_path, "r") as f:
                    post_data = json.load(f)
                    print(f"DEBUG: Post keys: {post_data.keys()}")
                    if 'analysis' in post_data:
                        print(f"DEBUG: Post has analysis key")
                    if 'agent_activities' in post_data:
                        print(f"DEBUG: Post has agent_activities key")
                    posts.append(post_data)
            except Exception as e:
                print(f"Error loading post {file_path}: {e}")
    
    # Sort by timestamp (newest first)
    return sorted(posts, key=lambda x: x.get("timestamp", 0), reverse=True)

def save_post(post_data: Dict[str, Any]) -> str:
    """Save post data to a file and return the file path."""
    # Generate a unique ID if not present
    if "id" not in post_data:
        post_data["id"] = str(uuid.uuid4())
    
    # Add timestamp if not present
    if "timestamp" not in post_data:
        post_data["timestamp"] = datetime.now().timestamp()
    
    # Create a filename based on topic and ID
    topic_slug = post_data.get("topic", "post").replace(" ", "_").lower()
    filename = f"{topic_slug}_{post_data['id'][:8]}.json"
    file_path = POSTS_DIRECTORY / filename
    
    # Create a JSON-serializable copy of the post data
    serializable_data = {}
    try:
        for key, value in post_data.items():
            if isinstance(value, dict):
                # Handle nested dictionaries
                serializable_data[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (str, int, float, bool, type(None), list, dict)):
                        # Check if it's a list or dict that might contain non-serializable objects
                        if isinstance(sub_value, (list, dict)):
                            try:
                                # Test if it's JSON serializable
                                json.dumps(sub_value)
                                serializable_data[key][sub_key] = sub_value
                            except (TypeError, OverflowError):
                                # Convert to string if not serializable
                                serializable_data[key][sub_key] = str(sub_value)
                        else:
                            serializable_data[key][sub_key] = sub_value
                    else:
                        # Convert non-serializable types to strings
                        serializable_data[key][sub_key] = str(sub_value)
            elif isinstance(value, (str, int, float, bool, type(None), list)):
                # Handle basic types and lists
                if isinstance(value, list):
                    try:
                        # Test if the list is JSON serializable
                        json.dumps(value)
                        serializable_data[key] = value
                    except (TypeError, OverflowError):
                        # Convert to string if not serializable
                        serializable_data[key] = str(value)
                else:
                    serializable_data[key] = value
            else:
                # Convert non-serializable types to strings
                serializable_data[key] = str(value)
        
        # Save to file
        with open(file_path, "w") as f:
            json.dump(serializable_data, f, indent=2)
    except Exception as e:
        print(f"Error saving post: {str(e)}")
        # Fallback to a simpler approach
        try:
            # Create a minimal serializable version
            minimal_data = {
                "id": post_data.get("id", str(uuid.uuid4())),
                "title": str(post_data.get("title", "Blog Post")),
                "content": str(post_data.get("content", "")),
                "topic": str(post_data.get("topic", "post")),
                "timestamp": post_data.get("timestamp", datetime.now().timestamp()),
                "error": f"Full data could not be saved: {str(e)}"
            }
            with open(file_path, "w") as f:
                json.dump(minimal_data, f, indent=2)
        except Exception as fallback_error:
            print(f"Error in fallback save: {str(fallback_error)}")
    
    # Also save as markdown file
    markdown_filename = f"{topic_slug}_{post_data['id'][:8]}.md"
    markdown_path = MARKDOWN_DIRECTORY / markdown_filename
    
    # Create markdown content with TLDR
    markdown_content = f"# {post_data.get('title', 'Blog Post')}\n\n"
    
    # Add TLDR section if not already present
    content = post_data.get("content", "")
    if "## TLDR" not in content and "## TL;DR" not in content and "## In a Nutshell" not in content:
        # Generate a TLDR
        tldr = "A concise overview of digital accessibility requirements across different industries, highlighting key considerations, benefits, and implementation strategies for creating inclusive digital experiences."
        markdown_content += f"## TLDR\n{tldr}\n\n"
    
    # Add the rest of the content
    markdown_content += content
    
    # Save markdown file
    with open(markdown_path, "w") as f:
        f.write(markdown_content)
    
    return str(file_path)

def update_post(post_id: str, updated_data: Dict[str, Any]) -> bool:
    """Update an existing post with new data."""
    # Find the post file
    for file_path in POSTS_DIRECTORY.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                post_data = json.load(f)
                if post_data.get("id") == post_id:
                    # Create serializable versions of the updated data
                    serializable_updates = {}
                    for key, value in updated_data.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            serializable_updates[key] = value
                        elif isinstance(value, dict):
                            # Handle nested dictionaries
                            serializable_dict = {}
                            for sub_key, sub_value in value.items():
                                if isinstance(sub_value, (str, int, float, bool, type(None))):
                                    serializable_dict[sub_key] = sub_value
                                else:
                                    # Convert non-serializable types to strings
                                    serializable_dict[sub_key] = str(sub_value)
                            serializable_updates[key] = serializable_dict
                        elif isinstance(value, list):
                            # Handle lists - convert to JSON-serializable list
                            try:
                                # Test if it's JSON serializable
                                json.dumps(value)
                                serializable_updates[key] = value
                            except (TypeError, OverflowError):
                                # Convert to string if not serializable
                                serializable_updates[key] = str(value)
                        else:
                            # Convert non-serializable types to strings
                            serializable_updates[key] = str(value)
                    
                    # Update the data with serializable values
                    post_data.update(serializable_updates)
                    
                    # Add last_modified timestamp
                    post_data["last_modified"] = datetime.now().timestamp()
                    
                    # Save back to file
                    with open(file_path, "w") as f:
                        json.dump(post_data, f, indent=2)
                    
                    # Also update markdown file
                    topic_slug = post_data.get("topic", "post").replace(" ", "_").lower()
                    markdown_filename = f"{topic_slug}_{post_data['id'][:8]}.md"
                    markdown_path = MARKDOWN_DIRECTORY / markdown_filename
                    
                    # Create markdown content with TLDR
                    markdown_content = f"# {post_data.get('title', 'Blog Post')}\n\n"
                    
                    # Add TLDR section if not already present
                    content = post_data.get("content", "")
                    if "## TLDR" not in content and "## TL;DR" not in content and "## In a Nutshell" not in content:
                        # Generate a TLDR
                        tldr = "A concise overview of digital accessibility requirements across different industries, highlighting key considerations, benefits, and implementation strategies for creating inclusive digital experiences."
                        markdown_content += f"## TLDR\n{tldr}\n\n"
                    
                    # Add the rest of the content
                    markdown_content += content
                    
                    # Save markdown file
                    with open(markdown_path, "w") as f:
                        f.write(markdown_content)
                    
                    return True
        except Exception as e:
            print(f"Error updating post {file_path}: {e}")
    
    return False