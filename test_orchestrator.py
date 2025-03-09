"""
Small test script to verify agent orchestration functionality
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Set a dummy API key for testing if not present in environment
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

def main():
    """Test the key components of agent orchestration."""
    try:
        print("Starting agent orchestration test")
        
        # Test dependency checker
        print("\nTesting dependency checker...")
        from src.agents.agent_orchestrator import check_dependencies
        try:
            check_dependencies()
            print("✅ Dependency check passed!")
        except Exception as e:
            print(f"❌ Dependency check failed: {e}")
            
        # Test agent initialization
        print("\nTesting agent orchestrator initialization...")
        from src.agents.agent_orchestrator import AgentOrchestrator
        try:
            orchestrator = AgentOrchestrator()
            print("✅ Agent orchestrator initialized successfully!")
            
            # Check which agents were initialized
            print("\nInitialized components:")
            print(f"✅ Keyword Agent: {orchestrator.keyword_agent is not None}")
            print(f"✅ Quality Checker: {orchestrator.quality_checker is not None}")
            print(f"✅ Memory Manager: {orchestrator.has_memory_manager}")
            print(f"✅ Research Agent: {orchestrator.research_agent is not None}")
            print(f"✅ Humanizer Agent: {orchestrator.humanizer_agent is not None}")
            print(f"✅ Validator Agent: {orchestrator.validator_agent is not None}")
            print(f"✅ Blog Analyzer: {orchestrator.blog_analyzer is not None}")
            
        except Exception as e:
            print(f"❌ Agent orchestrator initialization failed: {e}")
            
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()