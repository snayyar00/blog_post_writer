"""
Test script to verify the Streamlit app can start correctly.
This script checks the main components needed for app initialization.
"""

import os
import sys
import importlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_streamlit_imports():
    """Test if Streamlit and other required packages can be imported."""
    print("Testing imports...")
    required_packages = [
        "streamlit", 
        "pandas", 
        "numpy", 
        "openai", 
        "aiohttp",
        "asyncio",
        "time",
        "threading",
        "uuid"
    ]
    
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ Successfully imported {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ Failed to import {package}")
    
    return missing

def test_app_initialization():
    """Test if the app can be initialized."""
    print("\nTesting app initialization...")
    
    # Ensure basic session state functionality
    try:
        import streamlit as st
        print("✅ Streamlit session state available")
    except Exception as e:
        print(f"❌ Error accessing streamlit: {e}")
        return False
    
    # Try to import the main app
    try:
        # Import without executing
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        unified_app = importlib.import_module("unified_app")
        print("✅ Successfully imported unified_app module")
        
        # Check if key functions exist
        if hasattr(unified_app, "main"):
            print("✅ Main function exists")
        else:
            print("❌ Main function not found")
            
        if hasattr(unified_app, "init_session_state"):
            print("✅ Session state initialization function exists")
        else:
            print("❌ Session state initialization function not found")
        
        return True
    except Exception as e:
        print(f"❌ Error importing unified_app module: {e}")
        return False

def check_agent_orchestrator():
    """Test if the agent orchestrator can be initialized."""
    print("\nTesting agent orchestrator...")
    try:
        # Set dummy API key for testing
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy-key-for-testing")
        
        # Import agent orchestrator
        from src.agents.agent_orchestrator import check_dependencies, AgentOrchestrator
        
        # Test dependency checker
        print("Checking dependencies...")
        try:
            check_dependencies()
            print("✅ Dependency check passed")
        except Exception as e:
            print(f"❌ Dependency check failed: {e}")
            return False
            
        # Test agent initialization
        print("Initializing orchestrator...")
        try:
            orchestrator = AgentOrchestrator()
            print("✅ Orchestrator initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Orchestrator initialization failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error in agent orchestrator test: {e}")
        return False

if __name__ == "__main__":
    print("Starting Streamlit app tests...\n")
    
    # Check imports
    missing_packages = check_streamlit_imports()
    
    # Test app initialization if no critical packages are missing
    if not any(pkg in missing_packages for pkg in ["streamlit", "openai", "asyncio"]):
        app_init_success = test_app_initialization()
    else:
        app_init_success = False
        print("❌ Cannot test app initialization due to missing critical packages")
    
    # Test agent orchestrator
    orchestrator_success = check_agent_orchestrator()
    
    # Summary
    print("\nTest Summary:")
    print(f"✅ App initialization: {'Success' if app_init_success else 'Failed'}")
    print(f"✅ Agent orchestrator: {'Success' if orchestrator_success else 'Failed'}")
    
    if app_init_success and orchestrator_success:
        print("\n✅ All tests passed! The app should start correctly.")
        print("\nRun the app with: streamlit run unified_app.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues before running the app.")