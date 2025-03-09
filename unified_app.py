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

# Set page config before any other Streamlit commands
st.set_page_config(
    page_title="Blog Post Generator",
    page_icon="🚀",
    layout="wide"
)

# Import our modules
try:
    # Make sure re is available to all modules
    import sys
    if 're' not in sys.modules:
        sys.modules['re'] = re
        
    from src.utils.openai_blog_analyzer import analyze_content, analyze_and_save
    from src.utils.competitor_blog_scraper import scrape_competitor_blogs, analyze_competitor_structure, CompetitorBlogs
    from src.utils.keyword_research_manager import get_keyword_suggestions, KeywordResearch
    from src.utils.openai_blog_writer import BlogPost
    from src.utils.context_keyword_manager import extract_keywords_from_context, load_context_files, get_initial_keyword
    from src.utils.keyword_history_manager import KeywordHistoryManager
    from src.utils.update_session_state import (
        update_session_state_from_globals,
        display_blog_analysis,
        display_agent_activities,
        render_post_card
    )
    from src.utils.post_manager import save_post, update_post
    from src.utils.logging_manager import logging_manager, log_info, log_warning, log_error, log_debug
    from dotenv import load_dotenv
    import src.agents as agents
    from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector

    # Initialize managers
    keyword_history = KeywordHistoryManager()
    keyword_selector = EnhancedKeywordSelector()
    
    # Initialize logging manager and clear any old logs
    logging_manager.clear_logs()
    
    # Initialize agent orchestrator
    AgentOrchestrator = agents.get_agent_orchestrator()
    orchestrator = AgentOrchestrator()
    
    log_info("Blog Post Generator started", "APP")
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Some modules could not be imported. This may affect functionality.")

# Load environment variables
load_dotenv()

# Constants
POSTS_DIRECTORY = Path("./generated_posts")
POSTS_DIRECTORY.mkdir(exist_ok=True)
MARKDOWN_DIRECTORY = Path("./generated_posts/markdown")
MARKDOWN_DIRECTORY.mkdir(exist_ok=True, parents=True)

# Global variables to store agent activities
global_agent_activities = {}  # Store real agent activities

# Async task management
async_tasks = {}

def init_session_state() -> None:
    """Initialize session state with all required keys."""
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
                    log_debug(f"Loaded post: {post_data.get('title', 'Untitled')}", "APP")
            except Exception as e:
                log_error(f"Error loading post {file_path}: {e}", "APP")
    
    # Sort by timestamp (newest first)
    return sorted(posts, key=lambda x: x.get("timestamp", 0), reverse=True)

def extract_business_context_from_docs():
    """Extract business context from company documents."""
    context_dir = Path("./context")
    if not context_dir.exists():
        log_warning("Context directory not found, using default business context", "APP")
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
                    log_debug(f"Found high-value keywords in {file_path.name}", "APP")
        except Exception as e:
            log_error(f"Error reading {file_path}: {e}", "APP")
    
    # If we found keywords, add them to the context
    if keywords:
        business_context["keywords"] = keywords[:5]  # Take top 5 keywords
        log_debug(f"Extracted {len(keywords)} keywords, using top 5", "APP")
    
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
                        log_debug(f"Found business type: {business_context['business_type']}", "APP")
                
                # Extract industry
                if "industry:" in content:
                    line = [l for l in content.split("\n") if "industry:" in l.lower()]
                    if line:
                        business_context["industry"] = line[0].split(":", 1)[1].strip().title()
                        log_debug(f"Found industry: {business_context['industry']}", "APP")
                
                # Extract content goal
                if "content goal:" in content or "content purpose:" in content:
                    line = [l for l in content.split("\n") if "content goal:" in l.lower() or "content purpose:" in l.lower()]
                    if line:
                        business_context["content_goal"] = line[0].split(":", 1)[1].strip()
                        log_debug(f"Found content goal: {business_context['content_goal']}", "APP")
            except Exception as e:
                log_error(f"Error extracting business context from {file_path}: {e}", "APP")
    
    return business_context

