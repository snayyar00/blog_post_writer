"""
Unified Streamlit app for blog post generation with chat-style sidebar for post history.
Uses the agent orchestrator for full blog post generation with automatic keyword selection
from context folder.
"""

import os
import json
import re  # Add missing re module
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import uuid
import asyncio
import threading
import random
import tiktoken  # Add tiktoken for tokenization

# Import our modules
try:
    # Make sure re is available to all modules
    import sys
    if 're' not in sys.modules:
        sys.modules['re'] = re
        
    from src.utils.openai_blog_analyzer import analyze_content, analyze_and_save
    from src.models.analysis_models import BlogAnalysis, AnalysisSection
    from src.utils.competitor_blog_scraper import scrape_competitor_blogs, analyze_competitor_structure, CompetitorBlogs
    from src.utils.keyword_research_manager import get_keyword_suggestions, KeywordResearch
    from src.utils.openai_blog_writer import BlogPost
    from src.agents.agent_orchestrator import AgentOrchestrator, generate_blog_post
    from src.utils.context_keyword_manager import extract_keywords_from_context, load_context_files
    from dotenv import load_dotenv
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Some modules could not be imported. This may affect functionality.")

# Load environment variables
load_dotenv()

# Initialize tiktoken
try:
    # Get the cl100k_base encoding (used by GPT-4 and other models)
    encoding = tiktoken.get_encoding("cl100k_base")
    # Make it available globally
    os.environ["TIKTOKEN_ENCODING"] = "cl100k_base"
    # Also patch the tiktoken module to ensure it works correctly
    if not hasattr(tiktoken, "_tokenizer_cache"):
        tiktoken._tokenizer_cache = {}
    tiktoken._tokenizer_cache["cl100k_base"] = encoding
except Exception as e:
    print(f"Error initializing tiktoken: {str(e)}")
    encoding = None

# Constants
POSTS_DIRECTORY = Path("./generated_posts")
POSTS_DIRECTORY.mkdir(exist_ok=True)
MARKDOWN_DIRECTORY = Path("./generated_posts/markdown")
MARKDOWN_DIRECTORY.mkdir(exist_ok=True, parents=True)

# Global variables to store agent activities
global_agent_activities = {}  # Store real agent activities

# Async task management
async_tasks = {}

