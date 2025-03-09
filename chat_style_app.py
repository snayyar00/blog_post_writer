"""
Chat-style Streamlit app for blog post generation with post history sidebar and real-time cost reporting.
Combines the original design with new features for tracking post history and costs.
"""

import os
import json
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import uuid
import asyncio
import threading
import random

# Import our modules
try:
    from src.utils.openai_blog_analyzer import analyze_content, analyze_and_save
    from src.models.analysis_models import BlogAnalysis, AnalysisSection
    from src.utils.competitor_blog_scraper import scrape_competitor_blogs, analyze_competitor_structure, CompetitorBlogs
    from src.utils.keyword_research_manager import get_keyword_suggestions, KeywordResearch
    from src.utils.openai_blog_writer import generate_blog_post, BlogPost
    from src.utils.cost_tracker import generate_cost_report, save_cost_report, get_cost_tracker, log_api_call
    from dotenv import load_dotenv
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

# Global variables for cost tracking
cost_update_interval = 2  # seconds
cost_tracker_thread = None
stop_cost_tracker = False

# Global variables to store cost data (to avoid Streamlit context issues)
global_cost_report = None
global_total_cost = 0.0
global_cost_by_provider = {}

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
        'cost_report': None,  # Cost report data
        'total_cost': 0.0,  # Total cost so far
        'cost_by_provider': {},  # Cost breakdown by provider
        'cost_by_agent': {},  # Cost breakdown by agent
        'website_url': '',  # Website URL for analysis
        'is_generation_paused': False,  # Pause state for generation
        'current_agent': "Context Agent",  # Current active agent
        'generation_started': False,  # Flag to track if generation has started
        'agent_status': {},  # Status of each agent
        'perplexity_status': "Not started",  # Status of Perplexity research
        'concurrent_tasks': [],  # List of concurrent tasks
        'viewing_history': False,  # Flag to track if user is viewing history
        'generation_in_progress': False,  # Flag to track if generation is in progress
        'cost_tracker_running': False,  # Flag to track if cost tracker is running
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
    
    # Save to file
    with open(file_path, "w") as f:
        json.dump(post_data, f, indent=2)
    
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
                    # Update the data
                    post_data.update(updated_data)
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

def update_cost_display():
    """Update the cost display in real-time."""
    global stop_cost_tracker, global_cost_report, global_total_cost, global_cost_by_provider
    
    try:
        print("Cost tracker thread started")
        while not stop_cost_tracker:
            try:
                # Get the latest cost report
                cost_report = generate_cost_report()
                
                # Update global variables instead of session state
                global_cost_report = cost_report
                
                # Extract total cost
                lines = cost_report.split("\n")
                total_cost_line = next((line for line in lines if "Total Cost:" in line), "Total Cost: $0.0000")
                total_cost_str = total_cost_line.split("$")[1].strip()
                try:
                    global_total_cost = float(total_cost_str)
                except ValueError:
                    pass
                
                # Extract costs by provider
                provider_costs = {}
                in_provider_section = False
                for line in lines:
                    if "## Cost by Provider" in line:
                        in_provider_section = True
                        continue
                    if in_provider_section and line.startswith("##"):
                        in_provider_section = False
                        break
                    if in_provider_section and line.startswith("- **"):
                        parts = line.split("$")
                        if len(parts) >= 2:
                            provider = parts[0].replace("- **", "").replace("**:", "").strip()
                            try:
                                cost = float(parts[1].strip())
                                provider_costs[provider] = cost
                            except ValueError:
                                pass
                
                global_cost_by_provider = provider_costs
                
            except Exception as e:
                print(f"Error updating cost display: {e}")
            
            # Sleep for a short interval
            time.sleep(cost_update_interval)
            
    except Exception as e:
        print(f"Error in update_cost_display thread: {e}")
    
    print("Cost tracker thread stopped")

def start_cost_tracker():
    """Start the cost tracking thread if not already running."""
    global cost_tracker_thread, stop_cost_tracker
    
    # Make sure generation_started is set to True
    if 'generation_started' not in st.session_state:
        st.session_state.generation_started = True
    
    if cost_tracker_thread is None or not cost_tracker_thread.is_alive():
        stop_cost_tracker = False
        cost_tracker_thread = threading.Thread(target=update_cost_display)
        cost_tracker_thread.daemon = True
        cost_tracker_thread.start()
        print("Cost tracker started")