async def generate_blog_post_with_orchestrator(
    topic: str = "web accessibility",
    business_type: str = "Technology",
    content_goal: str = "educate and inform readers",
    web_references: int = 3,
    industry: str = None,
    add_case_studies: bool = True,
    add_expert_quotes: bool = True,
    add_real_data: bool = True,
    enhanced_formatting: bool = True,
    use_premium_model: bool = True
) -> Optional[BlogPost]:
    """
    Generate a blog post using the agent orchestrator with automatic keyword selection.
    Uses competitor blog analysis to improve content quality and style.
    Provides frequent UI updates to keep the user informed of progress.
    
    Args:
        topic: Main topic for the blog post
        business_type: Type of business (e.g., "Technology", "E-commerce")
        content_goal: Primary goal of the content (e.g., "educate", "convert")
        web_references: Number of web references to use
        industry: Target industry for industry-specific content
        add_case_studies: Whether to include case studies
        add_expert_quotes: Whether to include expert quotes
        add_real_data: Whether to include real data and statistics
        enhanced_formatting: Whether to use enhanced formatting
        use_premium_model: Whether to use premium LLM model (GPT-4)
        
    Returns:
        BlogPost object containing the generated content and metrics
    """
    try:
        # Initialize orchestrator using lazy import
        AgentOrchestrator = agents.get_agent_orchestrator()
        orchestrator = AgentOrchestrator()
        
        log_info(f"Starting blog post generation for topic: {topic}", "APP")
        
        # Generate blog post
        blog_post = await orchestrator.generate_blog_post(
            topic=topic,
            business_type=business_type,
            content_goal=content_goal,
            web_references=web_references,
            industry=industry,
            add_case_studies=add_case_studies,
            add_expert_quotes=add_expert_quotes,
            add_real_data=add_real_data,
            enhanced_formatting=enhanced_formatting,
            use_premium_model=use_premium_model
        )
        
        log_info("Successfully generated blog post", "APP")
        return blog_post
    except Exception as e:
        log_error(f"Error in generate_blog_post_with_orchestrator: {str(e)}", "APP")
        return None

