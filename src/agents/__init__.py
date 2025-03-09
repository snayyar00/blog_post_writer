"""
Agent package for blog post generation.
Contains modules for orchestrating the blog post generation process.
"""

# Define the list of available modules without importing them directly
# This avoids circular imports while still documenting what's available

# Export all important functions and classes
__all__ = [
    # Agent orchestrator
    'AgentOrchestrator',
    'generate_blog_post',
    'check_dependencies',
    'ensure_api_keys',
    
    # Research and analysis
    'ResearchAgent',
    'research_topic',
    'KeywordTopologyAgent',
    'generate_keywords',
    'find_related_content',
    'ContentQualityChecker',
    'analyze_competitor_blogs',
    
    # Content generation and improvement
    'HumanizerAgent',
    'BlogAnalyzer',
    'ContentValidatorAgent',
    'CompanyMemoryManager',
    'generate_outline',
    'generate_sections'
]

# Lazy imports to avoid circular dependencies
def get_agent_orchestrator():
    from src.agents.agent_orchestrator import AgentOrchestrator
    return AgentOrchestrator

def get_research_agent():
    from src.agents.research_agent import ResearchAgent
    return ResearchAgent

def get_keyword_agent():
    from src.agents.keyword_agent import KeywordTopologyAgent
    return KeywordTopologyAgent

def get_memory_manager():
    from src.agents.memory_manager import CompanyMemoryManager
    return CompanyMemoryManager

def get_validator_agent():
    from src.agents.validator_agent import ContentValidatorAgent
    return ContentValidatorAgent