def stop_cost_tracker_thread():
    """Stop the cost tracking thread."""
    global stop_cost_tracker
    stop_cost_tracker = True
    print("Cost tracker stopping...")

def update_session_state_from_globals():
    """Update session state from global variables to avoid thread context issues."""
    global global_cost_report, global_total_cost, global_cost_by_provider
    
    if global_cost_report is not None:
        st.session_state.cost_report = global_cost_report
    
    if global_total_cost > 0:
        st.session_state.total_cost = global_total_cost
    
    if global_cost_by_provider:
        st.session_state.cost_by_provider = global_cost_by_provider

def generate_dynamic_outline(keyword: str) -> List[str]:
    """Generate a dynamic outline for a blog post based on the keyword."""
    # Always include TLDR
    outline = ["## TLDR"]
    
    # Generate a dynamic title
    title_templates = [
        f"# {keyword.title()}: The Ultimate Guide",
        f"# The Complete Guide to {keyword.title()}",
        f"# Mastering {keyword.title()}: A Comprehensive Guide",
        f"# Everything You Need to Know About {keyword.title()}",
        f"# {keyword.title()}: Best Practices and Implementation Strategies",
        f"# Unlocking the Power of {keyword.title()}",
        f"# {keyword.title()}: A Deep Dive",
        f"# The Definitive Guide to {keyword.title()}"
    ]
    outline.append(random.choice(title_templates))
    
    # Always include Introduction
    outline.append("## Introduction")
    
    # Generate a pool of potential sections
    section_pool = [
        f"## What is {keyword.title()}?",
        f"## Understanding {keyword.title()}",
        f"## The Importance of {keyword.title()}",
        f"## Why {keyword.title()} Matters",
        f"## Benefits of {keyword.title()}",
        f"## Advantages of Implementing {keyword.title()}",
        f"## Key Features of {keyword.title()}",
        f"## {keyword.title()} Best Practices",
        f"## Implementing {keyword.title()} Successfully",
        f"## Common Challenges with {keyword.title()}",
        f"## Overcoming {keyword.title()} Obstacles",
        f"## {keyword.title()} in Different Industries",
        f"## Real-World Applications of {keyword.title()}",
        f"## Case Studies: {keyword.title()} in Action",
        f"## Expert Tips for {keyword.title()}",
        f"## The Future of {keyword.title()}",
        f"## {keyword.title()} Trends to Watch",
        f"## Tools and Resources for {keyword.title()}",
        f"## Measuring {keyword.title()} Success",
        f"## ROI of {keyword.title()}"
    ]
    
    # Randomly select 3-6 sections from the pool
    num_sections = random.randint(3, 6)
    selected_sections = random.sample(section_pool, min(num_sections, len(section_pool)))
    outline.extend(selected_sections)
    
    # Always include Conclusion
    outline.append("## Conclusion")
    
    return outline

async def load_preloaded_context() -> Dict[str, Any]:
    """Load pre-existing context data from context directory"""
    try:
        # This would normally load from files, but for now we'll use a mock
        context = {
            'business_type': 'Technology',
            'content_goals': ['Educate', 'Engage', 'Convert'],
            'common_headings': [
                'Introduction to [Topic]',
                'Why [Topic] Matters',
                'How to Implement [Topic]',
                'Best Practices for [Topic]',
                'Conclusion'
            ],
            'popular_keywords': [
                'optimization', 'strategy', 'implementation',
                'best practices', 'guide', 'tutorial'
            ],
            'competitor_insights': {
                'common_structures': [
                    'Problem-Solution-Benefits',
                    'How-To Guide with Steps',
                    'List-Based Article (Top 10)'
                ],
                'popular_keywords': [
                    'technology solutions', 'digital transformation',
                    'business efficiency', 'automation tools'
                ]
            }
        }
        
        # Store in session state for consistency
        st.session_state.business_context = context
        
        return context
    except Exception as e:
        st.error(f"Failed to load context: {str(e)}")
        return {}