def start_blog_generation_task(
    topic: str,
    business_type: str, 
    content_goal: str, 
    web_references: int,
    industry: str = None,
    add_case_studies: bool = True,
    add_expert_quotes: bool = True,
    add_real_data: bool = True,
    enhanced_formatting: bool = True,
    use_premium_model: bool = True
) -> None:
    """
    Start an asynchronous blog generation task with automatic keyword selection.
    
    Args:
        topic: Main topic for the blog post
        business_type: Type of business
        content_goal: Primary goal of the content
        web_references: Number of web references to use
        industry: Target industry for industry-specific content
        add_case_studies: Whether to include case studies
        add_expert_quotes: Whether to include expert quotes
        add_real_data: Whether to include real data and statistics
        enhanced_formatting: Whether to use enhanced formatting
        use_premium_model: Whether to use premium LLM model (GPT-4)
    """
    # Log task start
    log_debug(f"Starting blog generation task for topic: {topic}", "APP")
    log_debug(f"Options: business_type={business_type}, content_goal={content_goal}, industry={industry}", "APP")
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Create and start the task
    async def run_task():
        global global_agent_activities
        try:
            # Log task initialization
            log_debug(f"Run task started at {datetime.now().strftime('%H:%M:%S')}", "APP")
            
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
            
            # Generate the blog post
            blog_post = await generate_blog_post_with_orchestrator(
                topic=topic,
                business_type=business_type,
                content_goal=content_goal,
                web_references=web_references,
                industry=industry,
                add_case_studies=add_case_studies,
                add_expert_quotes=add_expert_quotes,
                add_real_data=add_real_data,
                enhanced_formatting=enhanced_formatting,
                use_premium_model=use_premium_model
            )
            
            if blog_post:
                # Create post data
                post_data = {
                    "id": str(uuid.uuid4()),
                    "title": blog_post.title,
                    "content": blog_post.content,
                    "topic": topic,
                    "timestamp": datetime.now().timestamp(),
                    "metrics": blog_post.metrics.model_dump(),
                    "keywords": blog_post.keywords,
                    "outline": blog_post.outline,
                    "agent_activities": global_agent_activities,
                    "generation_time": time.time() - st.session_state.generation_start_time
                }
                
                # Save the post
                save_post(post_data, POSTS_DIRECTORY, MARKDOWN_DIRECTORY)
                log_info(f"Saved blog post: {post_data['title']}", "APP")
                
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
                    
                    # Get analysis result
                    analysis_result = await analyze_content(blog_post.content)
                    
                    # Update post with analysis
                    post_data["analysis"] = analysis_result
                    update_post(post_data["id"], {"analysis": analysis_result}, POSTS_DIRECTORY, MARKDOWN_DIRECTORY)
                    log_info("Successfully analyzed blog post", "APP")
                    
                    # Update UI to show analysis is complete
                    global_agent_activities["Analysis Agent"] = {
                        "status": "Completed",
                        "output": "Blog post analysis complete"
                    }
                except Exception as analysis_error:
                    log_error(f"Error analyzing blog post: {str(analysis_error)}", "APP")
                    global_agent_activities["Analysis Agent"] = {
                        "status": "Failed",
                        "output": f"Error analyzing blog post: {str(analysis_error)}"
                    }
            
            # Update session state to indicate generation has completed
            st.session_state.generation_in_progress = False
            log_info("Blog post generation completed", "APP")
            
        except Exception as e:
            log_error(f"Error in blog generation task: {str(e)}", "APP")
            global_agent_activities["Error"] = {
                "status": "Failed",
                "output": f"Error generating blog post: {str(e)}"
            }
            st.session_state.generation_in_progress = False
    
    # Create a new event loop for the task
    loop = asyncio.new_event_loop()
    
    # Create a thread to run the task with proper context
    def run_async_task():
        try:
            # Set up thread-local storage
            import contextvars
            ctx = contextvars.copy_context()
            
            # Create and set event loop
            asyncio.set_event_loop(loop)
            
            # Run task in context
            ctx.run(lambda: loop.run_until_complete(run_task()))
        except Exception as e:
            log_error(f"Error in async task thread: {str(e)}", "APP")
        finally:
            loop.close()
    
    # Start the thread with error handling
    try:
        task_thread = threading.Thread(target=run_async_task)
        task_thread.daemon = True
        task_thread.start()
        log_debug("Started async task thread successfully", "APP")
    except Exception as e:
        log_error(f"Failed to start task thread: {str(e)}", "APP")
    
    # Store the task
    async_tasks[task_id] = {
        "thread": task_thread,
        "loop": loop,
        "start_time": datetime.now().timestamp()
    }

