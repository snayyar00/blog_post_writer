"""
Functions for updating session state and displaying agent activities.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional
from src.utils.logging_manager import log_info, log_error, log_debug

def update_session_state_from_globals(agent_activities: Optional[Dict[str, Any]] = None) -> None:
    """Update session state from global variables to avoid thread context issues."""
    try:
        log_debug("Updating session state from globals", "STATE")
        log_debug(f"Current agent activities: {agent_activities}", "STATE")
        
        # Initialize session state if needed
        if 'agent_activities' not in st.session_state:
            st.session_state.agent_activities = {}
        if 'agent_status' not in st.session_state:
            st.session_state.agent_status = {}
        if 'current_agent' not in st.session_state:
            st.session_state.current_agent = None
        
        # Update from global activities
        if agent_activities:
            # Make a safe copy of agent activities
            safe_activities = {}
            for k, v in agent_activities.items():
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
                        log_debug(f"Active agent found: {agent_name}", "STATE")
            
            # If no active agent found but we have a "Completed" status,
            # set the current agent to the last completed one for better UI feedback
            if not found_active_agent and not st.session_state.current_agent:
                completed_agents = [name for name, data in safe_activities.items()
                                  if isinstance(data, dict) and data.get("status") == "Completed"]
                if completed_agents:
                    st.session_state.current_agent = completed_agents[-1]
                    log_debug(f"Set current agent to last completed: {completed_agents[-1]}", "STATE")
            
            # Force Streamlit to update the UI more frequently
            # This is a hack to make Streamlit update the UI more often
            if st.session_state.generation_in_progress:
                # Add a timestamp to force updates
                st.session_state.last_update = datetime.now().timestamp()
                # Force a rerun every 2 seconds
                if not hasattr(st.session_state, 'last_rerun') or datetime.now().timestamp() - st.session_state.last_rerun > 2:
                    st.session_state.last_rerun = datetime.now().timestamp()
                    st.rerun()
    except Exception as e:
        log_error(f"Error updating session state from globals: {str(e)}", "STATE")

def display_blog_analysis(analysis: Dict[str, Any]) -> None:
    """Display blog analysis without nested expanders."""
    log_debug("Displaying blog analysis", "STATE")
    
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
    
    log_debug("Finished displaying blog analysis", "STATE")

def display_agent_activities(agent_activities: Dict[str, Any]) -> None:
    """Display agent activities from the orchestrator."""
    if not agent_activities:
        st.info("No agent activity data available.")
        log_debug("No agent activities to display", "STATE")
        return
    
    log_debug(f"Displaying activities for {len(agent_activities)} agents", "STATE")
    
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

def render_post_card(post: Dict[str, Any], index: int) -> None:
    """Render a card for a blog post in the sidebar."""
    # Format the date
    date_str = datetime.fromtimestamp(post.get("timestamp", 0)).strftime("%b %d, %Y")
    
    # Get the topic or title
    topic = post.get("topic", post.get("title", "Untitled Post"))
    
    log_debug(f"Rendering post card for: {topic}", "STATE")
    
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
        log_info(f"Opened post: {topic}", "STATE")
        
        # Rerun to update the UI
        st.rerun()
