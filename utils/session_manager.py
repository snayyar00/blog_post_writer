"""
Session state management for the blog post generator.
Handles initialization and updates to the Streamlit session state.
"""

import streamlit as st
from typing import Dict, Any
from utils.post_manager import load_posts_history

# Global variables to store agent activities
global_agent_activities = {}  # Store real agent activities

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

def update_session_state_from_globals():
    """Update session state from global variables to avoid thread context issues."""
    global global_agent_activities
    
    try:
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
                    if agent_data["status"] in ["Running", "Starting", "Processing", "Initializing"]:
                        st.session_state.current_agent = agent_name
                        found_active_agent = True
                        
                        # Also set generation_in_progress to True if we found an active agent
                        st.session_state.generation_in_progress = True
            
            # If no active agent found but we have a "Completed" status,
            # set the current agent to the last completed one for better UI feedback
            if not found_active_agent and not st.session_state.current_agent:
                completed_agents = [name for name, data in safe_activities.items()
                                  if isinstance(data, dict) and data.get("status") == "Completed"]
                if completed_agents:
                    st.session_state.current_agent = completed_agents[-1]
    except Exception as e:
        print(f"Error updating session state from globals: {str(e)}")

def get_agent_activities():
    """Get the current agent activities."""
    return global_agent_activities

def update_agent_activities(activities):
    """Update the global agent activities."""
    global global_agent_activities
    global_agent_activities = activities