def main():
    """Main function to run the Streamlit app."""
    # Initialize session state
    init_session_state()
    
    # Update session state from global variables
    global global_agent_activities
    update_session_state_from_globals(global_agent_activities)
    
    # Create a layout with sidebar and main content
    with st.sidebar:
        st.title("Post History")
        st.write("Previously generated blog posts:")
        
        # Display post history
        if st.session_state.posts_history:
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
    if st.session_state.generation_in_progress:
        st.title("Generating Blog Post")
        
        # Show current agent status
        current_agent = st.session_state.current_agent or "Initializing"
        st.subheader(f"Current Stage: {current_agent}")
        
        # Create a container for real-time status
        with st.container(border=True):
            # Progress indicator
            if st.session_state.agent_activities:
                total_agents = len(st.session_state.agent_activities)
                completed_agents = sum(1 for agent in st.session_state.agent_activities.values() 
                                if isinstance(agent, dict) and agent.get('status') == 'Completed')
                progress = completed_agents / total_agents
                st.progress(progress, text=f"Progress: {int(progress * 100)}%")
        
        # Add a scrollable log container
        st.markdown("### Generation Logs")
        
        # Display logs in reverse chronological order (newest first)
        with st.container(height=600, border=True):
            # Create columns for log filtering
            col1, col2, col3 = st.columns(3)
            with col1:
                show_debug = st.checkbox("Show Debug Logs", value=True)
            with col2:
                show_info = st.checkbox("Show Info Logs", value=True)
            with col3:
                show_errors = st.checkbox("Show Warnings/Errors", value=True)
            
            # Get more logs to ensure we don't miss any
            all_logs = logging_manager.get_recent_logs(count=2000)  # Increased buffer size significantly
            
            # Filter logs based on user preferences
            filtered_logs = []
            for log in reversed(all_logs):
                level = log.get('level', 'INFO')
                message = log.get('message', '')
                emoji = log.get('emoji', '📝')  # Get emoji from log entry
                
                # Skip HTTP request logs and empty messages
                if "HTTP Request:" in message or not message.strip():
                    continue
                
                # Apply user filters
                if level == 'DEBUG' and not show_debug:
                    continue
                if level == 'INFO' and not show_info:
                    continue
                if level in ['WARNING', 'ERROR'] and not show_errors:
                    continue
                
                filtered_logs.append({
                    'timestamp': log.get('timestamp', ''),
                    'level': level,
                    'message': message,
                    'emoji': emoji
                })
            
            # Group logs by timestamp (minute)
            grouped_logs = {}
            for log in filtered_logs:
                timestamp = log.get('timestamp', '')
                minute = timestamp[:5] if timestamp else ''  # Get HH:MM
                if minute not in grouped_logs:
                    grouped_logs[minute] = []
                grouped_logs[minute].append(log)
            
            # Display logs with collapsible groups
            for minute, logs in grouped_logs.items():
                with st.expander(f"Logs from {minute}", expanded=True):
                    for log in logs:
                        timestamp = log.get('timestamp', '')
                        level = log.get('level', 'INFO')
                        message = log.get('message', '')
                        
                        # Use different colors for different log levels
                        if log['level'] == 'ERROR':
                            st.error(f"{log['emoji']} `[{log['timestamp']}]` **{log['level']}**: {log['message']}")
                        elif log['level'] == 'WARNING':
                            st.warning(f"{log['emoji']} `[{log['timestamp']}]` **{log['level']}**: {log['message']}")
                        elif log['level'] == 'DEBUG':
                            st.text(f"{log['emoji']} [{log['timestamp']}] {log['level']}: {log['message']}")
                        else:
                            st.info(f"{log['emoji']} `[{log['timestamp']}]` **{log['level']}**: {log['message']}")
    
    elif st.session_state.viewing_history and st.session_state.current_post:
        # Display the selected post
        post = st.session_state.current_post
        st.title(post.get("title", "Blog Post"))
        
        # Create columns for metadata
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            st.write(f"📅 Generated on: {datetime.fromtimestamp(post.get('timestamp', 0)).strftime('%B %d, %Y')}")
        with meta_col2:
            if st.button("← Back to Generator", type="primary"):
                st.session_state.viewing_history = False
                st.session_state.current_post = None
                st.rerun()
        
        # Display content in a container with padding
        with st.container(border=True):
            st.markdown(post.get("content", ""))
        
        # Display analysis if available
        if "analysis" in post:
            st.divider()
            st.subheader("Content Analysis")
            display_blog_analysis(post["analysis"])
            
        # Don't show generation process in older blogs
    else:
        # Show the normal generation UI
        st.title("Blog Post Generator")
        
        # Mode selection
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if st.button("Auto Mode", type="primary", help="Generate blog post using pre-loaded context"):
                st.session_state.mode = 'auto'
        with mode_col2:
            if st.button("Manual Mode", help="Manually research competitors and generate content"):
                st.session_state.mode = 'manual'
        
        # Automatic Mode
        if st.session_state.mode == 'auto':
            st.info("Using pre-loaded context data from your company profile")
            
            # Load context data and extract business information
            try:
                # Extract business context using the function defined at module level
                business_context = extract_business_context_from_docs()
                
                # Use extracted business context automatically
                business_type = business_context["business_type"]
                content_goal = business_context["content_goal"]
                
                # Get next keyword from topology manager
                try:
                    from src.agents.agent_orchestrator import get_next_recommended_keyword
                    next_keyword = asyncio.run(get_next_recommended_keyword())
                    log_info(f"Using next recommended keyword from topology: {next_keyword}", "APP")
                except Exception as e:
                    # Fallback to simple selector if topology fails
                    log_warning(f"Error getting keyword from topology: {str(e)}", "APP")
                    next_keyword = asyncio.run(keyword_selector.get_next_keyword())
                
                # Create an expander for advanced content options
                with st.expander("Advanced Content Options", expanded=True):
                    # Industry selection
                    industry_options = ["Random", "None", "Healthcare", "Finance", "E-commerce", "Education", "Technology"]
                    industry = st.selectbox("Target Industry", industry_options, 
                                           help="Select an industry to generate industry-specific content, 'None' for general content, or 'Random' for automatic selection")
                    # Convert "None" selection to empty string for consistency
                    if industry == "None":
                        industry = ""
                    
                    # Enhanced content toggles
                    st.write("Content Enhancements:")
                    col1, col2 = st.columns(2)
                    with col1:
                        add_case_studies = st.toggle("Add Case Studies", value=True, 
                                                   help="Include relevant case studies with documented results")
                        add_expert_quotes = st.toggle("Add Expert Quotes", value=True, 
                                                     help="Include quotes from industry experts")
                    with col2:
                        add_real_data = st.toggle("Add Real Data & Statistics", value=True, 
                                                 help="Include real statistics with proper sources")
                        enhanced_formatting = st.toggle("Enhanced Formatting", value=True, 
                                                       help="Use advanced formatting with callouts, blockquotes, etc.")
                    
                    # Model selection
                    use_premium_model = st.toggle("Use Premium LLM", value=True, 
                                                help="Use GPT-4 for higher quality content (may be slower)")
                
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
                            topic=next_keyword,
                            business_type=business_type,
                            content_goal=content_goal,
                            web_references=3,
                            industry=industry,
                            add_case_studies=add_case_studies,
                            add_expert_quotes=add_expert_quotes,
                            add_real_data=add_real_data,
                            enhanced_formatting=enhanced_formatting,
                            use_premium_model=use_premium_model
                        )
                        st.success(f"Blog post generation started for topic: {next_keyword}")
                        st.rerun()
                    except Exception as e:
                        log_error(f"Error starting blog generation: {str(e)}", "APP")
                        st.error(f"Error starting blog generation: {str(e)}")
                        st.session_state.generation_in_progress = False
                        
            except Exception as e:
                log_error(f"Error loading company context: {str(e)}", "APP")
                st.error(f"Error loading company context: {str(e)}")
                # Fallback to default options
                business_type = "SaaS"
                content_goal = "educate and inform readers"
                
                # Get next keyword from topology manager for fallback case
                try:
                    from src.agents.agent_orchestrator import get_next_recommended_keyword
                    next_keyword = asyncio.run(get_next_recommended_keyword())
                    log_info(f"Using next recommended keyword from topology (fallback): {next_keyword}", "APP")
                except Exception as e:
                    # Fallback to simple selector if topology fails
                    log_warning(f"Error getting keyword from topology fallback: {str(e)}", "APP")
                    next_keyword = asyncio.run(keyword_selector.get_next_keyword())
                
                # Create an expander for advanced content options
                with st.expander("Advanced Content Options", expanded=True):
                    # Industry selection
                    industry_options = ["Random", "None", "Healthcare", "Finance", "E-commerce", "Education", "Technology"]
                    industry = st.selectbox("Target Industry", industry_options, 
                                           help="Select an industry to generate industry-specific content, 'None' for general content, or 'Random' for automatic selection")
                    # Convert "None" selection to empty string for consistency
                    if industry == "None":
                        industry = ""
                    
                    # Enhanced content toggles
                    st.write("Content Enhancements:")
                    col1, col2 = st.columns(2)
                    with col1:
                        add_case_studies = st.toggle("Add Case Studies", value=True, 
                                                   help="Include relevant case studies with documented results")
                        add_expert_quotes = st.toggle("Add Expert Quotes", value=True, 
                                                     help="Include quotes from industry experts")
                    with col2:
                        add_real_data = st.toggle("Add Real Data & Statistics", value=True, 
                                                 help="Include real statistics with proper sources")
                        enhanced_formatting = st.toggle("Enhanced Formatting", value=True, 
                                                       help="Use advanced formatting with callouts, blockquotes, etc.")
                    
                    # Model selection
                    use_premium_model = st.toggle("Use Premium LLM", value=True, 
                                                help="Use GPT-4 for higher quality content (may be slower)")
                
                if st.button("Generate Blog Post Now", type="primary"):
                    # Start the blog generation task with advanced options
                    start_blog_generation_task(
                        topic=next_keyword,
                        business_type=business_type,
                        content_goal=content_goal,
                        web_references=3,
                        industry=industry,
                        add_case_studies=add_case_studies,
                        add_expert_quotes=add_expert_quotes,
                        add_real_data=add_real_data,
                        enhanced_formatting=enhanced_formatting,
                        use_premium_model=use_premium_model
                    )
                    st.success(f"Blog post generation started for topic: {next_keyword}")
                    st.rerun()
        
        # Manual Mode
        else:
            st.info("Using manual keyword selection")
            
            # Manual keyword input
            manual_keyword = st.text_input("Enter Topic/Keyword:", 
                placeholder="E.g., web accessibility, ADA compliance, screen readers",
                help="Enter a specific topic to write about")
            
            # Create an expander for advanced content options
            with st.expander("Advanced Content Options", expanded=True):
                # Industry selection
                industry_options = ["Random", "None", "Healthcare", "Finance", "E-commerce", "Education", "Technology"]
                industry = st.selectbox("Target Industry", industry_options, 
                                       help="Select an industry to generate industry-specific content, 'None' for general content, or 'Random' for automatic selection")
                # Convert "None" selection to empty string for consistency
                if industry == "None":
                    industry = ""
                # Enhanced content toggles
                st.write("Content Enhancements:")
                col1, col2 = st.columns(2)
                with col1:
                    add_case_studies = st.toggle("Add Case Studies", value=True, 
                                               help="Include relevant case studies with documented results")
                    add_expert_quotes = st.toggle("Add Expert Quotes", value=True, 
                                                 help="Include quotes from industry experts")
                with col2:
                    add_real_data = st.toggle("Add Real Data & Statistics", value=True, 
                                             help="Include real statistics with proper sources")
                    enhanced_formatting = st.toggle("Enhanced Formatting", value=True, 
                                                   help="Use advanced formatting with callouts, blockquotes, etc.")
                
                # Model selection
                use_premium_model = st.toggle("Use Premium LLM", value=True, 
                                            help="Use GPT-4 for higher quality content (may be slower)")
            
            # Content Generation
            generate_button_disabled = not manual_keyword  # Disable button if no keyword entered
            if st.button("Generate Blog Post", type="primary", disabled=generate_button_disabled):
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
                    
                    # Start the blog generation task with advanced options and manually selected keyword
                    start_blog_generation_task(
                        topic=manual_keyword,
                        business_type="SaaS",  # Default for manual mode
                        content_goal="educate and inform readers",  # Default for manual mode
                        web_references=3,
                        industry=industry,
                        add_case_studies=add_case_studies,
                        add_expert_quotes=add_expert_quotes,
                        add_real_data=add_real_data,
                        enhanced_formatting=enhanced_formatting,
                        use_premium_model=use_premium_model
                    )
                    st.success(f"Blog post generation started for topic: {manual_keyword}")
                    st.rerun()
                except Exception as e:
                    log_error(f"Error starting blog generation: {str(e)}", "APP")
                    st.error(f"Error starting blog generation: {str(e)}")
                    st.session_state.generation_in_progress = False
            elif generate_button_disabled:
                st.warning("Please enter a topic first")

if __name__ == "__main__":
    main()