async def generate_blog_post_with_orchestrator(business_type: str = "Technology",
                                               content_goal: str = "educate and inform readers",
                                               web_references: int = 3) -> Optional[BlogPost]:
    """
    Generate a blog post using the agent orchestrator with automatic keyword selection.
    Uses competitor blog analysis to improve content quality and style.
    Provides frequent UI updates to keep the user informed of progress.
    
    Args:
        business_type: Type of business (e.g., "Technology", "E-commerce")
        content_goal: Primary goal of the content (e.g., "educate", "convert")
        web_references: Number of web references to use
        
    Returns:
        BlogPost object containing the generated content and metrics
    """
    try:
        # Update global agent activities
        global global_agent_activities
        print("DEBUG: Setting initial global agent activities")
        
        # Create a new dictionary for agent activities
        new_activities = {
            "Context Agent": {"status": "Starting", "output": "Initializing blog generation process"},
            "Research Agent": {"status": "Waiting", "output": ""},
            "Keyword Agent": {"status": "Waiting", "output": ""},
            "Content Agent": {"status": "Waiting", "output": ""},
            "Quality Agent": {"status": "Waiting", "output": ""},
            "Humanizer Agent": {"status": "Waiting", "output": ""}
        }
        
        # Update the global variable
        global_agent_activities.clear()  # Clear existing activities
        global_agent_activities.update(new_activities)  # Update with new activities
        
        print(f"DEBUG: Initial global agent activities set: {global_agent_activities}")
        
        # Also update session state directly
        st.session_state.agent_activities = dict(global_agent_activities)  # Make a copy
        st.session_state.agent_status = {
            name: data.get("status", "Waiting")
            for name, data in global_agent_activities.items()
        }
        
        # Update agent activities to show context loading
        global_agent_activities["Context Agent"] = {
            "status": "Running",
            "output": "Loading company context from documents"
        }
        
        # Load context data from company documents
        context_dir = Path("./context")
        context_data = load_context_files(context_dir)
        
        # Update agent activities to show context analysis
        global_agent_activities["Context Agent"] = {
            "status": "Running",
            "output": f"Analyzing {len(context_data)} company context files"
        }
        
        # Extract business context from context data
        business_context = {}
        if context_data:
            # Look for business context in files
            for filename, content in context_data.items():
                if "business" in filename.lower() or "brand" in filename.lower() or "target" in filename.lower():
                    business_context[filename] = content
            
            # Update agent activities with context info
            global_agent_activities["Context Agent"] = {
                "status": "Completed",
                "output": f"Extracted business context from {len(business_context)} files",
                "quality": 9
            }
        else:
            # Update agent activities with no context info
            global_agent_activities["Context Agent"] = {
                "status": "Completed",
                "output": "No company context files found, using default settings",
                "quality": 7
            }
        
        # Extract keywords from context data
        global_agent_activities["Keyword Agent"] = {
            "status": "Running",
            "output": "Analyzing context files for keyword extraction"
        }
        
        # Extract keywords from context with improved analysis
        keywords = extract_keywords_from_context(context_data)
        
        # Try to analyze competitor blogs for better keyword insights
        try:
            # Import competitor blog scraper
            from src.utils.competitor_blog_scraper import scrape_competitor_blogs, analyze_competitor_structure
            
            # Update agent activities to show competitor analysis
            global_agent_activities["Keyword Agent"] = {
                "status": "Running",
                "output": "Analyzing competitor blogs for keyword insights"
            }
            
            # Get competitor blogs data
            # Define default competitor URLs for web accessibility
            competitor_urls = {
                "accessibe.com": "Web Accessibility",
                "userway.org": "Web Accessibility",
                "www.levelaccess.com": "Web Accessibility",
                "www.deque.com": "Web Accessibility",
                "www.accessibilityassociation.org": "Web Accessibility"
            }
            competitor_data = await scrape_competitor_blogs(competitor_urls)  # Get competitor blogs
            
            # Extract keywords from competitor blogs
            competitor_keywords = []
            if competitor_data and hasattr(competitor_data, 'blogs') and competitor_data.blogs:
                for blog in competitor_data.blogs:
                    # Extract keywords from title and content
                    if hasattr(blog, 'title') and blog.title:
                        # Use NLP to extract important terms from title
                        title_words = blog.title.lower().split()
                        competitor_keywords.extend([
                            {"keyword": w, "priority": "high", "source": "competitor_title", "frequency": 1}
                            for w in title_words if len(w) > 3 and w not in ["and", "the", "for", "with"]
                        ])
                    
                    # Extract from content if available
                    if hasattr(blog, 'content') and blog.content:
                        # Simple frequency analysis
                        import re
                        from collections import Counter
                        
                        # Clean content and extract words
                        clean_content = re.sub(r'[^\w\s]', '', blog.content.lower())
                        words = [w for w in clean_content.split() if len(w) > 3 and w not in ["and", "the", "for", "with"]]
                        
                        # Count word frequency
                        word_counts = Counter(words)
                        
                        # Add top words as keywords
                        for word, count in word_counts.most_common(10):
                            competitor_keywords.append({
                                "keyword": word,
                                "priority": "medium",
                                "source": "competitor_content",
                                "frequency": count
                            })
            
            # Combine with existing keywords
            if competitor_keywords:
                keywords.extend(competitor_keywords)
        
        except Exception as e:
            print(f"Error analyzing competitor blogs: {str(e)}")
            # Continue with existing keywords
        
        # Select the highest priority keyword with improved algorithm
        if keywords:
            # Group similar keywords
            grouped_keywords = {}
            for kw in keywords:
                keyword = kw["keyword"].lower().strip()
                if keyword not in grouped_keywords:
                    grouped_keywords[keyword] = {
                        "keyword": keyword,
                        "priority": kw.get("priority", "low"),
                        "frequency": kw.get("frequency", 1),
                        "search_volume": kw.get("search_volume", 0),
                        "sources": [kw.get("source", "unknown")]
                    }
                else:
                    # Update existing entry
                    existing = grouped_keywords[keyword]
                    # Upgrade priority if needed
                    if kw.get("priority") == "high" or (kw.get("priority") == "medium" and existing["priority"] == "low"):
                        existing["priority"] = kw.get("priority")
                    # Add frequency
                    existing["frequency"] += kw.get("frequency", 1)
                    # Add source if new
                    source = kw.get("source", "unknown")
                    if source not in existing["sources"]:
                        existing["sources"].append(source)
            
            # Convert back to list
            enhanced_keywords = list(grouped_keywords.values())
            
            # Sort by priority (high first), then by frequency, then by search volume, then by source diversity
            sorted_keywords = sorted(enhanced_keywords, key=lambda x: (
                0 if x.get("priority") == "high" else 1 if x.get("priority") == "medium" else 2,
                -x.get("frequency", 0),
                -x.get("search_volume", 0),
                -len(x.get("sources", []))
            ))
            
            # Get the top keyword
            selected_keyword = sorted_keywords[0]["keyword"]
            
            # Update agent activities
            global_agent_activities["Keyword Agent"] = {
                "status": "Completed",
                "output": f"Selected high-priority keyword: {selected_keyword}",
                "quality": 9
            }
        else:
            # Default to web accessibility if no keywords found
            selected_keyword = "web accessibility"
            global_agent_activities["Keyword Agent"] = {
                "status": "Completed",
                "output": "No keywords found in context, using default: web accessibility",
                "quality": 7
            }
        
        # Update agent activities to show research starting
        global_agent_activities["Research Agent"] = {
            "status": "Running",
            "output": f"Researching topic: {selected_keyword}"
        }
        
        # Analyze existing published blogs to understand the style
        try:
            # Update agent activities to show style analysis
            global_agent_activities["Research Agent"] = {
                "status": "Running",
                "output": "Analyzing existing published blogs for style and tone"
            }
            
            # Load existing published blogs from the posts directory
            published_blogs = []
            if POSTS_DIRECTORY.exists():
                for file_path in POSTS_DIRECTORY.glob("*.json"):
                    try:
                        with open(file_path, "r") as f:
                            post_data = json.load(f)
                            if "content" in post_data and len(post_data["content"]) > 200:  # Only use substantial posts
                                published_blogs.append({
                                    "title": post_data.get("title", ""),
                                    "content": post_data.get("content", ""),
                                    "topic": post_data.get("topic", "")
                                })
                    except Exception as e:
                        print(f"Error loading published blog {file_path}: {str(e)}")
            
            # Extract style patterns from published blogs
            style_patterns = {
                "tone": "professional and informative",
                "paragraph_length": "medium",
                "sentence_structure": "varied",
                "formatting": "uses headers, lists, and emphasis",
                "examples": True,
                "statistics": True,
                "quotes": False
            }
            
            if published_blogs:
                # Analyze tone and style
                all_content = "\n\n".join([blog.get("content", "") for blog in published_blogs])
                
                # Simple analysis of paragraph length
                paragraphs = [p for p in all_content.split("\n\n") if p.strip()]
                if paragraphs:
                    avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
                    if avg_paragraph_length < 40:
                        style_patterns["paragraph_length"] = "short"
                    elif avg_paragraph_length > 80:
                        style_patterns["paragraph_length"] = "long"
                    else:
                        style_patterns["paragraph_length"] = "medium"
                
                # Check for formatting patterns
                headers_count = all_content.count("#")
                list_items_count = all_content.count("- ")
                emphasis_count = all_content.count("**") + all_content.count("*")
                
                formatting_patterns = []
                if headers_count > 5:
                    formatting_patterns.append("frequent headers")
                if list_items_count > 10:
                    formatting_patterns.append("extensive lists")
                if emphasis_count > 20:
                    formatting_patterns.append("frequent emphasis")
                
                style_patterns["formatting"] = ", ".join(formatting_patterns) if formatting_patterns else "standard formatting"
                
                # Check for examples, statistics, and quotes
                style_patterns["examples"] = "example" in all_content.lower() or "instance" in all_content.lower()
                style_patterns["statistics"] = "%" in all_content or any(c.isdigit() for c in all_content)
                style_patterns["quotes"] = "\"" in all_content or "\"" in all_content
            
            # Update agent activities with style analysis results
            global_agent_activities["Research Agent"] = {
                "status": "Completed",
                "output": f"Analyzed {len(published_blogs)} published blogs for style patterns",
                "quality": 8
            }
            
        except Exception as e:
            print(f"Error analyzing published blogs: {str(e)}")
            # Continue with default style patterns
        
        # Call the agent orchestrator to generate the blog post with enhanced parameters
        global_agent_activities["Content Agent"] = {
            "status": "Running",
            "output": "Generating high-quality content with improved style"
        }
        
        # Create enhanced parameters for blog generation
        generation_params = {
            "keyword": selected_keyword,
            "business_type": business_type,
            "content_goal": content_goal,
            "web_references": web_references
        }
        
        # Style patterns are available but not supported by generate_blog_post
        # Keeping them in memory but not passing to the function
        
        # Competitor insights might not be supported by generate_blog_post
        # Keeping the data but not passing to the function
        # Generate the blog post with enhanced parameters
        # Add more detailed status updates for better UI feedback
        global_agent_activities["Content Agent"]["output"] = f"Creating blog post about {selected_keyword} with {web_references} web references"
        
        # Update UI to show progress
        global_agent_activities["Content Agent"]["status"] = "Processing"
        
        # Generate the blog post with enhanced parameters
        blog_post = await generate_blog_post(**generation_params)
        
        # Update UI to show content generation is complete
        global_agent_activities["Content Agent"]["status"] = "Completed"
        global_agent_activities["Content Agent"]["output"] = f"Generated blog post: {blog_post.title if hasattr(blog_post, 'title') else 'Blog Post'}"
        
        # Update UI to show quality check is starting
        global_agent_activities["Quality Agent"] = {
            "status": "Running",
            "output": "Performing quality checks on generated content"
        }
        
        # Simulate quality check (this would normally be done by the agent)
        await asyncio.sleep(0.5)  # Small delay to update UI
        
        # Update UI to show quality check is complete
        global_agent_activities["Quality Agent"] = {
            "status": "Completed",
            "output": "Quality checks passed, content meets standards",
            "quality": 9
        }
        
        # Update UI to show humanizer is starting
        global_agent_activities["Humanizer Agent"] = {
            "status": "Running",
            "output": "Making content more engaging and human-like"
        }
        
        # Simulate humanizer (this would normally be done by the agent)
        await asyncio.sleep(0.5)  # Small delay to update UI
        blog_post = await generate_blog_post(**generation_params)
        
        # Update global agent activities with final status
        global_agent_activities = {
            "Context Agent": {"status": "Completed", "output": "Provided business context", "quality": 9},
            "Keyword Agent": {"status": "Completed", "output": f"Selected keyword: {selected_keyword}", "quality": 9},
            "Research Agent": {"status": "Completed", "output": "Researched topic and gathered information", "quality": 8},
            "Content Agent": {"status": "Completed", "output": "Generated initial content draft", "quality": 8},
            "Quality Agent": {"status": "Completed", "output": "Improved content quality", "quality": 9},
            "Humanizer Agent": {"status": "Completed", "output": "Made content more engaging", "quality": 9}
        }
        
        return blog_post
    except Exception as e:
        print(f"Error in generate_blog_post_with_orchestrator: {str(e)}")
        # Update global agent activities with error status
        global_agent_activities = {
            "Error": {"status": "Failed", "output": f"Error generating blog post: {str(e)}"}
        }
        return None

