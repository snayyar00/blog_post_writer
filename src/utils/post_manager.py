"""
Functions for managing blog post saving and updating.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from src.utils.logging_manager import log_info, log_error, log_debug

def save_post(post_data: Dict[str, Any], posts_dir: Path, markdown_dir: Path) -> str:
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
    file_path = posts_dir / filename
    
    log_debug(f"Saving post with ID: {post_data['id']}", "CONTENT")
    
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
                        # Test if it's JSON serializable
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
        log_info(f"Successfully saved post to {file_path}", "CONTENT")
    except Exception as e:
        log_error(f"Error saving post: {str(e)}", "CONTENT")
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
            log_info("Saved minimal version of post data", "CONTENT")
        except Exception as fallback_error:
            log_error(f"Error in fallback save: {str(fallback_error)}", "CONTENT")
    
    # Also save as markdown file
    markdown_filename = f"{topic_slug}_{post_data['id'][:8]}.md"
    markdown_path = markdown_dir / markdown_filename
    
    log_debug(f"Creating markdown version at {markdown_path}", "CONTENT")
    
    # Create markdown content with title and content
    title = post_data.get('title', 'Blog Post')
    markdown_content = f"# {title}\n\n"
    
    # Add TLDR section if not already present
    content = post_data.get("content", "")
    if "## TLDR" not in content and "## TL;DR" not in content and "## In a Nutshell" not in content:
        # Generate a TLDR based on title
        tldr = f"Learn everything you need to know about {title.lower()}. This comprehensive guide covers key concepts, practical implementation tips, and important considerations to help you understand and apply {post_data.get('topic', 'this subject')} effectively."
        markdown_content += f"## TL;DR\n{tldr}\n\n"
    
    # Add the rest of the content
    markdown_content += content
    
    # Save markdown file
    try:
        with open(markdown_path, "w") as f:
            f.write(markdown_content)
        log_info(f"Successfully saved markdown version to {markdown_path}", "CONTENT")
    except Exception as e:
        log_error(f"Error saving markdown file: {str(e)}", "CONTENT")
    
    return str(file_path)

def update_post(post_id: str, updated_data: Dict[str, Any], posts_dir: Path, markdown_dir: Path) -> bool:
    """Update an existing post with new data."""
    log_debug(f"Attempting to update post with ID: {post_id}", "CONTENT")
    
    # Find the post file
    for file_path in posts_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                post_data = json.load(f)
                if post_data.get("id") == post_id:
                    # Update the data
                    post_data.update(updated_data)
                    
                    # Add last_modified timestamp
                    post_data["last_modified"] = datetime.now().timestamp()
                    
                    # Save back to file
                    with open(file_path, "w") as f:
                        json.dump(post_data, f, indent=2)
                    log_info(f"Updated post data in {file_path}", "CONTENT")
                    
                    # Also update markdown file if content was updated
                    if "content" in updated_data:
                        topic_slug = post_data.get("topic", "post").replace(" ", "_").lower()
                        markdown_filename = f"{topic_slug}_{post_data['id'][:8]}.md"
                        markdown_path = markdown_dir / markdown_filename
                        
                        # Create markdown content with title and content
                        title = post_data.get('title', 'Blog Post')
                        markdown_content = f"# {title}\n\n"
                        
                        # Add TLDR section if not already present
                        content = post_data.get("content", "")
                        if "## TLDR" not in content and "## TL;DR" not in content and "## In a Nutshell" not in content:
                            # Generate a TLDR based on title
                            tldr = f"Learn everything you need to know about {title.lower()}. This comprehensive guide covers key concepts, practical implementation tips, and important considerations to help you understand and apply {post_data.get('topic', 'this subject')} effectively."
                            markdown_content += f"## TL;DR\n{tldr}\n\n"
                        
                        # Add the rest of the content
                        markdown_content += content
                        
                        with open(markdown_path, "w") as f:
                            f.write(markdown_content)
                        log_info(f"Updated markdown version in {markdown_path}", "CONTENT")
                    
                    return True
        except Exception as e:
            log_error(f"Error updating post {file_path}: {e}", "CONTENT")
    
    log_error(f"Post with ID {post_id} not found", "CONTENT")
    return False