async def run_perplexity_research(keyword: str) -> Dict[str, Any]:
    """Run Perplexity deep research in a separate task."""
    try:
        st.session_state.perplexity_status = "Running"
        
        # Simulate Perplexity research
        await asyncio.sleep(2)
        
        # Log the API call
        log_api_call("perplexity", "sonar-deep-research", "research", 1000, 2000)
        
        st.session_state.perplexity_status = "Completed"
        
        return {
            "research_data": f"Deep research on {keyword}",
            "sources": ["source1", "source2"]
        }
    except Exception as e:
        st.session_state.perplexity_status = f"Error: {str(e)}"
        return {"error": str(e)}

async def analyze_blog_content(content: str) -> Dict[str, Any]:
    """Analyze blog content using OpenAI."""
    try:
        # Log the API call
        log_api_call("openai", "gpt-4o", "blog_analysis", 3000, 2000)
        
        # This would normally call the OpenAI API, but for now we'll simulate it
        await asyncio.sleep(1)
        
        # Generate dynamic analysis based on content
        keywords = content.split()[:5]  # Just use the first 5 words as example keywords
        
        analysis = {
            "overall_score": 8.7,
            "structure": {
                "score": 8.8,
                "strengths": [
                    f"The blog post has a clear and logical flow, starting with an introduction to {keywords[0] if keywords else 'the topic'}.",
                    "Use of headers and subheaders is effective, providing structure and making the content easy to scan.",
                    "Paragraphs are well-organized and of an appropriate length, each focusing on one specific aspect."
                ],
                "weaknesses": [
                    "Some sentences could be clearer and more concise.",
                    "The content hierarchy could be more prominent in certain sections."
                ],
                "suggestions": [
                    "Simplify and shorten complex sentences where possible.",
                    "Highlight key features and benefits more prominently using bullet points or bold text.",
                    "Consider adding a summary section at the end to reiterate key points."
                ]
            },
            "accessibility": {
                "score": 8.6,
                "strengths": [
                    f"The blog post clearly addresses {keywords[1] if len(keywords) > 1 else 'accessibility'} considerations.",
                    "The explanation of accessibility features is comprehensive.",
                    "The blog post effectively communicates the benefits of accessibility."
                ],
                "weaknesses": [
                    "Could provide more specific examples of how features benefit users with different abilities.",
                    "The post could include more real-world applications."
                ],
                "suggestions": [
                    "Include case studies or testimonials from businesses that have benefited from accessibility improvements.",
                    "Add a section detailing how each feature specifically improves the experience for users with different abilities."
                ]
            },
            "empathy": {
                "score": 8.7,
                "strengths": [
                    f"Understanding of user challenges related to {keywords[2] if len(keywords) > 2 else 'the topic'}.",
                    "Inclusive language throughout the post.",
                    "Creates an emotional connection with the reader."
                ],
                "weaknesses": [
                    "Could include more personal stories or user perspectives.",
                    "The tone could be more supportive in some sections."
                ],
                "suggestions": [
                    "Include testimonials that highlight the impact on real users.",
                    "Acknowledge potential challenges and provide reassurance or solutions."
                ]
            }
        }
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing blog content: {e}")
        return {
            "overall_score": 7.0,
            "structure": {"score": 7.0, "strengths": [], "weaknesses": [], "suggestions": []},
            "accessibility": {"score": 7.0, "strengths": [], "weaknesses": [], "suggestions": []},
            "empathy": {"score": 7.0, "strengths": [], "weaknesses": [], "suggestions": []}
        }