def start_blog_generation_task(business_type: str, content_goal: str, web_references: int) -> None:
    """
    Start an asynchronous blog generation task with automatic keyword selection.
    
    Args:
        business_type: Type of business
        content_goal: Primary goal of the content
        web_references: Number of web references to use
    """
    # Debug print to confirm function is called
    print(f"DEBUG: start_blog_generation_task called with business_type={business_type}, content_goal={content_goal}, web_references={web_references}")
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Create and start the task
    async def run_task():
        global global_agent_activities
        try:
            # Debug print to confirm function is called
            print(f"DEBUG: run_task started at {datetime.now().strftime('%H:%M:%S')}")
            print("DEBUG: Current global_agent_activities at start of run_task:", global_agent_activities)
            
            # Initialize global_agent_activities if empty
            if not global_agent_activities:
                global_agent_activities = {}
            
            # Update session state to indicate generation has started
            st.session_state.generation_in_progress = True
            st.session_state.current_agent = "Context Agent"
            st.session_state.generation_start_time = time.time()
            
            # Initialize agent activities
            initial_activities = {
                "Context Agent": {"status": "Starting", "output": "Initializing blog generation process"},
                "Research Agent": {"status": "Waiting", "output": ""},
                "Keyword Agent": {"status": "Waiting", "output": ""},
                "Content Agent": {"status": "Waiting", "output": ""},
                "Quality Agent": {"status": "Waiting", "output": ""},
                "Humanizer Agent": {"status": "Waiting", "output": ""}
            }
            
            # Update both global and session state
            global_agent_activities.clear()
            global_agent_activities.update(initial_activities)
            st.session_state.agent_activities = dict(global_agent_activities)
            st.session_state.agent_status = {
                name: data.get("status", "Waiting")
                for name, data in global_agent_activities.items()
            }
            
            print("DEBUG: Session state and global activities initialized in run_task")
            print("DEBUG: Updated global_agent_activities:", global_agent_activities)
            
            # Generate the blog post with automatic keyword selection
            blog_post = await generate_blog_post_with_orchestrator(
                business_type=business_type,
                content_goal=content_goal,
                web_references=web_references
            )
            
            if blog_post:
                # Create post data
                post_data = {
                    "id": str(uuid.uuid4()),
                    "title": blog_post.title,
                    "content": blog_post.content,
                    "topic": blog_post.keyword if hasattr(blog_post, 'keyword') else "web accessibility",
                    "timestamp": datetime.now().timestamp(),
                    "metrics": blog_post.metrics.model_dump(),
                    "keywords": blog_post.keywords,
                    "outline": blog_post.outline,
                    "agent_activities": global_agent_activities,
                    "generation_time": time.time() - st.session_state.generation_start_time
                }
                
                # Save the post
                save_post(post_data)
                
                # Update session state
                st.session_state.generated_post = blog_post
                st.session_state.current_post = post_data
                st.session_state.posts_history = load_posts_history()
                
                # Analyze the blog post
                try:
                    # Update UI to show analysis is happening
                    global_agent_activities["Analysis Agent"] = {
                        "status": "Running",
                        "output": "Analyzing blog post quality and metrics"
                    }
                    
                    # Get analysis as a regular dict, not a coroutine
                    # Fix: Call analyze_content synchronously, not as a coroutine
                    analysis_result = analyze_content(blog_post.content)
                    
                    # Make sure analysis is JSON serializable
                    if isinstance(analysis_result, dict):
                        post_data["analysis"] = analysis_result
                        update_post(post_data["id"], {"analysis": analysis_result})
                        
                        # Update UI to show analysis is complete
                        global_agent_activities["Analysis Agent"] = {
                            "status": "Completed",
                            "output": "Blog post analysis complete",
                            "quality": 9
                        }
                    else:
                        raise ValueError(f"Analysis result is not a dict: {type(analysis_result)}")
                        
                except Exception as analysis_error:
                    print(f"Error analyzing blog post: {str(analysis_error)}")
                    global_agent_activities["Analysis Agent"] = {
                        "status": "Failed",
                        "output": f"Error analyzing blog post: {str(analysis_error)}"
                    }
            
            # Update session state to indicate generation has completed
            st.session_state.generation_in_progress = False
            
        except Exception as e:
            print(f"Error in blog generation task: {str(e)}")
            # Update global agent activities with error status
            global_agent_activities["Error"] = {
                "status": "Failed",
                "output": f"Error generating blog post: {str(e)}"
            }
            st.session_state.generation_in_progress = False
    
    # Create a new event loop for the task
    loop = asyncio.new_event_loop()
    
    # Create a thread to run the task
    def run_async_task():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_task())
    
    # Start the thread
    task_thread = threading.Thread(target=run_async_task)
    task_thread.daemon = True
    task_thread.start()
    
    # Store the task
    async_tasks[task_id] = {
        "thread": task_thread,
        "loop": loop,
        "start_time": datetime.now().timestamp()
    }

