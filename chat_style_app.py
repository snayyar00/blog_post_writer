"""
Enhanced Streamlit app with chat-style sidebar for blog post generation and management.
Includes cost reporting and history of previously generated posts.
"""

import os
import json
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import uuid

# Import our modules
from src.agents.keyword_functions import generate_keywords
from src.agents.research_agent import ResearchAgent
from src.agents.content_functions import humanize_content
from src.agents.memoripy_manager import ResearchMemoryManager
from src.utils.web_scraper import load_context_files, scrape_website_to_context
from src.utils.cost_tracker import generate_cost_report, save_cost_report, get_cost_tracker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
POSTS_DIRECTORY = Path("./generated_posts")
POSTS_DIRECTORY.mkdir(exist_ok=True)

# Session state initialization
def init_session_state():
    """Initialize session state variables."""
    if "posts_history" not in st.session_state:
        st.session_state.posts_history = load_posts_history()
    
    if "current_post" not in st.session_state:
        st.session_state.current_post = None
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    if "cost_report" not in st.session_state:
        st.session_state.cost_report = None
    
    if "editing_post" not in st.session_state:
        st.session_state.editing_post = False
    
    if "edit_content" not in st.session_state:
        st.session_state.edit_content = ""

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
                    return True
        except Exception as e:
            print(f"Error updating post {file_path}: {e}")
    
    return False

