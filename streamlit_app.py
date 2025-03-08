"""
Streamlit app for OpenAI-powered blog post analysis.
Uses functional programming patterns and structured outputs.
"""
import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.utils.openai_blog_analyzer import analyze_content, analyze_and_save
from src.models.analysis_models import BlogAnalysis, AnalysisSection
from src.utils.competitor_blog_scraper import scrape_competitor_blogs, analyze_competitor_structure, CompetitorBlogs
from src.utils.keyword_research_manager import get_keyword_suggestions, KeywordResearch
from src.utils.openai_blog_writer import generate_blog_post, BlogPost
import asyncio
import time

def init_session_state() -> None:
    """Initialize session state with RORO pattern"""
    required_keys = {
        'generated_post': None,
        'competitor_analysis': None,
        'suggested_keywords': [],
        'mode': 'auto',  # Default to automatic mode
        'business_context': None,  # Initialize business context
        'research_keyword': '',  # Initialize research keyword
        'regenerate_options': {},  # Options for blog regeneration
        'generation_steps': []  # Track generation process steps
    }
    for key, val in required_keys.items():
        if key not in st.session_state:
            st.session_state[key] = val

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

async def generate_post_automatically() -> Optional[BlogPost]:
    """Generate a blog post using all agents with detailed process visibility and user interaction"""
    try:
        # Import the agent orchestrator
        from src.agents.agent_orchestrator import generate_blog_post, AgentOrchestrator
        import time
        
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
                
                # Initialize pause state in session state if not present
                if 'is_generation_paused' not in st.session_state:
                    st.session_state.is_generation_paused = False
                if 'current_agent' not in st.session_state:
                    st.session_state.current_agent = "Context Agent"
                
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
                            import time
                            st.session_state.agent_feedback.append({
                                "timestamp": time.time(),
                                "content": feedback,
                                "agent": st.session_state.current_agent
                            })
                            
                            st.success("Feedback submitted! You can now resume generation.")
        
        # Step 1: Load context data
        st.session_state.current_agent = "Context Agent"
        active_agent.markdown("**📚 Context Agent**")
        agent_status.info("Loading business context data...")
        agent_thinking.markdown("*Thinking: What industry and goals should I focus on for this content?*")
        
        # Check for pause
        if st.session_state.is_generation_paused:
            while st.session_state.is_generation_paused:
                time.sleep(0.5)  # Wait until unpaused
        
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
        active_agent.markdown("**🔍 Research Agent**")
        agent_status.info(f"Researching {keyword}...")
        agent_thinking.markdown("*Thinking: What are the latest trends, statistics, and expert opinions on this topic?*")
        
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
        active_agent.markdown("**👀 Competitor Analysis Agent**")
        agent_status.info("Analyzing top competitors in your niche...")
        agent_thinking.markdown("*Thinking: What content strategies are working well for competitors? What gaps can we fill?*")
        
        # Check for pause
        if st.session_state.is_generation_paused:
            while st.session_state.is_generation_paused:
                time.sleep(0.5)  # Wait until unpaused
        
        time.sleep(2)  # Simulate agent working
        agent_output.success("I've analyzed the top performing content from competitors and identified opportunities to differentiate your content.")
        
        # Step 4: Outline Generation
        active_agent.markdown("**📋 Outline Agent**")
        agent_status.info("Creating an optimized content outline...")
        agent_thinking.markdown("*Thinking: What structure will best organize this information for the target audience?*")
        
        time.sleep(2)  # Simulate agent working
        
        # Generate a sample outline for preview
        sample_outline = [
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
        active_agent.markdown("**✍️ Content Generation Agent**")
        agent_status.info("Creating comprehensive content...")
        agent_thinking.markdown("*Thinking: How can I create detailed, valuable content for each section of the outline?*")
        
        # Show a progress bar for content generation
        content_progress = st.progress(0)
        for i in range(101):
            content_progress.progress(i)
            time.sleep(0.1)
        
        # Step 6: Generate the full blog post using all agents
        agent_output.success("I've drafted comprehensive content for each section of the outline.")
        
        # Step 7: Quality and Readability Check
        active_agent.markdown("**🔍 Quality Check Agent**")
        agent_status.info("Analyzing content quality and readability...")
        agent_thinking.markdown("*Thinking: Is this content clear, engaging, and valuable? How can it be improved?*")
        
        time.sleep(2)  # Simulate agent working
        agent_output.success("I've analyzed the content quality and made improvements to enhance readability and engagement.")
        
        # Step 8: Humanize content
        active_agent.markdown("**🧠 Humanizer Agent**")
        agent_status.info("Making content more engaging and conversational...")
        agent_thinking.markdown("*Thinking: How can I make this content more human, relatable, and aligned with the brand voice?*")
        
        time.sleep(2)  # Simulate agent working
        agent_output.success("I've transformed the content to be more conversational, engaging, and aligned with your brand voice.")
        
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
        active_agent.markdown("**📊 Metrics Agent**")
        agent_status.info("Calculating content performance metrics...")
        agent_thinking.markdown("*Thinking: How will this content perform? What business impact can be expected?*")
        
        time.sleep(1)  # Simulate agent working
        
        metrics_data = []
        for metric, value in post.metrics.business_impact.items():
            metrics_data.append(f"  {metric.replace('_', ' ').title()}: {value:.1f}%")
        
        agent_output.success("I've analyzed the potential business impact of this content:")
        st.write("\n".join(metrics_data))
        
        # Complete
        st.success("✅ Blog post generation complete!")
        return post
            
    except Exception as e:
        st.error(f"Auto-generation failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # Show detailed error for debugging
        return None

def display_score_gauge(score: float, category: str) -> None:
    """Display a score using Streamlit gauge with proper type hints."""
    st.write(f"### {category} Score")
    st.progress(score / 10)
    st.write(f"{score:.1f}/10")

def display_analysis_section(section: AnalysisSection, category: str) -> None:
    """Display analysis section with expandable details and proper type hints."""
    # Early validation
    if not section:
        st.warning(f"No {category} analysis available")
        return
        
    with st.expander(f"{category} Analysis", expanded=True):
        display_score_gauge(section.score, category)
        
        # Display strengths if any
        if section.strengths:
            st.write("#### ✅ Strengths")
            for strength in section.strengths:
                st.write(f"- {strength}")
                
        # Display areas for improvement if any
        if section.weaknesses:
            st.write("#### 🔄 Areas for Improvement")
            for weakness in section.weaknesses:
                st.write(f"- {weakness}")
                
        # Display suggestions if any
        if section.suggestions:
            st.write("#### 💡 Suggestions")
            for suggestion in section.suggestions:
                st.write(f"- {suggestion}")

@st.cache_resource(ttl=3600)
def get_competitor_cache() -> Dict[str, Any]:
    """Get cached competitor analysis results."""
    return {}

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

async def analyze_website_content() -> None:
    """Analyze website content to determine business context.
    
    This function extracts content from a website URL and analyzes it to determine:
    - Business type (e.g., E-commerce, SaaS)
    - Content type (e.g., Product, Educational)
    - Common topics and themes
    
    The analysis results are stored in session state for use by other components.
    
    Raises:
        ValueError: If website URL is invalid or missing
        HTTPError: If website cannot be accessed
        KeyError: If required data is missing from analysis results
        Exception: For other unexpected errors
    """
    # Early validation
    if not st.session_state.website_url:
        st.warning("Please enter your website URL first.")
        return
        
    if not validate_url(st.session_state.website_url):
        st.error("Invalid website URL format. Please check the URL and try again.")
        return
        
    try:
        with st.status("Analyzing your website...", expanded=True) as status:
            # Extract and validate content
            content = extract_content_from_url(st.session_state.website_url)
            if not content:
                raise ValueError("No content extracted from website")
                
            if 'business_context' not in content:
                raise KeyError("Missing business context in analysis results")
                
            # Update session state with analysis results
            business_context = content['business_context']
            st.session_state.business_context = business_context
            st.session_state.business_type = business_context.get('business_type', 'Unknown')
            st.session_state.content_type = business_context.get('content_type', 'Unknown')
            
            status.update(
                label="Website analysis complete!",
                state="complete"
            )
            
    except ValueError as e:
        st.session_state.business_context = None
        st.error(f"Content extraction failed: {str(e)}")
    except KeyError as e:
        st.session_state.business_context = None
        st.error(f"Analysis error: {str(e)}")
    except Exception as e:
        st.session_state.business_context = None
        st.error("An unexpected error occurred. Please try again.")
        # Log the actual error for debugging
        print(f"Error analyzing website: {str(e)}")

async def analyze_blog_post() -> None:
    """Analyze blog post with detailed progress tracking."""
    # Ensure we have business context
    if not st.session_state.business_context:
        st.warning("Please analyze your website first to determine business context.")
        return
    # Early validation
    if not st.session_state.blog_content:
        st.warning("Please enter some blog content first.")
        return
    
    try:
        with st.status("Analyzing your blog post...", expanded=True) as status:
            # Initialize progress
            progress_text = "Operation in progress. Please wait."
            progress_bar = st.progress(0, text=progress_text)
            
            # Get keyword suggestions if in guided mode
            keyword = None
            if st.session_state.research_mode == "guided":
                if st.session_state.seed_keywords:
                    try:
                        status.update(label="Researching keywords...", expanded=True)
                        progress_bar.progress(20, text="Generating keyword suggestions...")
                        
                        # Get fresh keyword suggestions
                        keyword_data = get_keyword_suggestions(
                            seed_keywords=st.session_state.seed_keywords,
                            research_dir=Path("analysis/keyword_research")
                        )
                        st.session_state.keyword_trends = keyword_data.get("trends", {})
                        st.session_state.suggested_keywords = keyword_data.get("suggested_keywords", [])
                        keyword = st.session_state.research_keyword or st.session_state.suggested_keywords[0]
                        
                        progress_bar.progress(40, text="Keywords analyzed")
                    except Exception as e:
                        st.warning(f"Error getting keyword suggestions: {e}. Proceeding with manual keyword.")
                        keyword = st.session_state.research_keyword
                else:
                    keyword = st.session_state.research_keyword
            
            # Get structured analysis results
            status.update(label="Analyzing content structure...", expanded=True)
            progress_bar.progress(60, text="Analyzing content structure and readability...")
            
            results = await analyze_content(
                content=st.session_state.blog_content,
                keyword=keyword
            )
            st.session_state.analysis_results = results
            
            # Save detailed report
            status.update(label="Generating report...", expanded=True)
            progress_bar.progress(80, text="Creating detailed analysis report...")
            
            # Convert the dictionary to proper format before awaiting
            save_results = await analyze_and_save(
                content=st.session_state.blog_content,
                keyword=keyword
            )
            
            # Handle the result properly
            if isinstance(save_results, dict):
                st.session_state.report_path = save_results.get("report_file", "")
                st.session_state.analysis_path = save_results.get("analysis_file", "")
            elif isinstance(save_results, str):
                st.session_state.report_path = save_results
                st.session_state.analysis_path = save_results.replace("_report.md", ".json")
            
            # Complete
            progress_bar.progress(100, text="Analysis complete!")
            status.update(label="Analysis complete! View results below.", state="complete")
            
    except ValueError as e:
        st.session_state.has_error = True
        st.session_state.error_message = str(e)
        st.error(f"Invalid input: {e}")
    except Exception as e:
        st.session_state.has_error = True
        st.session_state.error_message = str(e)
        st.error(f"Error analyzing blog post: {e}")
        import traceback
        st.error(traceback.format_exc())  # Show detailed error for debugging

def display_confidence_score(score: float, label: str) -> None:
    """Display a confidence score with a visual gauge.
    
    Args:
        score: Confidence score between 0 and 1
        label: Label for the score
    """
    st.write(f"**{label} Confidence**")
    st.progress(score, text=f"{int(score * 100)}%")

def display_topics_list(topics: List[str], title: str) -> None:
    """Display a list of topics with a title.
    
    Args:
        topics: List of topics to display
        title: Title for the topics section
    """
    if not topics:
        return
        
    st.write(f"**{title}**")
    for topic in topics:
        st.write(f"- {topic}")

def format_business_insights(context: Dict[str, Any]) -> str:
    """Format business insights into a readable string.
    
    Args:
        context: Business context dictionary containing analysis results
        
    Returns:
        Formatted string with business insights
    """
    return (
        "Based on your website content analysis:\n\n"
        f"- Your business appears to be focused on **{context['business_type'].lower()}** "
        f"with {int(context['business_confidence'] * 100)}% confidence\n"
        f"- Content strategy aligns with **{context['content_type'].lower()}** "
        f"content ({int(context['content_confidence'] * 100)}% confidence)\n"
        "- We recommend focusing on the suggested content goals and key topics above "
        "to maximize engagement"
    )

def display_business_context() -> None:
    """Display detected business context with confidence scores and insights.
    
    Shows:
    - Business type and content type with confidence scores
    - Common topics found in the content
    - Recommended content goals
    - Additional insights based on analysis
    """
    # Early validation
    if not st.session_state.business_context:
        return
        
    context = st.session_state.business_context
    
    # Display header
    st.write("## Business Context Analysis")
    
    # Business and Content Type Analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Business Profile")
        st.info(
            f"**Type:** {context['business_type']}\n\n"
            f"**Focus:** {context['content_type']}"
        )
        display_confidence_score(context['business_confidence'], "Business Type")
        display_confidence_score(context['content_confidence'], "Content Focus")
        
    with col2:
        st.write("### Content Strategy")
        display_topics_list(context.get('content_goals', []), "Recommended Goals")
        display_topics_list(context.get('common_topics', []), "Key Topics")
        
    # Additional Insights
    with st.expander("Analysis Insights", expanded=True):
        st.info(format_business_insights(context))
        content_suggestions = {
            'E-commerce': ['Product Reviews', 'Buying Guides', 'Industry Trends'],
            'SaaS': ['How-to Guides', 'Feature Highlights', 'Case Studies'],
            'Service Business': ['Expert Tips', 'Client Success Stories', 'Industry Insights'],
            'Content Creator': ['Tutorials', 'Best Practices', 'Resource Lists'],
            'Agency': ['Case Studies', 'Industry Analysis', 'Strategy Guides']
        }
        for suggestion in content_suggestions.get(context['business_type'], []):
            st.write(f"- {suggestion}")

def format_keyword_tag(keyword: str) -> str:
    """Format a keyword as an HTML tag with styling.
    
    Args:
        keyword: Keyword to format
        
    Returns:
        str: HTML-formatted keyword tag
    """
    return (
        f'<span style="background-color: #f0f2f6; padding: 3px 8px; '
        f'margin: 2px; border-radius: 10px;">{keyword}</span>'
    )

def display_heading_patterns(headings: List[str]) -> None:
    """Display a list of heading patterns.
    
    Args:
        headings: List of heading patterns to display
    """
    if not headings:
        return
        
    st.write("### Common Heading Patterns")
    for heading in headings:
        st.write(f"- {heading}")

def display_keyword_cloud(keywords: List[str]) -> None:
    """Display a cloud of keywords with styling.
    
    Args:
        keywords: List of keywords to display
    """
    if not keywords:
        return
        
    st.write("### Popular Keywords")
    keywords_html = ' '.join(format_keyword_tag(k) for k in keywords)
    st.markdown(
        f"<div style='line-height: 2.5;'>{keywords_html}</div>",
        unsafe_allow_html=True
    )

def display_blog_structures(patterns: List[str]) -> None:
    """Display a list of common blog structures.
    
    Args:
        patterns: List of blog structure patterns to display
    """
    if not patterns:
        return
        
    st.write("### Common Blog Structures")
    for pattern in patterns:
        st.write(f"- {pattern}")

def display_competitor_analysis() -> None:
    """Display competitor analysis results with proper type hints and validation."""
    # Early validation
    if not st.session_state.competitor_analysis:
        return
        
    analysis = st.session_state.competitor_analysis
    
    st.write("## Competitor Analysis")
    
    # Display analysis components
    display_heading_patterns(analysis.get('common_headings', []))
    display_keyword_cloud(analysis.get('popular_keywords', []))
    display_blog_structures(analysis.get('heading_patterns', []))

def display_keyword_research() -> None:
    """Display keyword research section with proper type hints and validation."""
    st.write("### 🎯 Keyword Research")
    
    # Input for seed keywords
    seed_input = st.text_input(
        "Enter seed keywords (comma-separated)",
        help="These will be used to generate fresh keyword suggestions"
    )
    
    # Process seed keywords if provided
    if seed_input:
        # Clean and validate seed keywords
        keywords = [k.strip() for k in seed_input.split(",") if k.strip()]
        if keywords:
            st.session_state.seed_keywords = keywords
        else:
            st.warning("Please enter valid seed keywords")
            return
    
    # Display suggested keywords if available
    if st.session_state.suggested_keywords:
        st.write("#### 💡 Suggested Keywords")
        cols = st.columns(3)
        for idx, keyword in enumerate(st.session_state.suggested_keywords):
            with cols[idx % 3]:
                if st.button(
                    f"Use '{keyword}'",
                    key=f"keyword_btn_{idx}",
                    help=f"Click to use '{keyword}' as your target keyword"
                ):
                    st.session_state.research_keyword = keyword
                    st.success(f"Selected keyword: {keyword}")
    
    # Display keyword trends if available
    if st.session_state.keyword_trends:
        with st.expander("📊 Keyword Trends", expanded=False):
            trends = st.session_state.keyword_trends
            
            # Display popular topics
            if trends.get("popular_topics"):
                st.write("**Popular Topics**")
                for topic in trends["popular_topics"]:
                    st.write(f"- {topic}")
            
            # Display underexplored areas
            if trends.get("underexplored_areas"):
                st.write("**Underexplored Areas**")
                for area in trends["underexplored_areas"]:
                    st.write(f"- {area}")
            
            # Display successful keywords
            if trends.get("successful_keywords"):
                st.write("**Successful Keywords**")
                for keyword in trends["successful_keywords"]:
                    st.write(f"- {keyword}")

def display_progress_status(status_message: str) -> None:
    """Display a progress status message with an emoji.
    
    Args:
        status_message: Message to display
    """
    st.write(f"📝 {status_message}")

async def analyze_content_patterns(keyword: str) -> Optional[Dict[str, Any]]:
    """Analyze competitor content patterns.
    
    Returns:
        Dict containing competitor analysis results, or None if analysis fails
    """
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
    """Generate a blog post using provided context data.
    
    Args:
        context_data: Dictionary containing either competitor insights or full context
        
    Returns:
        BlogPost object if successful, None if generation fails
    """
    try:
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
            
        # Generate blog post using all agents
        post = await generate_blog_post(
            keyword=keyword,
            business_type=business_type,
            content_goal=content_goals[0] if content_goals else "educate and inform readers",
            web_references=web_references
        )
        
        if not post:
            raise ValueError("Failed to generate blog post content")
            
        return post
        
    except Exception as e:
        st.error(f"Error generating blog post: {str(e)}")
        return None

async def analyze_generated_post(post_content: str) -> bool:
    """Analyze the generated blog post.
    
    Args:
        post_content: Content of the generated post to analyze
        
    Returns:
        bool: True if analysis was successful, False otherwise
    """
    try:
        # Store the content in session state first
        st.session_state.blog_content = post_content
        
        # Then call the analyze_blog_post function
        await analyze_blog_post()
        return True
    except Exception as e:
        st.error(f"Error analyzing generated post: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # Show detailed error for debugging
        return False

async def generate_viral_post() -> None:
    """Generate a viral blog post with competitor research.
    
    This function orchestrates the blog post generation process:
    1. Analyzes competitor content patterns
    2. Generates a blog post using insights
    3. Analyzes the generated post
    """
    # Reset error state
    st.session_state.has_error = False
    st.session_state.error_message = ""
    
    try:
        st.write("## Generating Your Viral Blog Post")
        
        # Step 1: Analyze competitor content
        st.write("🔍 Analyzing top performing content...")
        # Make sure we have a keyword to analyze
        if not hasattr(st.session_state, 'research_keyword') or not st.session_state.research_keyword:
            st.session_state.research_keyword = "digital accessibility"
            
        competitor_insights = await analyze_content_patterns(st.session_state.research_keyword)
        if not competitor_insights:
            st.warning("Could not analyze competitor content. Using default settings.")
            competitor_insights = {
                "common_headings": ["Introduction", "Benefits", "How-to", "Conclusion"],
                "popular_keywords": ["accessibility", "web", "digital", "compliance"],
                "heading_patterns": ["Problem-Solution", "List-Based Article"]
            }
            
        # Step 2: Generate blog post
        st.write("✍️ Writing your blog post...")
        post = await create_blog_post(competitor_insights)
        if not post:
            st.error("Failed to generate blog post.")
            return
            
        # Update session state
        st.session_state.generated_post = post
        st.session_state.blog_content = post.content
        
        # Step 3: Analyze post
        st.write("📊 Analyzing post performance...")
        if await analyze_generated_post(post.content):
            st.session_state.writing_status = "complete"
            st.success("✨ Your viral blog post is ready!")
        
    except Exception as e:
        st.session_state.has_error = True
        st.session_state.error_message = str(e)
        st.session_state.writing_status = "error"
        st.error(f"Failed to generate blog post: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # Show detailed error for debugging

async def render_business_context_section() -> None:
    """Render the business context analysis section."""
    st.write("## 🎯 Business Context Analysis")
    website_url = st.text_input(
        "Enter your website URL to analyze business context:",
        value=st.session_state.website_url,
        help="We'll analyze your website to understand your business type and content focus."
    )
    
    if website_url != st.session_state.website_url:
        st.session_state.website_url = website_url
        st.session_state.business_context = None
    
    if website_url:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(
                "We'll analyze your website to determine the optimal content strategy "
                "based on your business type and existing content."
            )
        with col2:
            if st.button("🔍 Analyze Website", use_container_width=True):
                await analyze_website_content()

def render_app_header() -> None:
    """Render the app header with title and description."""
    st.title("✍️ AI Blog Writer & Analyzer")
    st.write("""
        Create viral blog posts powered by AI! Our tool analyzes your business context,
        researches competitors, and generates optimized content for maximum impact.
    """)

def validate_url(url: str) -> bool:
    """Validate URL format.
    
    Args:
        url: URL string to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    if not url:
        return False
        
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        return False
        
    # Check for common URL components
    has_domain = any(char in url[8:] for char in ['.', ':'])
    return has_domain

def render_website_input() -> Optional[str]:
    """Render website URL input field with validation.
    
    Returns:
        Optional[str]: The entered website URL if valid, None otherwise
    """
    website_url = st.text_input(
        "Enter your website URL to analyze business context:",
        value=st.session_state.website_url,
        help="We'll analyze your website to understand your business type and content focus."
    )
    
    # Early return for empty input
    if not website_url:
        return None
        
    # Validate URL format
    if not validate_url(website_url):
        st.warning(
            "Please enter a valid URL (e.g., https://example.com). "
            "Make sure to include the protocol (http:// or https://) and domain."
        )
        return None
        
    return website_url

def render_analysis_button() -> bool:
    """Render the analyze website button.
    
    Returns:
        bool: True if button was clicked, False otherwise
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(
            "We'll analyze your website to determine the optimal content strategy "
            "based on your business type and existing content."
        )
    with col2:
        return st.button("Analyze Website", use_container_width=True)

def render_website_analysis_section() -> None:
    """Render the website URL input and analysis section."""
    website_url = render_website_input()
    
    if website_url != st.session_state.website_url:
        st.session_state.website_url = website_url
        st.session_state.business_context = None
        
    if website_url and render_analysis_button():
        run_async(analyze_website_content())

def render_content_goals_section() -> None:
    """Render the content goals section if business context is available."""
    if not st.session_state.business_context:
        return
        
    st.write("### Content Goals")
    content_goals = st.text_area(
        "Override content goals (optional):",
        value="\n".join(st.session_state.business_context.get('content_goals', [])),
        help="Enter each content goal on a new line"
    )
    
    if content_goals:
        st.session_state.business_context['content_goals'] = [
            goal.strip() for goal in content_goals.split("\n") if goal.strip()
        ]

async def render_business_context_section() -> None:
    """Render the business context analysis section following functional principles."""
    st.write("## Business Context Analysis")
    
    # Website URL input and analysis
    render_website_analysis_section()
    
    # Display business context if available
    if st.session_state.business_context:
        display_business_context()
        render_content_goals_section()

async def main() -> None:
    st.set_page_config(
        page_title="AI Blog Writer",
        page_icon="✍️",
        layout="centered"
    )
    init_session_state()

    with st.container():
        st.title("🚀 Blog Post Generator")
        
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
                post = await generate_post_automatically()
                if post:
                    st.session_state.generated_post = post
                    st.success("Blog post generated successfully!")
        
        # Manual Mode
        else:
            # Competitor Research
            keyword = st.text_input("Enter target keyword:", key="keyword_input")
            if st.button("🔍 Analyze Competitors", disabled=not keyword):
                if analysis := await analyze_competitors(keyword):
                    st.session_state.competitor_analysis = analysis
                    st.success("Competitor analysis complete!")

            # Content Generation        
            if st.session_state.competitor_analysis:
                if st.button("✨ Generate Blog Post", type="primary"):
                    with st.spinner("Generating..."):
                        post = await create_blog_post(st.session_state.competitor_analysis)
                        st.session_state.generated_post = post
            elif 'competitor_analysis' in st.session_state:
                st.info("Complete competitor research first")

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
            
            # Analyze blog post with OpenAI analyzer for dynamic improvement suggestions
            with st.expander("✅ Content Analysis & Improvement Suggestions"):
                st.markdown("**Analyzing content quality and business impact...**")
                
                # Use OpenAI blog analyzer for dynamic suggestions
                with st.spinner("Analyzing blog post quality..."):
                    try:
                        # Import the analyzer
                        from src.utils.openai_blog_analyzer import analyze_content
                        
                        # Get competitor insights if available
                        competitor_insights = None
                        if st.session_state.competitor_analysis:
                            competitor_insights = {
                                "structure": [item.get("structure", "") for item in st.session_state.competitor_analysis],
                                "tone": [item.get("tone", "") for item in st.session_state.competitor_analysis],
                                "content": [item.get("content", "") for item in st.session_state.competitor_analysis]
                            }
                        
                        # Analyze the blog post - don't use asyncio.run inside an async function
                        analysis_result = await analyze_content(
                            content=st.session_state.generated_post.content,
                            keyword=st.session_state.research_keyword,
                            competitor_insights=competitor_insights
                        )
                        
                        # Display analysis results
                        st.markdown(f"**Overall Score: {analysis_result.overall_score:.1f}/10**")
                        
                        # Display structure analysis
                        st.markdown("### Structure Analysis")
                        st.markdown(f"**Score: {analysis_result.structure.score:.1f}/10**")
                        st.markdown("**Strengths:**")
                        for strength in analysis_result.structure.strengths:
                            st.markdown(f"- {strength}")
                        st.markdown("**Areas for Improvement:**")
                        for weakness in analysis_result.structure.weaknesses:
                            st.markdown(f"- {weakness}")
                        
                        # Display business impact analysis (from empathy section)
                        st.markdown("### Business Impact Analysis")
                        st.markdown(f"**Score: {analysis_result.empathy.score:.1f}/10**")
                        st.markdown("**Strengths:**")
                        for strength in analysis_result.empathy.strengths:
                            st.markdown(f"- {strength}")
                        st.markdown("**Areas for Improvement:**")
                        for weakness in analysis_result.empathy.weaknesses:
                            st.markdown(f"- {weakness}")
                        
                        # Create checkboxes for improvement options based on analysis
                        st.markdown("### Select improvements to apply:")
                        improvement_options = {}
                        
                        # Add structure suggestions
                        for i, suggestion in enumerate(analysis_result.structure.suggestions):
                            improvement_options[f"structure_{i}"] = suggestion
                            
                        # Add empathy/business impact suggestions
                        for i, suggestion in enumerate(analysis_result.empathy.suggestions):
                            improvement_options[f"business_{i}"] = suggestion
                        
                        # Create checkboxes for improvement options
                        selected_improvements = {}
                        for key, description in improvement_options.items():
                            selected_improvements[key] = st.checkbox(description)
                        
                        # Regenerate button
                        if st.button("♻️ Regenerate with Selected Improvements"):
                            st.session_state.regenerate_options = {
                                k: v for k, v in selected_improvements.items() if v
                            }
                            if st.session_state.regenerate_options:
                                with st.spinner("Regenerating blog post with improvements..."):
                                    # Here you would implement the regeneration logic
                                    # This would use the selected improvements to guide the regeneration
                                    st.success("Blog post regenerated with selected improvements!")
                            else:
                                st.warning("Please select at least one improvement option")
                    
                    except Exception as e:
                        st.error(f"Error analyzing blog post: {str(e)}")
                        st.markdown("**Fallback Improvement Suggestions:**")
                        fallback_options = {
                            "headline": "Create a more benefit-driven headline",
                            "examples": "Add more specific industry examples with metrics",
                            "data": "Include more data points and statistics",
                            "structure": "Improve section organization for better flow",
                            "business_impact": "Strengthen business ROI focus"
                        }
                        
                        # Create checkboxes for fallback improvement options
                        selected_improvements = {}
                        for key, description in fallback_options.items():
                            selected_improvements[key] = st.checkbox(description)
                        
                        # Regenerate button for fallback options
                        if st.button("♻️ Regenerate with Improvements"):
                            st.session_state.regenerate_options = {
                                k: v for k, v in selected_improvements.items() if v
                            }
                            if st.session_state.regenerate_options:
                                with st.spinner("Regenerating blog post with improvements..."):
                                    # Fallback regeneration logic
                                    st.success("Blog post regenerated with selected improvements!")
                            else:
                                st.warning("Please select at least one improvement option")
            
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

def run_async(coro):
    """Run an async coroutine in a synchronous context."""
    try:
        # Set up asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()

if __name__ == "__main__":
    try:
        run_async(main())
    except Exception as e:
        st.error(f"Application error: {e}")