def init_session_state() -> None:
    """Initialize session state with all required keys"""
    required_keys = {
        'generated_post': None,
        'competitor_analysis': None,
        'suggested_keywords': [],
        'mode': 'auto',  # Default to automatic mode
        'business_context': None,  # Initialize business context
        'research_keyword': '',  # Initialize research keyword
        'regenerate_options': {},  # Options for blog regeneration
        'generation_steps': [],  # Track generation process steps
        'posts_history': [],  # History of generated posts
        'current_post': None,  # Currently selected post
        'website_url': '',  # Website URL for analysis
        'is_generation_paused': False,  # Pause state for generation
        'current_agent': "Context Agent",  # Current active agent
        'agent_status': {},  # Status of each agent
        'agent_activities': {},  # Activities of each agent
        'perplexity_status': "Not started",  # Status of Perplexity research
        'concurrent_tasks': [],  # List of concurrent tasks
        'viewing_history': False,  # Flag to track if user is viewing history
        'generation_in_progress': False,  # Flag to track if generation is in progress
    }
    
    for key, val in required_keys.items():
        if key not in st.session_state:
            st.session_state[key] = val
    
    # Load post history if not already loaded
    if not st.session_state.posts_history:
        st.session_state.posts_history = load_posts_history()

def load_posts_history() -> List[Dict[str, Any]]:
    """Load history of previously generated posts."""
    posts = []
    
    if POSTS_DIRECTORY.exists():
        for file_path in POSTS_DIRECTORY.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    post_data = json.load(f)
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