def add_chat_message(role: str, content: str, post_id: Optional[str] = None):
    """Add a message to the chat history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().timestamp(),
        "post_id": post_id
    }
    st.session_state.chat_messages.append(message)

def process_topic(topic: str, context_data: Dict[str, str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Process a topic through the agent pipeline with visualization."""
    results = {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "timestamp": datetime.now().timestamp(),
        "keywords": [],
        "research": [],
        "context_used": [],
        "webability_context": [],
        "brand_context": {},
        "content": "",
        "errors": []
    }
    
    # Extract and categorize context
    webability_context = []
    brand_voice = "professional yet conversational"  # Default
    target_audience = "business professionals"  # Default
    company_info = "WebAbility.io is a leading web accessibility consultancy"  # Default
    
    # Process context data
    for key, value in context_data.items():
        # Track which context files are used
        results["context_used"].append(key)
        
        # Categorize context
        if key.startswith("web_"):
            webability_context.append(value)
            results["webability_context"].append(key)
        elif "brand" in key.lower() or "voice" in key.lower():
            brand_voice = value
            results["brand_context"]["brand_voice"] = key
        elif "audience" in key.lower() or "target" in key.lower():
            target_audience = value
            results["brand_context"]["target_audience"] = key
        elif "company" in key.lower() or "business" in key.lower():
            company_info = value
            results["brand_context"]["company_info"] = key
    
    # Combine WebAbility.io context
    webability_content = "\n\n---\n\n".join(webability_context)
    
    # Add a chat message for starting the process
    add_chat_message("system", f"Starting to generate blog post about: {topic}", results["id"])
    
    # Step 1: Generate keywords
    with st.spinner("Generating keywords..."):
        try:
            # Add company info to context for better keyword generation
            keyword_context = context_data.copy()
            keyword_context["company_info"] = company_info
            keyword_context["webability_content"] = webability_content[:5000]  # Limit size
            
            results["keywords"] = generate_keywords(topic, keyword_context)
            st.success(f"Generated {len(results['keywords'])} keywords")
            
            # Add a chat message for keywords
            keyword_msg = f"Generated keywords: {', '.join(results['keywords'][:5])}"
            if len(results['keywords']) > 5:
                keyword_msg += f" and {len(results['keywords']) - 5} more"
            add_chat_message("assistant", keyword_msg, results["id"])
            
        except Exception as e:
            error_msg = f"Error generating keywords: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            # Use fallback keywords
            results["keywords"] = [topic, f"{topic} best practices", f"{topic} guide", "web accessibility"]
            add_chat_message("assistant", f"Error generating keywords. Using fallback keywords.", results["id"])
    
    # Step 2: Research the topic
    with st.spinner("Researching topic..."):
        try:
            research_agent = ResearchAgent(api_key=api_key)
            # Include WebAbility.io in the research query
            research_query = f"WebAbility.io {topic}: {', '.join(results['keywords'][:5])}"
            research_results = research_agent.research_topic(research_query)
            results["research"] = research_results
            st.success(f"Research completed with {len(research_results)} findings")
            
            # Add a chat message for research
            add_chat_message("assistant", f"Completed research with {len(research_results)} findings", results["id"])
            
        except Exception as e:
            error_msg = f"Error during research: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            # Use mock research data
            results["research"] = [{
                "content": f"Error researching {topic}. Using placeholder content.",
                "sources": [],
                "confidence": 0
            }]
            add_chat_message("assistant", f"Error during research. Using placeholder content.", results["id"])
    
    # Step 3: Store research results in memory
    with st.spinner("Storing research in memory..."):
        try:
            memory_manager = ResearchMemoryManager(api_key)
            research_data = {
                "topic": topic,
                "keywords": results["keywords"],
                "research": results["research"],
                "context_used": results["context_used"],
                "webability_context": results["webability_context"],
                "timestamp": time.time()
            }
            
            # Save research results to a file for reference
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            memory_dir = Path("./memory")
            memory_dir.mkdir(exist_ok=True)
            research_file = memory_dir / f"research_{timestamp}.json"
            with open(research_file, "w") as f:
                json.dump(research_data, f, indent=2)
            
            # Store in memory system
            store_success = memory_manager.store_research_results(research_data, topic)
            if store_success:
                st.success(f"Research stored in memory and saved to {research_file}")
                add_chat_message("assistant", f"Research stored in memory system", results["id"])
            else:
                st.warning(f"Memory storage failed, but research saved to {research_file}")
                add_chat_message("assistant", f"Memory storage failed, but research saved to file", results["id"])
                
        except Exception as e:
            error_msg = f"Error storing research: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            add_chat_message("assistant", f"Error storing research: {str(e)}", results["id"])
            
            # Try to save research results to a file even if memory storage failed
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                memory_dir = Path("./memory")
                memory_dir.mkdir(exist_ok=True)
                research_file = memory_dir / f"research_error_{timestamp}.json"
                with open(research_file, "w") as f:
                    json.dump({
                        "topic": topic,
                        "keywords": results["keywords"],
                        "research": results["research"],
                        "error": str(e),
                        "timestamp": time.time()
                    }, f, indent=2)
                st.info(f"Research saved to {research_file} despite memory error")
                add_chat_message("assistant", f"Research saved to file despite memory error", results["id"])
            except Exception as file_error:
                st.error(f"Could not save research to file: {str(file_error)}")
    
    # Step 4: Humanize the content
    with st.spinner("Generating human-friendly content..."):
        try:
            # Prepare context for humanization
            humanization_context = {
                "brand_voice": brand_voice,
                "target_audience": target_audience,
                "company": "WebAbility.io",
                "company_info": company_info,
                "website": "https://www.webability.io",
                "topic": topic,
                "keywords": ", ".join(results["keywords"][:10])
            }
            
            # Extract research content
            research_content = "\n\n".join([item.get("content", "") for item in results["research"]])
            
            # Add WebAbility.io specific context
            if webability_content:
                research_content += "\n\nWebAbility.io Context:\n" + webability_content[:2000]
            
            # Humanize content
            results["content"] = humanize_content(
                research_content, 
                humanization_context.get("brand_voice", brand_voice),
                humanization_context.get("target_audience", target_audience)
            )
            st.success("Content humanized successfully")
            add_chat_message("assistant", f"Blog post generated successfully!", results["id"])
            
        except Exception as e:
            error_msg = f"Error humanizing content: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            results["content"] = research_content  # Use raw research as fallback
            add_chat_message("assistant", f"Error humanizing content. Using raw research as fallback.", results["id"])
    
    # Save the post to history
    save_post(results)
    
    # Update session state
    st.session_state.posts_history = load_posts_history()
    st.session_state.current_post = results
    
    # Generate cost report
    try:
        cost_report = generate_cost_report()
        st.session_state.cost_report = cost_report
        add_chat_message("system", "Cost report updated", results["id"])
    except Exception as e:
        st.error(f"Error generating cost report: {str(e)}")
    
    return results