async def generate_post_automatically() -> Optional[BlogPost]:
    """Generate a blog post using all agents with detailed process visibility and user interaction"""
    try:
        # Set generation in progress flag
        st.session_state.generation_in_progress = True
        
        # Start cost tracking thread
        st.session_state.generation_started = True
        start_cost_tracker()
        
        # Import the agent orchestrator
        try:
            from src.agents.agent_orchestrator import generate_blog_post, AgentOrchestrator
        except ImportError:
            st.error("Could not import agent orchestrator. Some functionality may be limited.")
            return None
        
        # Create main container for process visibility
        process_container = st.container()
        with process_container:
            st.subheader("🤖 Agent Collaboration Panel")
            st.write("Watch as our AI agents work together to create your blog post. You can interact with them at key points.")
            
            # Create columns for agent activity and output
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### 🔄 Active Agents")
                active_agent = st.empty()
                agent_status = st.empty()
                
                # Add agent control panel during generation
                st.markdown("#### 🎮 Agent Control Panel")
                control_cols = st.columns(2)
                
                with control_cols[0]:
                    pause_button = st.button(
                        "⏸️ Pause Generation", 
                        key="pause_generation",
                        disabled=st.session_state.is_generation_paused,
                        help="Pause the blog generation process to provide feedback"
                    )
                    if pause_button:
                        st.session_state.is_generation_paused = True
                        st.rerun()
                
                with control_cols[1]:
                    resume_button = st.button(
                        "▶️ Resume Generation", 
                        key="resume_generation",
                        disabled=not st.session_state.is_generation_paused,
                        help="Resume the blog generation process after providing feedback"
                    )
                    if resume_button:
                        st.session_state.is_generation_paused = False
                        st.rerun()
                
                # Show pause status
                if st.session_state.is_generation_paused:
                    st.warning("Generation paused. Please provide feedback and resume when ready.")
                
                # Show Perplexity status
                st.markdown("#### 🔍 Perplexity Research")
                st.info(f"Status: {st.session_state.perplexity_status}")
            
            with col2:
                st.markdown("#### 📝 Agent Output")
                agent_output = st.empty()
                agent_thinking = st.empty()
                
                # Add feedback section when paused
                if st.session_state.is_generation_paused:
                    st.markdown("#### ✏️ Provide Feedback")
                    feedback = st.text_area(
                        "What would you like to change or improve?",
                        placeholder="Example: Add more statistics, focus more on B2B applications, etc."
                    )
                    
                    if st.button("Submit Feedback", type="primary"):
                        if feedback:
                            if 'agent_feedback' not in st.session_state:
                                st.session_state.agent_feedback = []
                            
                            # Store feedback with timestamp
                            st.session_state.agent_feedback.append({
                                "timestamp": time.time(),
                                "content": feedback,
                                "agent": st.session_state.current_agent
                            })
                            
                            st.success("Feedback submitted! You can now resume generation.")
        
        # Step 1: Load context data
        st.session_state.current_agent = "Context Agent"
        st.session_state.agent_status["Context Agent"] = "Active"
        active_agent.markdown("**📚 Context Agent**")
        agent_status.info("Loading business context data...")
        agent_thinking.markdown("*Thinking: What industry and goals should I focus on for this content?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "context_analysis", 500, 200)
        
        # Check for pause
        if st.session_state.is_generation_paused:
            while st.session_state.is_generation_paused:
                time.sleep(0.5)  # Wait until unpaused
        
        # Start Perplexity research in the background
        perplexity_task = asyncio.create_task(run_perplexity_research("digital accessibility"))
        st.session_state.concurrent_tasks.append(perplexity_task)
        
        context = await load_preloaded_context()
        business_type = context.get('business_type', 'Technology')
        content_goals = context.get('content_goals', ['Educate'])
        
        time.sleep(1)  # Simulate agent thinking
        agent_output.success(f"I've analyzed your business profile. We'll create content for the **{business_type}** industry with a focus on **{', '.join(content_goals)}** goals.")
        
        # Get keyword from context files using the context keyword manager
        try:
            from src.utils.context_keyword_manager import get_initial_keyword
            
            # Get a relevant keyword from context files
            keyword = context.get('main_keyword', get_initial_keyword())
        except ImportError:
            # Fallback if module not available
            keyword = "digital accessibility"
            
        st.session_state.research_keyword = keyword  # Store for later use
        
        # Allow user to modify the keyword
        with st.expander("✏️ Refine Your Topic", expanded=True):
            st.write("Would you like to refine the main topic before we continue?")
            new_keyword = st.text_input("Main Keyword/Topic", value=keyword)
            if new_keyword and new_keyword != keyword:
                keyword = new_keyword
                st.success(f"Topic updated to: {keyword}")
        
        # Step 2: Research phase
        st.session_state.current_agent = "Research Agent"
        st.session_state.agent_status["Context Agent"] = "Completed"
        st.session_state.agent_status["Research Agent"] = "Active"
        active_agent.markdown("**🔍 Research Agent**")
        agent_status.info(f"Researching {keyword}...")
        agent_thinking.markdown("*Thinking: What are the latest trends, statistics, and expert opinions on this topic?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "research", 1000, 1500)
        
        # Check for pause
        if st.session_state.is_generation_paused:
            while st.session_state.is_generation_paused:
                time.sleep(0.5)  # Wait until unpaused
        
        research_progress = st.progress(0)
        for i in range(101):
            research_progress.progress(i)
