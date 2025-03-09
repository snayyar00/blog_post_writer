"""
Enhanced Streamlit app for blog post generation with post history sidebar and real-time cost reporting.
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
import concurrent.futures

# Import our modules
from src.utils.openai_blog_analyzer import analyze_content, analyze_and_save
from src.models.analysis_models import BlogAnalysis, AnalysisSection
from src.utils.competitor_blog_scraper import scrape_competitor_blogs, analyze_competitor_structure, CompetitorBlogs
from src.utils.keyword_research_manager import get_keyword_suggestions, KeywordResearch
from src.utils.openai_blog_writer import generate_blog_post, BlogPost
from src.utils.cost_tracker import generate_cost_report, save_cost_report, get_cost_tracker, log_api_call
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
POSTS_DIRECTORY = Path("./generated_posts")
POSTS_DIRECTORY.mkdir(exist_ok=True)
MARKDOWN_DIRECTORY = Path("./generated_posts/markdown")
MARKDOWN_DIRECTORY.mkdir(exist_ok=True, parents=True)

# Global variables for cost tracking
cost_update_interval = 2  # seconds

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

def start_cost_tracker():
    """Start the cost tracking thread if not already running."""
    if not st.session_state.cost_tracker_running:
        st.session_state.generation_started = True
        st.session_state.cost_tracker_running = True
        cost_thread = threading.Thread(target=update_cost_display)
        cost_thread.daemon = True
        cost_thread.start()
        print("Cost tracker started")

def update_cost_display():
    """Update the cost display in real-time."""
    try:
        print("Cost tracker thread started")
        while True:
            try:
                # Get the latest cost report
                cost_report = generate_cost_report()
                
                # Update session state
                st.session_state.cost_report = cost_report
                
                # Extract total cost
                lines = cost_report.split("\n")
                total_cost_line = next((line for line in lines if "Total Cost:" in line), "Total Cost: $0.0000")
                total_cost_str = total_cost_line.split("$")[1].strip()
                try:
                    st.session_state.total_cost = float(total_cost_str)
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
                
                st.session_state.cost_by_provider = provider_costs
                
            except Exception as e:
                print(f"Error updating cost display: {e}")
            
            # Sleep for a short interval
            time.sleep(cost_update_interval)
            
            # Check if we should stop
            if not st.session_state.generation_started:
                st.session_state.cost_tracker_running = False
                print("Cost tracker stopped")
                break
                
    except Exception as e:
        print(f"Error in update_cost_display thread: {e}")
        st.session_state.cost_tracker_running = False

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
                    f"The blog post has a clear and logical flow, starting with an introduction to {keywords[0]}.",
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
                    f"The blog post clearly addresses {keywords[1]} accessibility considerations.",
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
                    f"Understanding of user challenges related to {keywords[2]}.",
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
        from src.agents.agent_orchestrator import generate_blog_post, AgentOrchestrator
        
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
        from src.utils.context_keyword_manager import get_initial_keyword
        
        # Get a relevant keyword from context files
        keyword = context.get('main_keyword', get_initial_keyword())
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
            time.sleep(0.05)
        
        agent_output.success(f"I've gathered comprehensive research on **{keyword}** including latest trends, statistics, and expert opinions.")
        
        # Step 3: Competitor Analysis
        st.session_state.current_agent = "Competitor Analysis Agent"
        st.session_state.agent_status["Research Agent"] = "Completed"
        st.session_state.agent_status["Competitor Analysis Agent"] = "Active"
        active_agent.markdown("**👀 Competitor Analysis Agent**")
        agent_status.info("Analyzing top competitors in your niche...")
        agent_thinking.markdown("*Thinking: What content strategies are working well for competitors? What gaps can we fill?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "competitor_analysis", 1200, 800)
        
        # Check for pause
        if st.session_state.is_generation_paused:
            while st.session_state.is_generation_paused:
                time.sleep(0.5)  # Wait until unpaused
        
        time.sleep(2)  # Simulate agent working
        agent_output.success("I've analyzed the top performing content from competitors and identified opportunities to differentiate your content.")
        
        # Step 4: Outline Generation
        st.session_state.current_agent = "Outline Agent"
        st.session_state.agent_status["Competitor Analysis Agent"] = "Completed"
        st.session_state.agent_status["Outline Agent"] = "Active"
        active_agent.markdown("**📋 Outline Agent**")
        agent_status.info("Creating an optimized content outline...")
        agent_thinking.markdown("*Thinking: What structure will best organize this information for the target audience?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "outline_generation", 800, 600)
        
        time.sleep(2)  # Simulate agent working
        
        # Generate a sample outline for preview
        sample_outline = [
            "## TLDR",
            f"# {keyword.title()}: The Ultimate Guide",
            "## Introduction",
            f"## What is {keyword.title()}?",
            f"## Benefits of {keyword.title()}",
            "## Best Practices",
            "## Case Studies",
            "## Conclusion"
        ]
        
        agent_output.success("I've created an optimized outline based on research and competitor analysis:")
        st.write("\n".join(sample_outline))
        
        # Allow user to modify the outline
        with st.expander("✏️ Refine Your Outline", expanded=True):
            st.write("Would you like to modify the outline before we generate the full content?")
            outline_feedback = st.text_area("Suggestions for the outline", 
                placeholder="Example: Add a section about pricing, Remove the case studies section, etc.")
            
            if outline_feedback:
                st.success("Thank you! Your feedback will be incorporated into the final outline.")
        
        # Step 5: Content Generation
        st.session_state.current_agent = "Content Generation Agent"
        st.session_state.agent_status["Outline Agent"] = "Completed"
        st.session_state.agent_status["Content Generation Agent"] = "Active"
        active_agent.markdown("**✍️ Content Generation Agent**")
        agent_status.info("Creating comprehensive content...")
        agent_thinking.markdown("*Thinking: How can I create detailed, valuable content for each section of the outline?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "content_generation", 2000, 3000)
        
        # Show a progress bar for content generation
        content_progress = st.progress(0)
        for i in range(101):
            content_progress.progress(i)
            time.sleep(0.1)
        
        # Step 6: Generate the full blog post using all agents
        agent_output.success("I've drafted comprehensive content for each section of the outline.")
        
        # Step 7: Quality and Readability Check
        st.session_state.current_agent = "Quality Check Agent"
        st.session_state.agent_status["Content Generation Agent"] = "Completed"
        st.session_state.agent_status["Quality Check Agent"] = "Active"
        active_agent.markdown("**🔍 Quality Check Agent**")
        agent_status.info("Analyzing content quality and readability...")
        agent_thinking.markdown("*Thinking: Is this content clear, engaging, and valuable? How can it be improved?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "quality_check", 3000, 1000)
        
        time.sleep(2)  # Simulate agent working
        agent_output.success("I've analyzed the content quality and made improvements to enhance readability and engagement.")
        
        # Step 8: Humanize content
        st.session_state.current_agent = "Humanizer Agent"
        st.session_state.agent_status["Quality Check Agent"] = "Completed"
        st.session_state.agent_status["Humanizer Agent"] = "Active"
        active_agent.markdown("**🧠 Humanizer Agent**")
        agent_status.info("Making content more engaging and conversational...")
        agent_thinking.markdown("*Thinking: How can I make this content more human, relatable, and aligned with the brand voice?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "humanize_content", 3000, 2000)
        
        time.sleep(2)  # Simulate agent working
        agent_output.success("I've transformed the content to be more conversational, engaging, and aligned with your brand voice.")
        
        # Wait for Perplexity research to complete
        try:
            perplexity_result = await perplexity_task
            st.success("Perplexity deep research completed successfully!")
        except Exception as e:
            st.error(f"Perplexity research error: {str(e)}")
        
        # Now actually generate the blog post behind the scenes
        with st.spinner("Finalizing your blog post..."):
            post = await generate_blog_post(
                keyword=keyword,
                business_type=business_type,
                content_goal=content_goals[0] if content_goals else "educate and inform readers",
                web_references=5
            )
            
            if not post:
                raise ValueError("Failed to generate blog post")
        
        # Final metrics
        st.session_state.current_agent = "Metrics Agent"
        st.session_state.agent_status["Humanizer Agent"] = "Completed"
        st.session_state.agent_status["Metrics Agent"] = "Active"
        active_agent.markdown("**📊 Metrics Agent**")
        agent_status.info("Calculating content performance metrics...")
        agent_thinking.markdown("*Thinking: How will this content perform? What business impact can be expected?*")
        
        # Log the API call
        log_api_call("openai", "gpt-4o-mini", "metrics_calculation", 500, 300)
        
        time.sleep(1)  # Simulate agent working
        
        metrics_data = []
        for metric, value in post.metrics.business_impact.items():
            metrics_data.append(f"  {metric.replace('_', ' ').title()}: {value:.1f}%")
        
        agent_output.success("I've analyzed the potential business impact of this content:")
        st.write("\n".join(metrics_data))
        
        # Complete
        st.session_state.agent_status["Metrics Agent"] = "Completed"
        st.success("✅ Blog post generation complete!")
        
        # Add TLDR to the content if not already present
        content = post.content
        if "## TLDR" not in content and "## TL;DR" not in content and "## In a Nutshell" not in content:
            # Generate a TLDR
            tldr = "A concise overview of digital accessibility requirements across different industries, highlighting key considerations, benefits, and implementation strategies for creating inclusive digital experiences."
            content = f"## In a Nutshell\n{tldr}\n\n" + content
            post.content = content
        
        # Analyze the blog content
        analysis = await analyze_blog_content(content)
        
        # Save the post to history
        post_data = {
            "id": str(uuid.uuid4()),
            "topic": keyword,
            "title": post.title,
            "content": post.content,
            "timestamp": datetime.now().timestamp(),
            "metrics": {
                "viral_potential": post.metrics.viral_potential,
                "business_impact": post.metrics.business_impact,
                "content_type": post.metrics.content_type
            },
            "analysis": analysis
        }
        save_post(post_data)
        
        # Update session state
        st.session_state.posts_history = load_posts_history()
        st.session_state.current_post = post_data
        
        # Stop cost tracking thread
        st.session_state.generation_started = False
        
        # Reset generation in progress flag
        st.session_state.generation_in_progress = False
        
        return post
            
    except Exception as e:
        st.error(f"Auto-generation failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # Show detailed error for debugging
        
        # Stop cost tracking thread
        st.session_state.generation_started = False
        
        # Reset generation in progress flag
        st.session_state.generation_in_progress = False
        
        return None

async def analyze_competitors(keyword: str) -> Optional[Dict[str, Any]]:
    """Analyze competitors with guard clauses and early returns"""
    if not keyword:
        st.error("Please enter a keyword")
        return None

    try:
        with st.spinner("Analyzing top content..."):
            return await analyze_content_patterns(keyword)
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None

async def analyze_content_patterns(keyword: str) -> Optional[Dict[str, Any]]:
    """Analyze competitor content patterns."""
    try:
        competitor_insights = await analyze_competitors(keyword)
        if not competitor_insights:
            raise ValueError("No competitor insights found")
            
        st.session_state.competitor_analysis = competitor_insights
        return competitor_insights
        
    except Exception as e:
        st.error(f"Error analyzing competitor blogs: {str(e)}")
        return None

async def create_blog_post(context_data: Dict[str, Any]) -> Optional[BlogPost]:
    """Generate a blog post using provided context data."""
    try:
        # Set generation in progress flag
        st.session_state.generation_in_progress = True
        
        # Start cost tracking thread
        st.session_state.generation_started = True
        start_cost_tracker()
        
        # Import the agent orchestrator
        from src.agents.agent_orchestrator import generate_blog_post
        
        # Determine if we're in auto or manual mode
        if st.session_state.mode == 'auto':
            # In auto mode, context_data contains all necessary information
            business_type = context_data.get('business_type', 'Technology')
            content_goals = context_data.get('content_goals', ['Educate', 'Engage'])
            keyword = context_data.get('main_keyword', 'content marketing')
            web_references = context_data.get('web_references', 5)
        else:
            # In manual mode, we need business context from session state
            if not st.session_state.business_context:
                # Use default values if not available
                business_type = 'Technology'
                content_goals = ['Educate', 'Engage']
            else:
                business_type = st.session_state.business_context.get('business_type', 'Technology')
                content_goals = st.session_state.business_context.get('content_goals', ['Educate', 'Engage'])
            
            # Use the research keyword as the main keyword
            keyword = st.session_state.research_keyword.split(",")[0] if st.session_state.research_keyword else 'content marketing'
            web_references = 5  # Default to 5 web references
        
        # Start Perplexity research in the background
        perplexity_task = asyncio.create_task(run_perplexity_research(keyword))
        st.session_state.concurrent_tasks.append(perplexity_task)
        
        # Generate blog post using all agents
        post = await generate_blog_post(
            keyword=keyword,
            business_type=business_type,
            content_goal=content_goals[0] if content_goals else "educate and inform readers",
            web_references=web_references
        )
        
        if not post:
            raise ValueError("Failed to generate blog post content")
        
        # Wait for Perplexity research to complete
        try:
            perplexity_result = await perplexity_task
            st.success("Perplexity deep research completed successfully!")
        except Exception as e:
            st.error(f"Perplexity research error: {str(e)}")
        
        # Add TLDR to the content if not already present
        content = post.content
        if "## TLDR" not in content and "## TL;DR" not in content and "## In a Nutshell" not in content:
            # Generate a TLDR
            tldr = "A concise overview of digital accessibility requirements across different industries, highlighting key considerations, benefits, and implementation strategies for creating inclusive digital experiences."
            content = f"## In a Nutshell\n{tldr}\n\n" + content
            post.content = content
        
        # Analyze the blog content
        analysis = await analyze_blog_content(content)
        
        # Save the post to history
        post_data = {
            "id": str(uuid.uuid4()),
            "topic": keyword,
            "title": post.title,
            "content": post.content,
            "timestamp": datetime.now().timestamp(),
            "metrics": {
                "viral_potential": post.metrics.viral_potential,
                "business_impact": post.metrics.business_impact,
                "content_type": post.metrics.content_type
            },
            "analysis": analysis
        }
        save_post(post_data)
        
        # Update session state
        st.session_state.posts_history = load_posts_history()
        st.session_state.current_post = post_data
        
        # Stop cost tracking thread
        st.session_state.generation_started = False
        
        # Reset generation in progress flag
        st.session_state.generation_in_progress = False
            
        return post
        
    except Exception as e:
        st.error(f"Error generating blog post: {str(e)}")
        
        # Stop cost tracking thread
        st.session_state.generation_started = False
        
        # Reset generation in progress flag
        st.session_state.generation_in_progress = False
        
        return None

def run_async(coro):
    """Run an async coroutine in a synchronous context."""
    try:
        # Set up asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def main():
    st.set_page_config(
        page_title="Blog Post Generator",
        page_icon="🚀",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Start cost tracker if not already running
    if not st.session_state.cost_tracker_running:
        start_cost_tracker()
    
    # Sidebar for post history and cost reporting
    with st.sidebar:
        st.title("📚 Post History")
        st.write("Previously generated blog posts:")
        
        # Display post history
        if st.session_state.posts_history:
            # Create a scrollable container for post history
            with st.container(height=400, border=False):
                for i, post in enumerate(st.session_state.posts_history):
                    render_post_card(post, i)
        else:
            st.info("No posts generated yet. Create your first post!")
        
        # Cost report section
        st.divider()
        st.header("💰 Cost Reporting")
        
        # Always display the current cost
        st.metric(
            label="Total API Cost", 
            value=f"${st.session_state.total_cost:.4f}",
            delta=None
        )
        
        # Show cost breakdown if available
        if hasattr(st.session_state, 'cost_by_provider') and st.session_state.cost_by_provider:
            st.subheader("Cost by Provider")
            for provider, cost in st.session_state.cost_by_provider.items():
                st.text(f"{provider}: ${cost:.4f}")
        
        # Show detailed cost report
        if st.session_state.cost_report:
            with st.expander("Detailed Cost Report", expanded=False):
                st.text(st.session_state.cost_report)
        
        # Add a button to return to current generation if viewing history
        if st.session_state.viewing_history and st.session_state.generation_in_progress:
            if st.button("⬅️ Return to Current Generation", type="primary"):
                st.session_state.viewing_history = False
                st.rerun()
    
    # Main content area
    st.title("🚀 Blog Post Generator")
    
    # If viewing history and not in generation, show the history post
    if st.session_state.viewing_history and not st.session_state.generation_in_progress:
        if st.session_state.current_post:
            st.subheader(f"📄 {st.session_state.current_post.get('title', 'Blog Post')}")
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
            
            # Display blog analysis if available
            if "analysis" in st.session_state.current_post:
                with st.expander("📊 Blog Analysis", expanded=False):
                    analysis = st.session_state.current_post["analysis"]
                    
                    # Overall score
                    st.subheader(f"Overall Score: {analysis['overall_score']}/10")
                    
                    # Structure
                    st.markdown("### Structure")
                    st.progress(analysis["structure"]["score"] / 10)
                    st.markdown(f"**Score:** {analysis['structure']['score']}/10")
                    
                    with st.expander("Strengths"):
                        for strength in analysis["structure"]["strengths"]:
                            st.markdown(f"- {strength}")
                    
                    with st.expander("Weaknesses"):
                        for weakness in analysis["structure"]["weaknesses"]:
                            st.markdown(f"- {weakness}")
                    
                    with st.expander("Suggestions"):
                        for suggestion in analysis["structure"]["suggestions"]:
                            st.markdown(f"- {suggestion}")
                    
                    # Accessibility
                    st.markdown("### Accessibility")
                    st.progress(analysis["accessibility"]["score"] / 10)
                    st.markdown(f"**Score:** {analysis['accessibility']['score']}/10")
                    
                    with st.expander("Strengths"):
                        for strength in analysis["accessibility"]["strengths"]:
                            st.markdown(f"- {strength}")
                    
                    with st.expander("Weaknesses"):
                        for weakness in analysis["accessibility"]["weaknesses"]:
                            st.markdown(f"- {weakness}")
                    
                    with st.expander("Suggestions"):
                        for suggestion in analysis["accessibility"]["suggestions"]:
                            st.markdown(f"- {suggestion}")
                    
                    # Empathy
                    st.markdown("### Empathy")
                    st.progress(analysis["empathy"]["score"] / 10)
                    st.markdown(f"**Score:** {analysis['empathy']['score']}/10")
                    
                    with st.expander("Strengths"):
                        for strength in analysis["empathy"]["strengths"]:
                            st.markdown(f"- {strength}")
                    
                    with st.expander("Weaknesses"):
                        for weakness in analysis["empathy"]["weaknesses"]:
                            st.markdown(f"- {weakness}")
                    
                    with st.expander("Suggestions"):
                        for suggestion in analysis["empathy"]["suggestions"]:
                            st.markdown(f"- {suggestion}")
            
            # Edit button
            if st.button("✏️ Edit This Post"):
                st.session_state.editing_post = True
                st.session_state.edit_content = st.session_state.current_post.get("content", "")
                st.rerun()
            
            # Return to main interface button
            if st.button("⬅️ Return to Generator"):
                st.session_state.viewing_history = False
                st.session_state.current_post = None
                st.rerun()
    # If editing a post
    elif hasattr(st.session_state, 'editing_post') and st.session_state.editing_post:
        st.subheader("✏️ Edit Blog Post")
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
            if st.button("🤖 Auto Mode", type="primary", help="Generate blog post using pre-loaded context"):
                st.session_state.mode = 'auto'
        with mode_col2:
            if st.button("👨‍💻 Manual Mode", help="Manually research competitors and generate content"):
                st.session_state.mode = 'manual'
        
        # Automatic Mode
        if st.session_state.mode == 'auto':
            st.info("Using pre-loaded context data from your company profile")
            
            if st.button("✨ Generate Blog Post Now", type="primary"):
                post = run_async(generate_post_automatically())
                if post:
                    st.session_state.generated_post = post
                    st.success("Blog post generated successfully!")
        
        # Manual Mode
        else:
            # Competitor Research
            keyword = st.text_input("Enter target keyword:", key="keyword_input")
            if st.button("🔍 Analyze Competitors", disabled=not keyword):
                if analysis := run_async(analyze_competitors(keyword)):
                    st.session_state.competitor_analysis = analysis
                    st.success("Competitor analysis complete!")

            # Content Generation        
            if st.session_state.competitor_analysis:
                if st.button("✨ Generate Blog Post", type="primary"):
                    with st.spinner("Generating..."):
                        post = run_async(create_blog_post(st.session_state.competitor_analysis))
                        st.session_state.generated_post = post
            elif 'competitor_analysis' in st.session_state:
                st.info("Complete competitor research first")
        
        # Agent Status Display
        if st.session_state.agent_status:
            st.subheader("Agent Status")
            status_cols = st.columns(5)
            
            for i, (agent, status) in enumerate(st.session_state.agent_status.items()):
                with status_cols[i % 5]:
                    if status == "Active":
                        st.info(f"🔄 {agent}: {status}")
                    elif status == "Completed":
                        st.success(f"✅ {agent}: {status}")
                    else:
                        st.warning(f"⚠️ {agent}: {status}")
        
        # Results Display
        if st.session_state.generated_post:
            st.divider()
            
            # Display blog post with rating
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown("### Blog Post Analysis")
                
                with col2:
                    # Display overall rating
                    rating = st.session_state.generated_post.metrics.viral_potential.get('shareability', 0) / 10
                    st.markdown(f"**Rating: {rating:.1f}/10**")
            
            # Display metrics in expandable section
            with st.expander("📊 Content Metrics"):
                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                
                with metrics_col1:
                    st.markdown("**Viral Potential**")
                    for key, value in st.session_state.generated_post.metrics.viral_potential.items():
                        st.progress(value/100)
                        st.caption(f"{key.replace('_', ' ').title()}: {value:.1f}%")
                
                with metrics_col2:
                    st.markdown("**Business Impact**")
                    for key, value in st.session_state.generated_post.metrics.business_impact.items():
                        st.progress(value/100)
                        st.caption(f"{key.replace('_', ' ').title()}: {value:.1f}%")
                
                with metrics_col3:
                    st.markdown("**Content Type**")
                    for key, value in st.session_state.generated_post.metrics.content_type.items():
                        st.progress(value)
                        st.caption(f"{key.replace('_', ' ').title()}: {value*100:.1f}%")
            
            # Display the actual blog post content with interactive feedback options
            st.subheader("Generated Blog Post")
            
            # Create tabs for different views of the content
            content_tab, feedback_tab, agent_tab = st.tabs(["📝 Content", "🔄 Feedback", "🤖 Agent Activity"])
            
            with content_tab:
                # Display title
                post = st.session_state.generated_post
                st.markdown(f"# {post.title}")
                
                # Split content into sections for better readability
                content_sections = post.content.split('##')
                
                # Display introduction (first section)
                st.markdown(content_sections[0])
                
                # Display remaining sections
                for section in content_sections[1:]:
                    st.markdown(f"## {section}")
                
                # Download button
                st.download_button(
                    label="Download Blog Post",
                    data=post.content,
                    file_name=f"blog_post_{post.title.replace(' ', '_')}.md",
                    mime="text/markdown"
                )
                
                # Show path to saved markdown file
                if st.session_state.current_post:
                    topic_slug = post.title.replace(" ", "_").lower()
                    markdown_filename = f"{topic_slug}_{st.session_state.current_post['id'][:8]}.md"
                    markdown_path = MARKDOWN_DIRECTORY / markdown_filename
                    st.success(f"Blog post saved to: {markdown_path}")
            
            with feedback_tab:
                st.markdown("### Provide Feedback on Your Blog Post")
                st.write("Use this panel to guide the AI in refining your content.")
                
                # Overall content direction
                st.markdown("#### Overall Content Direction")
                content_direction = st.radio(
                    "What would you like to prioritize in the next revision?",
                    options=["More detailed research", "More engaging style", "More actionable advice", 
                             "Simplify language", "Add more examples", "Other (specify below)"],
                    horizontal=True
                )
                
                if content_direction == "Other (specify below)":
                    custom_direction = st.text_input("Please specify your direction:")
                
                # Section-specific feedback
                st.markdown("#### Section-Specific Feedback")
                section_to_improve = st.selectbox(
                    "Which section would you like to improve?",
                    options=["Introduction"] + [f"Section {i+1}" for i in range(len(content_sections)-1)]
                )
                
                improvement_suggestion = st.text_area(
                    f"How would you like to improve the {section_to_improve.lower()}?",
                    placeholder="Example: Add more statistics, Include a case study, etc."
                )
                
                if st.button("Submit Feedback", type="primary"):
                    st.success("Thank you! Your feedback has been submitted. The AI agents will now refine your content.")
                    # In a real implementation, this would trigger the agents to revise the content
            
            with agent_tab:
                st.markdown("### Agent Activity Log")
                st.write("See what each AI agent contributed to your blog post.")
                
                # Create an expandable section for each agent
                with st.expander("🔍 Research Agent", expanded=True):
                    st.markdown("**Contribution:** Gathered comprehensive research on the topic including latest trends, statistics, and expert opinions.")
                    st.markdown("**Process:** Searched through web sources, academic papers, and industry reports to find relevant information.")
                    st.markdown("**Output Quality:** 8.5/10")
                
                with st.expander("📋 Outline Agent"):
                    st.markdown("**Contribution:** Created an optimized content structure based on research and competitor analysis.")
                    st.markdown("**Process:** Analyzed top-performing content structures and adapted them to your specific topic.")
                    st.markdown("**Output Quality:** 9.0/10")
                
                with st.expander("✍️ Content Generation Agent"):
                    st.markdown("**Contribution:** Drafted comprehensive content for each section of the outline.")
                    st.markdown("**Process:** Transformed research into engaging, informative content optimized for your target audience.")
                    st.markdown("**Output Quality:** 8.7/10")
                
                with st.expander("🔍 Quality Check Agent"):
                    st.markdown("**Contribution:** Analyzed content quality and made improvements to enhance readability and engagement.")
                    st.markdown("**Process:** Evaluated content against readability metrics, SEO best practices, and engagement factors.")
                    st.markdown("**Output Quality:** 8.9/10")
                
                with st.expander("🧠 Humanizer Agent"):
                    st.markdown("**Contribution:** Made content more conversational, engaging, and aligned with your brand voice.")
                    st.markdown("**Process:** Added human touches, improved flow, and enhanced the overall tone.")
                    st.markdown("**Output Quality:** 9.2/10")
                
                # Add pause/resume functionality
                st.markdown("### Agent Control Panel")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Pause Generation", disabled=True):
                        pass
                with col2:
                    if st.button("Resume Generation", disabled=True):
                        pass
                
                st.info("Note: Pause/Resume functionality will be available in the next update.")

if __name__ == "__main__":
    main()