def render_chat_message(message):
    """Render a chat message with appropriate styling."""
    is_user = message["role"] == "user"
    
    # Create columns for avatar and message
    col1, col2 = st.columns([1, 9])
    
    with col1:
        # Display avatar
        if is_user:
            st.markdown("👤")
        elif message["role"] == "assistant":
            st.markdown("🤖")
        else:
            st.markdown("🔔")
    
    with col2:
        # Create message container with appropriate styling
        if is_user:
            st.markdown(f"""
            <div style="background-color: #e6f7ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;">
                <p style="margin: 0;">{message['content']}</p>
                <p style="margin: 0; font-size: 0.8em; color: #888; text-align: right;">
                    {datetime.fromtimestamp(message['timestamp']).strftime('%I:%M %p')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.markdown(f"""
            <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 10px;">
                <p style="margin: 0;">{message['content']}</p>
                <p style="margin: 0; font-size: 0.8em; color: #888; text-align: right;">
                    {datetime.fromtimestamp(message['timestamp']).strftime('%I:%M %p')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: #f9f9f9; padding: 10px; border-radius: 10px; margin-bottom: 10px; border-left: 3px solid #ccc;">
                <p style="margin: 0; font-style: italic;">{message['content']}</p>
                <p style="margin: 0; font-size: 0.8em; color: #888; text-align: right;">
                    {datetime.fromtimestamp(message['timestamp']).strftime('%I:%M %p')}
                </p>
            </div>
            """, unsafe_allow_html=True)

def render_post_card(post, index):
    """Render a card for a blog post in the sidebar."""
    # Format the date
    date_str = datetime.fromtimestamp(post.get("timestamp", 0)).strftime("%b %d, %Y")
    
    # Create a clickable card
    st.markdown(f"""
    <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; cursor: pointer; background-color: {'#f0f0f0' if st.session_state.current_post and st.session_state.current_post.get('id') == post.get('id') else '#ffffff'};">
        <h4 style="margin: 0;">{post.get("topic", "Untitled Post")}</h4>
        <p style="margin: 0; font-size: 0.8em; color: #888;">{date_str}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create a button to load this post
    if st.button(f"Open", key=f"open_post_{index}"):
        st.session_state.current_post = post
        st.session_state.editing_post = False
        
        # Filter chat messages for this post
        post_messages = [msg for msg in st.session_state.chat_messages 
                         if msg.get("post_id") == post.get("id")]
        
        # If no messages for this post, add a system message
        if not post_messages:
            add_chat_message("system", f"Loaded post: {post.get('topic', 'Untitled Post')}", post.get("id"))
        
        # Rerun to update the UI
        st.rerun()

def render_cost_report():
    """Render the cost report in the chat interface."""
    if st.session_state.cost_report:
        # Extract key information from the cost report
        lines = st.session_state.cost_report.split("\n")
        total_cost_line = next((line for line in lines if "Total Cost:" in line), "Total Cost: $0.0000")
        
        # Create a formatted message
        st.markdown(f"""
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 3px solid #4CAF50;">
            <h3 style="margin-top: 0;">API Cost Report</h3>
            <p><strong>{total_cost_line}</strong></p>
            <details>
                <summary>View detailed cost breakdown</summary>
                <pre style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto;">
{st.session_state.cost_report}
                </pre>
            </details>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main application function."""
    st.set_page_config(
        page_title="WebAbility.io Blog Post Generator",
        page_icon="📝",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Sidebar for post history
    with st.sidebar:
        st.title("📚 Post History")
        st.write("Previously generated blog posts:")
        
        # Display post history
        if st.session_state.posts_history:
            for i, post in enumerate(st.session_state.posts_history):
                render_post_card(post, i)
        else:
            st.info("No posts generated yet. Create your first post!")
        
        # Divider
        st.divider()
        
        # Configuration section
        st.header("⚙️ Configuration")
        
        # API key handling - don't show the actual key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.warning("⚠️ No API key found in environment variables")
            st.info("API key will be loaded from .env file if available")
        else:
            st.success("✅ API key loaded from environment")
        
        # Website scraping section
        st.header("🌐 WebAbility.io Content")
        sitemap_url = "https://www.webability.io/sitemap.xml"
        
        # Check if we already have scraped content
        context_data = load_context_files()
        web_context_count = sum(1 for filename in context_data.keys() if filename.startswith("web_"))
        
        if web_context_count > 0:
            st.success(f"✅ {web_context_count} WebAbility.io pages loaded")
        else:
            st.warning("No WebAbility.io content loaded")
        
        # Scrape button
        col1, col2 = st.columns(2)
        with col1:
            max_urls = st.number_input("Max URLs", min_value=1, max_value=20, value=5)
        with col2:
            scrape_button = st.button("Scrape Website")
        
        if scrape_button:
            with st.spinner(f"Scraping {sitemap_url}..."):
                saved_files = scrape_website_to_context(sitemap_url, max_urls=max_urls)
                st.success(f"Scraped {len(saved_files)} pages from WebAbility.io")
                # Reload context data
                context_data = load_context_files()
    
    # Main content area
    st.title("📝 WebAbility.io Blog Post Generator")
    st.subheader("Generate engaging accessibility-focused blog posts with AI")
    
    # Create a chat-like interface
    chat_container = st.container()
    
    # Input area at the bottom
    with st.container():
        if st.session_state.editing_post:
            # Editing interface
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
                        
                        # Add a chat message
                        add_chat_message("user", "Edited the blog post content", post_id)
                        add_chat_message("system", "Blog post updated successfully", post_id)
                        
                        # Exit editing mode
                        st.session_state.editing_post = False
                        st.rerun()
            
            with col2:
                if st.button("Cancel"):
                    st.session_state.editing_post = False
                    st.rerun()
        else:
            # Normal input interface
            col1, col2 = st.columns([3, 1])
            
            with col1:
                topic = st.text_input("Enter blog topic", placeholder="e.g., web accessibility best practices")
            
            with col2:
                generate_button = st.button("Generate Blog Post", type="primary", disabled=not topic)
            
            # Show cost report button
            if st.button("Show Cost Report"):
                try:
                    cost_report = generate_cost_report()
                    st.session_state.cost_report = cost_report
                    add_chat_message("user", "Requested cost report")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating cost report: {str(e)}")
            
            # If current post is loaded, show edit button
            if st.session_state.current_post:
                if st.button("✏️ Edit Current Post"):
                    st.session_state.editing_post = True
                    st.session_state.edit_content = st.session_state.current_post.get("content", "")
                    add_chat_message("user", "Started editing the blog post", 
                                    st.session_state.current_post.get("id"))
                    st.rerun()
    
    # Process the topic if generate button is clicked
    if generate_button and topic:
        add_chat_message("user", f"Generate a blog post about: {topic}")
        
        # Process the topic
        with st.spinner("Generating blog post..."):
            results = process_topic(topic, context_data)
        
        # Rerun to update the UI
        st.rerun()
    
    # Display chat messages
    with chat_container:
        # Filter messages for the current post if one is selected
        if st.session_state.current_post:
            post_id = st.session_state.current_post.get("id")
            filtered_messages = [msg for msg in st.session_state.chat_messages 
                               if msg.get("post_id") == post_id or msg.get("post_id") is None]
        else:
            filtered_messages = st.session_state.chat_messages
        
        # Render each message
        for message in filtered_messages:
            render_chat_message(message)
        
        # Show cost report if requested
        if st.session_state.cost_report and any(msg.get("content") == "Requested cost report" for msg in filtered_messages):
            render_cost_report()
        
        # Display current post content if available
        if st.session_state.current_post and not st.session_state.editing_post:
            st.markdown("---")
            st.subheader(f"📄 {st.session_state.current_post.get('topic', 'Blog Post')}")
            st.markdown(st.session_state.current_post.get("content", ""))
            
            # Download button
            st.download_button(
                label="Download Blog Post",
                data=st.session_state.current_post.get("content", ""),
                file_name=f"blog_post_{st.session_state.current_post.get('topic', 'post').replace(' ', '_')}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()