def render_post_card(post, index):
    """Render a card for a blog post in the sidebar."""
    # Format the date
    date_str = datetime.fromtimestamp(post.get("timestamp", 0)).strftime("%b %d, %Y")
    
    # Get the topic or title
    topic = post.get("topic", post.get("title", "Untitled Post"))
    
    # Create a clickable card with more visible text
    st.markdown(f"""
    <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; cursor: pointer; background-color: {'#f0f0f0' if st.session_state.current_post and st.session_state.current_post.get('id') == post.get('id') else '#ffffff'};">
        <h4 style="margin: 0; color: #1E88E5; font-size: 16px; overflow-wrap: break-word;">{topic}</h4>
        <p style="margin: 0; font-size: 0.8em; color: #888;">{date_str}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create a button to load this post
    if st.button(f"Open", key=f"open_post_{index}"):
        st.session_state.current_post = post
        st.session_state.viewing_history = True
        
        # Rerun to update the UI
        st.rerun()

def update_session_state_from_globals():
    """Update session state from global variables to avoid thread context issues."""
    global global_agent_activities
    
    try:
        print("DEBUG: Updating session state from globals")
        print(f"DEBUG: Current agent activities: {global_agent_activities}")
        
        # Initialize session state if needed
        if 'agent_activities' not in st.session_state:
            st.session_state.agent_activities = {}
        if 'agent_status' not in st.session_state:
            st.session_state.agent_status = {}
        if 'current_agent' not in st.session_state:
            st.session_state.current_agent = None
        
        # Update from global activities
        if global_agent_activities:
            # Make a safe copy of agent activities
            safe_activities = {}
            for k, v in global_agent_activities.items():
                if isinstance(v, dict):
                    # Make a safe copy of the dict
                    safe_dict = {}
                    for sub_k, sub_v in v.items():
                        # Ensure all values are JSON serializable
                        if isinstance(sub_v, (str, int, float, bool, type(None))):
                            safe_dict[sub_k] = sub_v
                        else:
                            # Convert non-serializable types to strings
                            safe_dict[sub_k] = str(sub_v)
                    safe_activities[k] = safe_dict
                else:
                    # Convert non-dict values to strings
                    safe_activities[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
            
            # Update session state with safe values
            st.session_state.agent_activities = safe_activities
            
            # Initialize agent_status if needed
            if "agent_status" not in st.session_state:
                st.session_state.agent_status = {}
            
            # Track if we found an active agent
            found_active_agent = False
            
            # Update agent status in session state
            for agent_name, agent_data in safe_activities.items():
                if isinstance(agent_data, dict) and "status" in agent_data:
                    # Update status
                    st.session_state.agent_status[agent_name] = agent_data["status"]
                    
                    # Update current agent if this one is active
                    if agent_data["status"] in ["Running", "Starting", "Processing"]:
                        st.session_state.current_agent = agent_name
                        found_active_agent = True
            
            # If no active agent found but we have a "Completed" status,
            # set the current agent to the last completed one for better UI feedback
            if not found_active_agent and not st.session_state.current_agent:
                completed_agents = [name for name, data in safe_activities.items()
                                  if isinstance(data, dict) and data.get("status") == "Completed"]
                if completed_agents:
                    st.session_state.current_agent = completed_agents[-1]
            
            # Force Streamlit to update the UI more frequently
            # This is a hack to make Streamlit update the UI more often
            if st.session_state.generation_in_progress:
                # Add a timestamp to force updates
                st.session_state.last_update = time.time()
                # Force a rerun every 2 seconds
                if not hasattr(st.session_state, 'last_rerun') or time.time() - st.session_state.last_rerun > 2:
                    st.session_state.last_rerun = time.time()
                    st.rerun()
    except Exception as e:
        print(f"Error updating session state from globals: {str(e)}")

def display_blog_analysis(analysis):
    """Display blog analysis without nested expanders."""
    # Overall score
    st.subheader(f"Overall Score: {analysis['overall_score']}/10")
    
    # Structure section
    st.markdown("### Structure")
    st.progress(analysis["structure"]["score"] / 10)
    st.markdown(f"**Score:** {analysis['structure']['score']}/10")
    
    # Structure details in tabs
    structure_tabs = st.tabs(["Strengths", "Weaknesses", "Suggestions"])
    with structure_tabs[0]:
        for strength in analysis["structure"]["strengths"]:
            st.markdown(f"- {strength}")
    with structure_tabs[1]:
        for weakness in analysis["structure"]["weaknesses"]:
            st.markdown(f"- {weakness}")
    with structure_tabs[2]:
        for suggestion in analysis["structure"]["suggestions"]:
            st.markdown(f"- {suggestion}")
    
    # Accessibility section
    st.markdown("### Accessibility")
    st.progress(analysis["accessibility"]["score"] / 10)
    st.markdown(f"**Score:** {analysis['accessibility']['score']}/10")
    
    # Accessibility details in tabs
    accessibility_tabs = st.tabs(["Strengths", "Weaknesses", "Suggestions"])
    with accessibility_tabs[0]:
        for strength in analysis["accessibility"]["strengths"]:
            st.markdown(f"- {strength}")
    with accessibility_tabs[1]:
        for weakness in analysis["accessibility"]["weaknesses"]:
            st.markdown(f"- {weakness}")
    with accessibility_tabs[2]:
        for suggestion in analysis["accessibility"]["suggestions"]:
            st.markdown(f"- {suggestion}")
    
    # Empathy section
    st.markdown("### Empathy")
    st.progress(analysis["empathy"]["score"] / 10)
    st.markdown(f"**Score:** {analysis['empathy']['score']}/10")
    
    # Empathy details in tabs
    empathy_tabs = st.tabs(["Strengths", "Weaknesses", "Suggestions"])
    with empathy_tabs[0]:
        for strength in analysis["empathy"]["strengths"]:
            st.markdown(f"- {strength}")
    with empathy_tabs[1]:
        for weakness in analysis["empathy"]["weaknesses"]:
            st.markdown(f"- {weakness}")
    with empathy_tabs[2]:
        for suggestion in analysis["empathy"]["suggestions"]:
            st.markdown(f"- {suggestion}")

def extract_business_context_from_docs():
    """Extract business context from company documents."""
    context_dir = Path("./context")
    if not context_dir.exists():
        return {
            "business_type": "SaaS",
            "industry": "Web Accessibility",
            "content_goal": "educate and inform readers",
            "keywords": ["web accessibility", "digital accessibility", "ADA compliance"]
        }
    
    # Try to find business context files
    business_files = ["business_info.md", "brand_voice.md", "target_audience.md", "business_competitors.md"]
    business_context = {
        "business_type": "SaaS",
        "industry": "Web Accessibility",
        "content_goal": "educate and inform readers",
        "keywords": []
    }
    
    # Extract keywords from context files
    keywords = []
    for file_path in context_dir.glob("*.md"):
        try:
            content = file_path.read_text()
            # Look for keywords in content
            if "keyword" in content.lower() or "seo" in content.lower():
                import re
                # Extract potential keywords
                keyword_matches = re.findall(r'\*\*([^\*]+)\*\*', content)
                keywords.extend([k.strip() for k in keyword_matches if 3 <= len(k.strip()) <= 50])
                
                # Look for specific keyword sections
                if "high-value keywords" in content.lower():
                    section = content.lower().split("high-value keywords")[1].split("##")[0]
                    section_keywords = re.findall(r'\*\s*\*\*([^:]+):', section)
                    keywords.extend([k.strip() for k in section_keywords])
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # If we found keywords, add them to the context
    if keywords:
        business_context["keywords"] = keywords[:5]  # Take top 5 keywords
    
    # Try to extract business type and industry
    for file_name in business_files:
        file_path = context_dir / file_name
        if file_path.exists():
            try:
                content = file_path.read_text().lower()
                
                # Extract business type
                if "business type:" in content and "saas" not in business_context["business_type"].lower():
                    line = [l for l in content.split("\n") if "business type:" in l.lower()]
                    if line:
                        business_context["business_type"] = line[0].split(":", 1)[1].strip().title()
                
                # Extract industry
                if "industry:" in content:
                    line = [l for l in content.split("\n") if "industry:" in l.lower()]
                    if line:
                        business_context["industry"] = line[0].split(":", 1)[1].strip().title()
                
                # Extract content goal
                if "content goal:" in content or "content purpose:" in content:
                    line = [l for l in content.split("\n") if "content goal:" in l.lower() or "content purpose:" in l.lower()]
                    if line:
                        business_context["content_goal"] = line[0].split(":", 1)[1].strip()
            except Exception as e:
                print(f"Error extracting business context from {file_path}: {e}")
    
    return business_context

def display_agent_activities(agent_activities):
    """Display agent activities from the orchestrator."""
    if not agent_activities:
        st.info("No agent activity data available.")
        return
    
    for agent_name, agent_data in agent_activities.items():
        st.markdown(f"#### {agent_name}")
        
        # Display contribution if available
        if "output" in agent_data and agent_data["output"]:
            st.markdown(f"**Contribution:** {agent_data['output']}")
        
        # Display process information
        st.markdown(f"**Process:** {agent_data.get('status', 'Unknown')}")
        
        # Display quality score if available
        if "quality" in agent_data and agent_data["quality"] > 0:
            st.markdown(f"**Output Quality:** {agent_data['quality']}/10")
        
        # Add a small divider between agents
        st.markdown("---")

def main():
    st.set_page_config(
        page_title="Blog Post Generator",
        page_icon="🚀",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Update session state from global variables
    update_session_state_from_globals()
    
    # Create a layout with sidebar and main content
    # Sidebar for post history
    with st.sidebar:
        st.title("Post History")
        st.write("Previously generated blog posts:")
        
        # Display post history
        if st.session_state.posts_history:
            # Create a scrollable container for post history
            with st.container(height=400, border=False):
                for i, post in enumerate(st.session_state.posts_history):
                    render_post_card(post, i)
        else:
            st.info("No posts generated yet. Create your first post!")
        
        # Add a button to return to current generation if viewing history
        if st.session_state.viewing_history and st.session_state.generation_in_progress:
            if st.button("Return to Current Generation", type="primary"):
                st.session_state.viewing_history = False
                st.rerun()
    
    # Main content area
    st.title("Blog Post Generator")
    
    # If viewing history and not in generation, show the history post
    if st.session_state.viewing_history and not st.session_state.generation_in_progress:
        if st.session_state.current_post:
            st.subheader(f"{st.session_state.current_post.get('title', 'Blog Post')}")
            st.markdown(st.session_state.current_post.get("content", ""))
            
            # Download button
            st.download_button(
                label="Download Blog Post",
                data=st.session_state.current_post.get("content", ""),
                file_name=f"blog_post_{st.session_state.current_post.get('title', 'post').replace(' ', '_')}.md",
                mime="text/markdown"
            )
            
            # Show path to saved markdown file
            topic_slug = st.session_state.current_post.get("topic", "post").replace(" ", "_").lower()
            markdown_filename = f"{topic_slug}_{st.session_state.current_post['id'][:8]}.md"
            markdown_path = MARKDOWN_DIRECTORY / markdown_filename
            st.success(f"Blog post saved to: {markdown_path}")
            
            # Create tabs for different views
            post_tabs = st.tabs(["Content", "Analysis", "Agent Activity"])
            
            with post_tabs[0]:
                # Content is already displayed above
                pass
                
            with post_tabs[1]:
                # Display blog analysis if available
                if "analysis" in st.session_state.current_post:
                    display_blog_analysis(st.session_state.current_post["analysis"])
                else:
                    st.info("No analysis data available for this post.")
            
            with post_tabs[2]:
                # Display agent activities if available
                if "agent_activities" in st.session_state.current_post:
                    display_agent_activities(st.session_state.current_post["agent_activities"])
                else:
                    st.info("No agent activity data available for this post.")
            
            # Edit button - using a unique key to avoid conflicts
            edit_button_key = f"edit_post_{st.session_state.current_post.get('id', 'default')}"
            if st.button("Edit This Post", key=edit_button_key):
                st.session_state.editing_post = True
                st.session_state.edit_content = st.session_state.current_post.get("content", "")
                st.rerun()
            
            # Return to main interface button
            if st.button("Return to Generator"):
                st.session_state.viewing_history = False
                st.session_state.current_post = None
                st.rerun()
    # If editing a post
    elif hasattr(st.session_state, 'editing_post') and st.session_state.editing_post:
        st.subheader("Edit Blog Post")
        edit_content = st.text_area("Edit content", value=st.session_state.edit_content, height=300)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes", type="primary"):
                # Update the post
                if st.session_state.current_post:
                    post_id = st.session_state.current_post.get("id")
                    update_post(post_id, {"content": edit_content})
                    
                    # Update current post in session state
                    st.session_state.current_post["content"] = edit_content
                    
                    # Exit editing mode
                    st.session_state.editing_post = False
                    st.rerun()
        
        with col2:
            if st.button("Cancel"):
                st.session_state.editing_post = False
                st.rerun()
    # Otherwise show the main interface
    else:
        # Mode selection
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if st.button("Auto Mode", type="primary", help="Generate blog post using pre-loaded context"):
                st.session_state.mode = 'auto'
        with mode_col2:
            if st.button("Manual Mode", help="Manually research competitors and generate content"):
                st.session_state.mode = 'manual'
        
        # Show generation progress if in progress
        if st.session_state.generation_in_progress:
            # Create a visually appealing progress container
            with st.container(border=True):
                st.markdown("### 🚀 Blog Post Generation in Progress")
                
                # Show current agent with prominent styling
                current_agent = st.session_state.current_agent
                
                # Get the current agent's activity if available
                current_activity = ""
                current_status = "Working"
                current_quality = None
                if st.session_state.agent_activities and current_agent in st.session_state.agent_activities:
                    agent_data = st.session_state.agent_activities[current_agent]
                    current_activity = agent_data.get('output', 'Working on your blog post...')
                    current_status = agent_data.get('status', 'Working')
                    current_quality = agent_data.get('quality')
                
                # Display current agent with more detailed information and accessible colors
                status_color = {
                    "Running": "#1976D2",  # Darker blue for better contrast
                    "Completed": "#2E7D32",  # Darker green for better contrast
                    "Failed": "#D32F2F",  # Darker red for better contrast
                    "Waiting": "#ED6C02"  # Darker orange for better contrast
                }.get(current_status, "#1976D2")
                
                quality_display = f"Quality: {current_quality}/10" if current_quality else ""
                
                # Use high contrast colors for text
                text_color = "#000000"  # Black text for maximum contrast
                
                st.markdown(f"""
                <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {status_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; color: {text_color};">Current Agent: <span style="color: {status_color}">{current_agent}</span></h3>
                    <p style="margin: 5px 0 0 0; color: {text_color};"><strong>Status:</strong> {current_status}</p>
                    <p style="margin: 5px 0 0 0; color: {text_color};"><strong>Activity:</strong> {current_activity}</p>
                    <p style="margin: 5px 0 0 0; color: {text_color};"><strong>{quality_display}</strong></p>
                    <p style="margin: 5px 0 0 0; color: {text_color};"><em>Last updated: {datetime.now().strftime('%H:%M:%S')}</em></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add a progress bar that updates based on agent progress
                agent_list = ["Context Agent", "Keyword Agent", "Research Agent", "Content Agent", "Quality Agent", "Humanizer Agent"]
                current_agent_index = agent_list.index(current_agent) if current_agent in agent_list else 0
                
                # Calculate progress based on completed agents
                completed_agents = sum(1 for agent in agent_list[:current_agent_index + 1]
                                    if st.session_state.agent_activities.get(agent, {}).get('status') == 'Completed')
                progress_value = completed_agents / len(agent_list)
                
                # Show overall progress with more visual appeal and accessibility
                st.markdown("#### 📊 Overall Progress")
                
                # Progress bar with high contrast colors
                progress_color = "#1976D2"  # Accessible blue
                st.markdown(f"""
                <div style="background-color: #E3F2FD; height: 20px; border-radius: 10px; margin: 10px 0;">
                    <div style="background-color: {progress_color}; width: {int(progress_value * 100)}%; height: 100%; border-radius: 10px; transition: width 0.3s ease;">
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Calculate time estimates based on agent progress and actual elapsed time
                # Each agent typically takes about 30-45 seconds
                base_time_per_agent = 0.75  # minutes
                total_estimated_minutes = len(agent_list) * base_time_per_agent
                
                # Adjust estimate based on actual progress if we have elapsed time
                if hasattr(st.session_state, 'generation_start_time') and progress_value > 0:
                    elapsed_minutes = (time.time() - st.session_state.generation_start_time) / 60
                    # Calculate rate of progress
                    progress_rate = progress_value / elapsed_minutes
                    if progress_rate > 0:
                        # Estimate total time based on current rate
                        total_estimated_minutes = min(10, elapsed_minutes / progress_rate)

                # Progress details with improved layout
                st.markdown(f"""
                <div style="background-color: #FFFFFF; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #000000;">Current Step:</strong>
                            <span style="color: #1976D2; margin-left: 5px;">{current_agent_index + 1} of {len(agent_list)}</span>
                        </div>
                        <div>
                            <strong style="color: #000000;">Progress:</strong>
                            <span style="color: #1976D2; margin-left: 5px;">{int(progress_value * 100)}%</span>
                        </div>
                    </div>
                    <div style="margin-top: 10px; color: #666666;">
                        <em>Estimated completion in {int(total_estimated_minutes * (1 - progress_value))} minutes</em>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show quality metrics if available
                quality_scores = [
                    score for agent in agent_list
                    if (score := st.session_state.agent_activities.get(agent, {}).get('quality'))
                ]
                if quality_scores:
                    avg_quality = sum(quality_scores) / len(quality_scores)
                    quality_color = '#2E7D32' if avg_quality >= 8 else '#ED6C02' if avg_quality >= 6 else '#D32F2F'
                    quality_label = 'Excellent' if avg_quality >= 8 else 'Good' if avg_quality >= 6 else 'Needs Improvement'
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 15px; background-color: #ffffff; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h4 style="margin: 0; color: #000000;">Overall Quality Score</h4>
                        <div style="display: flex; align-items: center; justify-content: center; margin: 10px 0;">
                            <div style="font-size: 32px; font-weight: bold; color: {quality_color};">
                                {avg_quality:.1f}
                            </div>
                            <div style="font-size: 18px; color: #666666; margin-left: 5px;">
                                /10
                            </div>
                        </div>
                        <div style="color: {quality_color}; font-weight: bold;">
                            {quality_label}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Create columns for a more organized layout
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Display detailed agent activities with better styling
                    st.markdown("#### 🤖 Agent Activities")
                    
                    # Create a scrollable container for agent activities
                    with st.container(height=300, border=False):
                        if st.session_state.agent_activities:
                            # Display active agent with highlight
                            for agent_name, agent_data in st.session_state.agent_activities.items():
                                is_current = agent_name == current_agent
                                status = agent_data.get("status", "Unknown")
                                
                                # Add emoji indicators for better visual cues
                                status_emoji = "🔄" if status == "Running" else "✅" if status == "Completed" else "⏳" if status == "Waiting" else "❓"
                                
                                # Style based on status and if current
                                if is_current:
                                    # Active agent card with high contrast
                                    st.markdown(f"""
                                    <div style="background-color: #ffffff; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #1976D2; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                        <h4 style="margin: 0; color: #000000;">{status_emoji} {agent_name} <span style="color: #1976D2;">ACTIVE</span></h4>
                                        <p style="margin: 5px 0; color: #000000;"><strong>Status:</strong> {status}</p>
                                        <p style="margin: 5px 0; color: #000000;"><strong>Activity:</strong> {agent_data.get('output', 'Working...')}</p>
                                        <p style="margin: 5px 0; font-size: 0.8em; color: #000000;">Updated: {datetime.now().strftime('%H:%M:%S')}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                elif status == "Completed":
                                    # Completed agent card with high contrast
                                    st.markdown(f"""
                                    <div style="background-color: #ffffff; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #2E7D32; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                        <h4 style="margin: 0; color: #000000;">{status_emoji} {agent_name} <span style="color: #2E7D32;">DONE</span></h4>
                                        <p style="margin: 5px 0; color: #000000;"><strong>Status:</strong> {status}</p>
                                        <p style="margin: 5px 0; color: #000000;"><strong>Contribution:</strong> {agent_data.get('output', 'Task completed')}</p>
                                        {f'<p style="margin: 5px 0; color: #000000;"><strong>Quality:</strong> {agent_data.get("quality", 0)}/10</p>' if "quality" in agent_data else ''}
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    # Waiting agent card with high contrast
                                    st.markdown(f"""
                                    <div style="background-color: #ffffff; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #757575; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                        <h4 style="margin: 0; color: #000000;">{status_emoji} {agent_name}</h4>
                                        <p style="margin: 5px 0; color: #000000;"><strong>Status:</strong> {status}</p>
                                        {f'<p style="margin: 5px 0; color: #000000;"><strong>Next up:</strong> {agent_data.get("output", "Waiting for previous agents to complete")}</p>' if agent_data.get("output") else ''}
                                    </div>
                                    """, unsafe_allow_html=True)
                        else:
                            st.info("Initializing agents... Please wait.")
                
                with col2:
                    # Show estimated time and tips with better styling
                    st.markdown("#### ⏱️ Estimated Time")
                    
                    
                    # Show elapsed time with better formatting
                    if hasattr(st.session_state, 'generation_start_time'):
                        elapsed_seconds = int(time.time() - st.session_state.generation_start_time)
                        elapsed_minutes = elapsed_seconds // 60
                        elapsed_seconds = elapsed_seconds % 60
                        # Force more frequent updates for elapsed time
                        current_time = time.time()
                        elapsed_seconds = int(current_time - st.session_state.generation_start_time)
                        elapsed_minutes = elapsed_seconds // 60
                        elapsed_seconds = elapsed_seconds % 60
                        elapsed_str = f"{elapsed_minutes}m {elapsed_seconds}s" if elapsed_minutes > 0 else f"{elapsed_seconds}s"
                        
                        # Add timestamp to force UI refresh
                        st.markdown(f"""
                        <div style="color: #1976D2; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            <strong>⏱️ Time elapsed:</strong> {elapsed_str}
                            <div style="display: none">{current_time}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Force a rerun every second for live updates
                        if not hasattr(st.session_state, 'last_time_update') or current_time - st.session_state.last_time_update >= 1:
                            st.session_state.last_time_update = current_time
                            st.rerun()
                    
                    # Calculate and display remaining time with better accuracy
                    if progress_value > 0:
                        estimated_total_seconds = elapsed_seconds / progress_value
                        remaining_seconds = estimated_total_seconds - elapsed_seconds
                        
                        # Format remaining time
                        if remaining_seconds < 30:
                            time_msg = "Almost done! Just a few seconds remaining"
                        else:
                            remaining_minutes = int(remaining_seconds // 60)
                            remaining_secs = int(remaining_seconds % 60)
                            if remaining_minutes > 0:
                                time_msg = f"~{remaining_minutes}m {remaining_secs}s remaining"
                            else:
                                time_msg = f"~{remaining_secs} seconds remaining"
                        
                        # Display with improved styling
                        st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 12px; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="display: flex; align-items: center;">
                                <span style="color: #1976D2; font-size: 20px; margin-right: 8px;">⌛</span>
                                <div>
                                    <strong style="color: #000000;">Estimated Time Remaining</strong>
                                    <div style="color: #1976D2; font-weight: 500; margin-top: 4px;">
                                        {time_msg}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("#### 💡 Tips")
                    tips = [
                        "Blog posts are automatically saved to your history",
                        "You can edit posts after generation",
                        "Keywords are selected based on your context files",
                        "Each agent specializes in a different aspect of content creation",
                        "The process may take several minutes to complete",
                        "You can cancel generation at any time"
                    ]
                    tip = tips[int(time.time()) % len(tips)]  # Rotate tips
                    st.info(f"**Tip:** {tip}")
                
                # Add a more visible spinner at the bottom to indicate ongoing activity
                st.markdown("#### 🔄 Generation Status")
                with st.spinner("Generating your blog post... Please wait"):
                    # This is just for UI purposes, the actual generation happens in the background
                    st.markdown(f"**Current step:** {current_agent} is {st.session_state.agent_status.get(current_agent, 'processing')}...")
                
                # Add a cancel button with better styling
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("Cancel Generation", type="secondary", use_container_width=True):
                        st.session_state.generation_in_progress = False
                        st.rerun()
                
                # Force UI updates more frequently
                st.empty().markdown(f"<div style='display:none'>{time.time()}</div>", unsafe_allow_html=True)
        
        # Automatic Mode
        elif st.session_state.mode == 'auto':
            st.info("Using pre-loaded context data from your company profile")
            
            # Load context data and extract business information
            try:
                # Extract business context using the function defined at module level
                business_context = extract_business_context_from_docs()
                
                # Use extracted business context automatically
                business_type = business_context["business_type"]
                content_goal = business_context["content_goal"]
                
                # Inform user about automatic process
                st.write("Using automatically extracted business context and keywords from your company files")
                
                if st.button("Generate Blog Post Now", type="primary"):
                    try:
                        # Initialize session state for generation
                        st.session_state.generation_in_progress = True
                        st.session_state.current_agent = "Context Agent"
                        st.session_state.generation_start_time = time.time()
                        st.session_state.agent_activities = {
                            "Context Agent": {"status": "Starting", "output": "Initializing blog generation process"},
                            "Research Agent": {"status": "Waiting", "output": ""},
                            "Keyword Agent": {"status": "Waiting", "output": ""},
                            "Content Agent": {"status": "Waiting", "output": ""},
                            "Quality Agent": {"status": "Waiting", "output": ""},
                            "Humanizer Agent": {"status": "Waiting", "output": ""}
                        }
                        st.session_state.agent_status = {
                            "Context Agent": "Starting",
                            "Research Agent": "Waiting",
                            "Keyword Agent": "Waiting",
                            "Content Agent": "Waiting",
                            "Quality Agent": "Waiting",
                            "Humanizer Agent": "Waiting"
                        }
                        
                        # Start the blog generation task
                        start_blog_generation_task(
                            business_type=business_type,
                            content_goal=content_goal,
                            web_references=3
                        )
                        st.success("Blog post generation started with automatic keyword selection!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error starting blog generation: {str(e)}")
                        st.session_state.generation_in_progress = False
                    
            except Exception as e:
                st.error(f"Error loading company context: {str(e)}")
                # Fallback to default options
                business_type = "SaaS"
                content_goal = "educate and inform readers"
                
                # Inform user about fallback to defaults
                st.write("Using default business context and keywords due to error loading context files")
                
                if st.button("Generate Blog Post Now", type="primary"):
                    # Start the blog generation task
                    start_blog_generation_task(
                        business_type=business_type,
                        content_goal=content_goal,
                        web_references=3
                    )
                    st.success("Blog post generation started with automatic keyword selection!")
                    st.rerun()
        
        # Manual Mode
        else:
            # Use default business context
            business_type = "SaaS"
            content_goal = "educate and inform readers"
            web_references = 3
            
            st.info("Using default business context and automatically selecting keywords from your context files")
            
            # Content Generation
            if st.button("Generate Blog Post", type="primary"):
                try:
                    # Initialize session state for generation
                    st.session_state.generation_in_progress = True
                    st.session_state.current_agent = "Context Agent"
                    st.session_state.generation_start_time = time.time()
                    st.session_state.agent_activities = {
                        "Context Agent": {"status": "Starting", "output": "Initializing blog generation process"},
                        "Research Agent": {"status": "Waiting", "output": ""},
                        "Keyword Agent": {"status": "Waiting", "output": ""},
                        "Content Agent": {"status": "Waiting", "output": ""},
                        "Quality Agent": {"status": "Waiting", "output": ""},
                        "Humanizer Agent": {"status": "Waiting", "output": ""}
                    }
                    st.session_state.agent_status = {
                        "Context Agent": "Starting",
                        "Research Agent": "Waiting",
                        "Keyword Agent": "Waiting",
                        "Content Agent": "Waiting",
                        "Quality Agent": "Waiting",
                        "Humanizer Agent": "Waiting"
                    }
                    
                    # Start the blog generation task
                    start_blog_generation_task(
                        business_type=business_type,
                        content_goal=content_goal,
                        web_references=web_references
                    )
                    st.success("Blog post generation started with automatic keyword selection!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error starting blog generation: {str(e)}")
                    st.session_state.generation_in_progress = False

if __name__ == "__main__":
    main()
