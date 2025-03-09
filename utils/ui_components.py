"""
UI components for the blog post generator.
Contains functions for rendering UI elements in the Streamlit app.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List

def render_post_card(post, index):
    """Render a card for a blog post in the sidebar."""
    # Debug the post object
    print(f"DEBUG: Post object type: {type(post)}")
    print(f"DEBUG: Post object keys: {post.keys() if isinstance(post, dict) else 'Not a dict'}")
    
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
        print(f"DEBUG: Button clicked for post {index}, setting current_post and viewing_history")
        
        # Make a deep copy of the post to avoid reference issues
        import copy
        post_copy = copy.deepcopy(post)
        
        # Print post details for debugging
        print(f"DEBUG: Post ID: {post_copy.get('id')}")
        print(f"DEBUG: Post title: {post_copy.get('title')}")
        print(f"DEBUG: Post has analysis: {'analysis' in post_copy}")
        print(f"DEBUG: Post has agent_activities: {'agent_activities' in post_copy}")
        
        # Set the session state
        st.session_state.current_post = post_copy
        st.session_state.viewing_history = True
        
        # Rerun to update the UI
        st.rerun()

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

def render_agent_status_card(agent_name, agent_data, is_current):
    """Render a card for an agent's status."""
    status = agent_data.get("status", "Unknown")
    
    # Style based on status and if current
    if is_current:
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #2196F3;">
            <h4 style="margin: 0; color: #2196F3;">{agent_name} <span style="color: #4CAF50;">ACTIVE</span></h4>
            <p style="margin: 5px 0;"><strong>Status:</strong> {status}</p>
            <p style="margin: 5px 0;"><strong>Activity:</strong> {agent_data.get('output', 'Working...')}</p>
        </div>
        """, unsafe_allow_html=True)
    elif status == "Completed":
        st.markdown(f"""
        <div style="background-color: #f1f8e9; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #8BC34A;">
            <h4 style="margin: 0; color: #689F38;">{agent_name} DONE</h4>
            <p style="margin: 5px 0;"><strong>Status:</strong> {status}</p>
            <p style="margin: 5px 0;"><strong>Contribution:</strong> {agent_data.get('output', 'Task completed')}</p>
            {f'<p style="margin: 5px 0;"><strong>Quality:</strong> {agent_data.get("quality", 0)}/10</p>' if "quality" in agent_data else ''}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #9E9E9E;">
            <h4 style="margin: 0; color: #616161;">{agent_name}</h4>
            <p style="margin: 5px 0;"><strong>Status:</strong> {status}</p>
        </div>
        """, unsafe_allow_html=True)

def display_progress_ui(current_agent, agent_activities):
    """Display the progress UI for blog generation."""
    print("DEBUG: display_progress_ui called with current_agent =", current_agent)
    print("DEBUG: agent_activities =", agent_activities)
    
    # Create a visually appealing progress container
    with st.container(border=True):
        st.markdown("### Blog Post Generation in Progress")
        
        # Show current agent with prominent styling
        st.markdown(f"""
        <div style="background-color: #f0f7ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #1E88E5;">
            <h3 style="margin: 0; color: #1E88E5;">Current Agent: {current_agent}</h3>
            <p style="margin: 5px 0 0 0;">Working on your blog post...</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Add a progress bar that updates based on agent progress
        agent_list = ["Context Agent", "Keyword Agent", "Research Agent", "Content Agent", "Quality Agent", "Humanizer Agent"]
        current_agent_index = agent_list.index(current_agent) if current_agent in agent_list else 0
        progress_value = (current_agent_index + 1) / len(agent_list)
        
        # Show overall progress
        st.markdown("#### Overall Progress")
        st.progress(progress_value)
        st.markdown(f"**Step {current_agent_index + 1} of {len(agent_list)}**: {int(progress_value * 100)}% complete")
        
        # Create columns for a more organized layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Display detailed agent activities
            st.markdown("#### Agent Activities")
            
            # Create a scrollable container for agent activities
            with st.container(height=300, border=False):
                if agent_activities:
                    # Display active agent with highlight
                    for agent_name, agent_data in agent_activities.items():
                        is_current = agent_name == current_agent
                        render_agent_status_card(agent_name, agent_data, is_current)
                else:
                    st.info("Initializing agents... Please wait.")
        
        with col2:
            # Show estimated time and tips
            st.markdown("#### Estimated Time")
            
            # Calculate remaining time based on current agent
            remaining_minutes = (len(agent_list) - current_agent_index) * 2
            st.markdown(f"**Approximately {remaining_minutes}-{remaining_minutes+2} minutes remaining**")
            
            st.markdown("#### Tips")
            tips = [
                "Blog posts are automatically saved to your history",
                "You can edit posts after generation",
                "Keywords are selected based on your context files",
                "Each agent specializes in a different aspect of content creation"
            ]
            import time
            tip = tips[int(time.time()) % len(tips)]  # Rotate tips
            st.info(f"**Tip:** {tip}")
        
        # Add a spinner at the bottom to indicate ongoing activity
        with st.spinner("Generating your blog post..."):
            # This is just for UI purposes, the actual generation happens in the background
            pass
        
        # Add a cancel button with better styling
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Cancel Generation", type="secondary", use_container_width=True):
                st.session_state.generation_in_progress = False
                st.rerun()