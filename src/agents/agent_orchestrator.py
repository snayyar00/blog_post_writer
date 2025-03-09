"""
Agent orchestrator that coordinates all agents for blog post generation.
Uses functional programming patterns and follows RORO principles.
"""

import os
import asyncio
import re  # Add explicit re import
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import importlib.util
import datetime

from src.agents.research_agent import research_topic, ResearchAgent
from src.agents.keyword_agent import KeywordTopologyAgent, generate_keywords
from src.agents.context_search_agent import find_related_content
from src.agents.competitor_analysis_agent import analyze_competitor_blogs
from src.agents.humanizer_agent import HumanizerAgent
from src.agents.validator_agent import ContentValidatorAgent
from src.agents.memory_manager import CompanyMemoryManager
from src.agents.content_functions import generate_outline, generate_sections, humanize_content
from src.utils.openai_blog_writer import BlogPost, ContentMetrics
from src.utils.keyword_history_manager import KeywordHistoryManager
from src.utils.logging_manager import log_info, log_warning, log_error, log_debug
from src.utils.openai_blog_analyzer import analyze_content
from src.utils.keyword_topology_manager import KeywordTopology

# Initialize keyword managers
keyword_history = KeywordHistoryManager()
try:
    keyword_topology = KeywordTopology()
    log_info("Keyword topology manager initialized", "TOPOLOGY")
except Exception as e:
    log_warning(f"Error initializing keyword topology: {e}", "TOPOLOGY")
    keyword_topology = None

# Global variables to track agent progress
global_agent_activities = {}

def ensure_api_keys():
    """Ensure that necessary API keys are available."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")

class AgentOrchestrator:
    """Orchestrates all agents for blog post generation."""
    
    def __init__(self):
        """Initialize the orchestrator with all required agents."""
        # Check API keys
        ensure_api_keys()
        
        self.keyword_agent = KeywordTopologyAgent()
        
        # Initialize keyword topology with error handling
        global keyword_topology
        try:
            if keyword_topology is None:
                keyword_topology = KeywordTopology()
            self.keyword_topology = keyword_topology
            self.has_keyword_topology = True
            log_info("Keyword topology is ready", "KEYWORD")
        except Exception as e:
            log_warning(f"Failed to initialize keyword topology: {str(e)}")
            self.has_keyword_topology = False
        
        # Initialize memory manager with error handling
        try:
            self.memory_manager = CompanyMemoryManager()
            self.has_memory_manager = True
        except Exception as e:
            log_warning(f"Failed to initialize memory manager: {str(e)}")
            self.has_memory_manager = False
            
        # Initialize research agent with error handling
        try:
            # Get API keys from environment variables
            perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            # Initialize research agent if any API keys are available
            if any([perplexity_api_key, anthropic_api_key, openai_api_key]):
                from src.agents.research_agent import ResearchAgent, AIProvider
                self.research_agent = ResearchAgent(
                    perplexity_api_key=perplexity_api_key,
                    anthropic_api_key=anthropic_api_key,
                    openai_api_key=openai_api_key,
                    default_provider=AIProvider.AUTO
                )
                log_info("Research agent initialized successfully with available API providers")
            else:
                self.research_agent = None
                log_warning("No API keys available for research agent")
        except Exception as e:
            log_warning(f"Failed to initialize research agent: {str(e)}")
            self.research_agent = None
            
        self.humanizer_agent = HumanizerAgent()
        self.validator_agent = ContentValidatorAgent()
    
    async def generate_blog_post(self, topic: str, **kwargs) -> BlogPost:
        """Generate a blog post using coordinated agents.
        
        Args:
            topic: Main topic for the blog post
            **kwargs: Additional parameters for customization
            
        Returns:
            Generated blog post with metadata
        """
        global global_agent_activities
        
        # Update global activities for Context Agent
        global_agent_activities["Context Agent"] = {
            "status": "Running",
            "output": "Analyzing context and preparing research"
        }
        log_info("Starting blog post generation for topic: " + topic, "CONTEXT")
        
        # Track keyword usage after confirming it's a valid topic
        try:
            # Validate topic is not empty or just whitespace
            if not topic or not topic.strip():
                raise ValueError("Topic cannot be empty")
            
            # Record keyword usage in both history and topology
            keyword_history.record_keyword_use(topic)
            if self.has_keyword_topology and self.keyword_topology:
                # Record in topology to improve future selection
                self.keyword_topology.record_keyword_use(topic)
                
            log_info(f"Recorded keyword usage for: {topic}")
        except Exception as e:
            log_warning(f"Failed to record keyword usage: {str(e)}")
        
        # Initialize tasks to be executed in parallel
        research_task = None
        competitor_task = None
        
        # Research phase with retries and exponential backoff
        global_agent_activities["Research Agent"] = {
            "status": "Running",
            "output": "Gathering research data"
        }
        
        # Define research function with retries and improved error handling
        async def perform_research():
            if not self.research_agent:
                log_warning("No research agent available, skipping research phase")
                return None
                
            max_retries = 3
            retry_count = 0
            backoff_time = 1  # Initial backoff time in seconds
            
            while retry_count < max_retries:
                try:
                    log_info(f"Research attempt {retry_count + 1} for topic: {topic}", "RESEARCH")
                    research_result = await self.research_agent.research_topic(
                        topic=topic,
                        business_context=kwargs.get("business_context"),
                        depth=kwargs.get("research_depth", 3)
                    )
                    # Handle both list and dictionary return types
                    research_data = research_result if isinstance(research_result, list) else research_result.get("findings", [])
                    
                    if research_data:  # Only mark as complete if we got data
                        global_agent_activities["Research Agent"]["status"] = "Completed"
                        global_agent_activities["Research Agent"]["output"] = f"Found {len(research_data)} research sources"
                        return research_data
                    else:
                        retry_count += 1
                        log_warning(f"Research attempt {retry_count} returned no data, retrying after {backoff_time}s...")
                        # Implement exponential backoff
                        await asyncio.sleep(backoff_time)
                        backoff_time *= 2  # Double the backoff time for next retry
                except Exception as e:
                    retry_count += 1
                    log_warning(f"Research attempt {retry_count} failed: {str(e)}")
                    # Implement exponential backoff
                    await asyncio.sleep(backoff_time)
                    backoff_time *= 2  # Double the backoff time for next retry
                    
                    if retry_count >= max_retries:
                        global_agent_activities["Research Agent"]["status"] = "Failed"
                        global_agent_activities["Research Agent"]["output"] = f"Research failed after {max_retries} attempts"
                        log_error(f"Research failed after {max_retries} attempts: {str(e)}")
                        # Return empty data as fallback
                        return []
            
            # If we reach here, all retries failed but didn't hit an exception
            global_agent_activities["Research Agent"]["status"] = "Failed"
            return []
            
        # Define competitor analysis function
        async def perform_competitor_analysis():
            try:
                log_info("Starting competitor analysis", "COMPETITOR")
                # Mock implementation - this would be replaced with real implementation
                await asyncio.sleep(1) 
                return {"top_competitors": ["competitor1.com", "competitor2.com"], "insights": "Competitor insights"}
            except Exception as e:
                log_warning(f"Competitor analysis failed: {str(e)}")
                return {}
                
        # Start parallel tasks
        research_task = asyncio.create_task(perform_research())
        
        # Start competitor analysis only if needed
        if kwargs.get("analyze_competitors", False):
            global_agent_activities["Competitor Agent"] = {
                "status": "Running",
                "output": "Analyzing competitor content"
            }
            competitor_task = asyncio.create_task(perform_competitor_analysis())
        
        # Run keyword generation in parallel with research
        global_agent_activities["Keyword Agent"] = {
            "status": "Running",
            "output": "Generating keywords and outline"
        }
        log_info("Generating initial keywords", "KEYWORD")
        
        # Generate initial keywords without research data first
        initial_keywords_task = asyncio.create_task(
            self.keyword_agent.generate_keywords(topic, None)
        )
        
        # Wait for research to complete
        research_data = await research_task
        
        # Wait for competitor analysis if it was started
        competitor_insights = None
        if competitor_task:
            competitor_insights = await competitor_task
            global_agent_activities["Competitor Agent"]["status"] = "Completed"
            
        # Get initial keywords result
        initial_keywords = await initial_keywords_task
        
        # If we have research data, enrich keywords with research insights
        if research_data:
            log_info("Enhancing keywords with research data", "KEYWORD")
            keywords = await self.keyword_agent.enhance_keywords(
                initial_keywords, 
                research_data
            )
        else:
            keywords = initial_keywords
            
        # Generate outline with all available data
        log_info("Generating content outline", "KEYWORD")
        outline = await generate_outline(
            keyword=topic,
            research_results=research_data or {},
            competitor_insights=competitor_insights,
            content_type=kwargs.get("content_type", "standard"),
            industry=kwargs.get("industry", None)  # Added industry parameter
        )
        
        global_agent_activities["Keyword Agent"]["status"] = "Completed"
        global_agent_activities["Keyword Agent"]["output"] = f"Generated {len(keywords)} keywords and {len(outline) if outline else 0} outline sections"
        
        # Generate content sections with cost optimization and better error handling
        global_agent_activities["Content Agent"] = {
            "status": "Running",
            "output": "Generating enhanced content sections"
        }
        log_info("Generating enhanced content sections", "CONTENT")
        
        # Determine optimal model based on content complexity
        content_model = "gpt-3.5-turbo"  # Default to cheaper model
        
        # Use premium model for complex topics or when specified
        if kwargs.get("use_premium_model", False) or self._is_complex_topic(topic, outline, research_data):
            content_model = "gpt-4"
            log_info(f"Using premium model ({content_model}) for complex content generation", "CONTENT")
        else:
            log_info(f"Using standard model ({content_model}) for content generation", "CONTENT")
            
        # Track content generation start time for monitoring
        import time
        content_start_time = time.time()
        
        # Get enhancement options from kwargs or use defaults
        industry = kwargs.get("industry", None)
        # Handle empty string as None
        if industry == "":
            industry = None
        add_case_studies = kwargs.get("add_case_studies", True)
        add_expert_quotes = kwargs.get("add_expert_quotes", True)
        add_real_data = kwargs.get("add_real_data", True) 
        enhanced_formatting = kwargs.get("enhanced_formatting", True)
        
        # Log enhancement options
        log_info(f"Generating with enhancements: industry={industry}, case_studies={add_case_studies}, expert_quotes={add_expert_quotes}, real_data={add_real_data}", "CONTENT")
        
        # Always perform live research for important facts before content generation
        log_info("Performing focused research for key facts and statistics", "RESEARCH")
        research_keywords = [topic]
        
        # Extract additional research keywords from outline
        if outline and len(outline) > 1:
            for section in outline[1:3]:  # Use first couple sections for additional research
                if section and not section.startswith("#"):
                    research_keywords.append(section)
        
        # Store research results for use in content generation
        from src.agents.research_agent import research_topic
        try:
            focused_research = await research_topic(
                keywords=research_keywords, 
                mode="deep",
                business_context=kwargs.get("business_context", {})
            )
            
            # Save this research to memory for future use
            if self.has_memory_manager:
                await self.memory_manager.store_research(
                    f"{topic} latest research", 
                    focused_research
                )
                log_info(f"Stored latest research in memory", "RESEARCH")
                
            # Combine with existing research
            if research_data:
                if isinstance(research_data, list) and isinstance(focused_research, dict) and "findings" in focused_research:
                    research_data.extend(focused_research["findings"])
                elif isinstance(research_data, dict) and isinstance(focused_research, dict) and "findings" in focused_research:
                    if "findings" in research_data:
                        research_data["findings"].extend(focused_research["findings"])
                    else:
                        research_data["findings"] = focused_research["findings"]
            else:
                research_data = focused_research
                
            log_info(f"Enhanced research data with focused research", "RESEARCH")
        except Exception as e:
            log_warning(f"Focused research failed but continuing: {str(e)}", "RESEARCH")
            # Continue with existing research data
        
        # Generate enhanced sections with retry logic and performance monitoring
        try:
            sections = await generate_sections(
                outline=outline,
                research_results=research_data or {},
                keyword=topic,
                content_type=kwargs.get("content_type", "standard"),
                model=content_model,
                industry=industry,
                add_case_studies=add_case_studies,
                add_expert_quotes=add_expert_quotes,
                add_real_data=add_real_data,
                enhanced_formatting=enhanced_formatting,
                memory_manager=self.memory_manager if self.has_memory_manager else None
            )
            
            # Calculate and log generation time
            generation_time = time.time() - content_start_time
            log_info(f"Enhanced content generated in {generation_time:.2f} seconds", "CONTENT")
            
            global_agent_activities["Content Agent"]["status"] = "Completed"
            global_agent_activities["Content Agent"]["output"] = f"Generated enhanced content with {len(outline) if outline else 0} sections in {generation_time:.2f}s"
            
        except Exception as e:
            log_error(f"Error generating enhanced content sections: {str(e)}", "CONTENT")
            
            # Fallback to simpler model if premium model failed
            if content_model == "gpt-4":
                log_warning("Falling back to gpt-3.5-turbo after premium model failure", "CONTENT")
                try:
                    sections = await generate_sections(
                        outline=outline,
                        research_results=research_data or {},
                        keyword=topic,
                        content_type=kwargs.get("content_type", "standard"),
                        model="gpt-3.5-turbo",
                        industry=industry,
                        add_case_studies=add_case_studies,
                        add_expert_quotes=add_expert_quotes,
                        add_real_data=add_real_data,
                        enhanced_formatting=enhanced_formatting,
                        memory_manager=self.memory_manager if self.has_memory_manager else None
                    )
                    global_agent_activities["Content Agent"]["status"] = "Completed"
                    global_agent_activities["Content Agent"]["output"] = "Generated enhanced content with fallback model"
                except Exception as fallback_error:
                    log_error(f"Fallback enhanced content generation failed: {str(fallback_error)}", "CONTENT")
                    
                    # Try one more time with basic content generation (no enhancements)
                    try:
                        log_warning("Falling back to basic content generation without enhancements", "CONTENT")
                        sections = await generate_sections(
                            outline=outline,
                            research_results=research_data or {},
                            keyword=topic,
                            content_type=kwargs.get("content_type", "standard"),
                            model="gpt-3.5-turbo"
                        )
                        global_agent_activities["Content Agent"]["status"] = "Completed with basic features"
                        global_agent_activities["Content Agent"]["output"] = "Generated basic content after enhanced content failures"
                    except Exception as basic_error:
                        log_error(f"Basic content generation also failed: {str(basic_error)}", "CONTENT")
                        sections = self._generate_minimal_sections(outline, topic)
                        global_agent_activities["Content Agent"]["status"] = "Failed"
                        global_agent_activities["Content Agent"]["output"] = "Generated minimal content after all failures"
            else:
                # Try basic content generation if enhanced generation failed
                try:
                    log_warning("Falling back to basic content generation", "CONTENT")
                    sections = await generate_sections(
                        outline=outline,
                        research_results=research_data or {},
                        keyword=topic,
                        content_type=kwargs.get("content_type", "standard"),
                        model=content_model
                    )
                    global_agent_activities["Content Agent"]["status"] = "Completed with basic features"
                    global_agent_activities["Content Agent"]["output"] = "Generated basic content after enhanced content failure"
                except Exception as basic_error:
                    log_error(f"Basic content generation also failed: {str(basic_error)}", "CONTENT")
                    sections = self._generate_minimal_sections(outline, topic)
                    global_agent_activities["Content Agent"]["status"] = "Failed"
                    global_agent_activities["Content Agent"]["output"] = "Generated minimal content after all failures"
        
        # Humanize content with monitoring and error handling
        global_agent_activities["Humanizer Agent"] = {
            "status": "Running",
            "output": "Humanizing content"
        }
        log_info("Applying human-like writing style", "HUMANIZER")
        
        humanize_start_time = time.time()
        try:
            humanized = await humanize_content(
                content=sections,
                brand_voice=kwargs.get("brand_voice", ""),
                target_audience=kwargs.get("target_audience", "")
            )
            
            # Calculate and log humanization time
            humanize_time = time.time() - humanize_start_time
            log_info(f"Content humanized in {humanize_time:.2f} seconds", "HUMANIZER")
            
            global_agent_activities["Humanizer Agent"]["status"] = "Completed"
            global_agent_activities["Humanizer Agent"]["output"] = f"Content humanized in {humanize_time:.2f}s"
            
        except Exception as e:
            log_error(f"Error humanizing content: {str(e)}", "HUMANIZER")
            # Use original content if humanization fails
            humanized = sections
            global_agent_activities["Humanizer Agent"]["status"] = "Failed"
            global_agent_activities["Humanizer Agent"]["output"] = "Using original content due to humanization failure"
        
        # Validate content
        global_agent_activities["Quality Agent"] = {
            "status": "Running",
            "output": "Validating content quality"
        }
        log_info("Validating content", "QUALITY")
        try:
            # Extract company context from kwargs or use default
            company_context = kwargs.get("business_context", {})
            if not isinstance(company_context, str):
                company_context = json.dumps(company_context)
            
            validation_result = await self.validator_agent.validate_content(
                content=humanized,
                company_context=company_context
            )
            global_agent_activities["Quality Agent"]["status"] = "Completed"
        except Exception as e:
            log_warning(f"Content validation failed: {str(e)}")
            validation_result = {
                "is_valid": False,
                "issues": str(e),
                "readability": 0,
                "seo_score": 0,
                "engagement_score": 0
            }
            global_agent_activities["Quality Agent"]["status"] = "Failed"
        if not validation_result["is_valid"]:
            if "issues" in validation_result:
                log_warning(f"Content validation failed: {validation_result['issues']}")
                global_agent_activities["Quality Agent"]["status"] = "Failed"
                global_agent_activities["Quality Agent"]["output"] = f"Content rejected: {validation_result['issues']}"
                
                # If the content is off-topic (not about web accessibility), regenerate with proper focus
                if "web accessibility" in validation_result.get("issues", "").lower() or "off-topic" in validation_result.get("issues", "").lower():
                    log_warning(f"Content is off-topic but we'll keep it and add accessibility angle.")
                    
                    # Add a message to the activities to inform the user
                    global_agent_activities["Quality Agent"]["status"] = "Warning"
                    global_agent_activities["Quality Agent"]["output"] = "Content may need more accessibility focus but will proceed"
                    
                    # Don't waste API calls by regenerating content
                    # Instead, we'll just accept it with a warning and let user decide if they want to keep it
            else:
                log_warning("Content validation failed without specific issues provided")
                global_agent_activities["Quality Agent"]["status"] = "Warning"
        else:
            global_agent_activities["Quality Agent"]["status"] = "Completed"
        
        # Calculate generation time
        import time
        total_generation_time = time.time() - content_start_time
        
        # Create enhancement data based on what was included
        from src.utils.openai_blog_writer import EnhancementData
        enhancement_data = EnhancementData(
            industry=industry,
            has_enhanced_formatting=enhanced_formatting
        )
        
        # Detect features in the content
        has_case_studies = "CASE STUDY:" in humanized
        has_expert_quotes = "EXPERT QUOTE:" in humanized or "> " in humanized
        has_real_data = "STAT:" in humanized or "📊" in humanized
        
        # Create blog post with enhanced features
        # Extract readability score as a float
        readability_score = 0.0
        if isinstance(validation_result.get("readability", 0), dict):
            # If it's a dict, use an average of available metrics
            readability_dict = validation_result.get("readability", {})
            if readability_dict and len(readability_dict) > 0:
                readability_values = [value for value in readability_dict.values() if isinstance(value, (int, float))]
                if readability_values:
                    readability_score = sum(readability_values) / len(readability_values)
        elif isinstance(validation_result.get("readability", 0), (int, float)):
            readability_score = float(validation_result.get("readability", 0))
        
        # Create metrics
        metrics = ContentMetrics(
            readability_score=readability_score,
            seo_score=float(validation_result.get("seo_score", 0)),
            engagement_score=float(validation_result.get("engagement", 0)),
            has_real_data=has_real_data,
            has_case_studies=has_case_studies,
            has_expert_quotes=has_expert_quotes,
            enhanced_formatting=enhanced_formatting
        )
        
        # Create the blog post
        blog_post = BlogPost(
            title=outline[0] if outline else f"Complete Guide to {topic}",  # First line is title
            content=humanized,
            keywords=[topic] + (keywords or []),  # Combine topic with generated keywords
            outline=outline,
            industry=industry,
            enhancement_data=enhancement_data,
            generation_time=total_generation_time,
            metrics=metrics
        )
        
        # Store in memory if available
        if self.has_memory_manager:
            try:
                await self.memory_manager.store_blog_post(blog_post)
            except Exception as e:
                log_warning(f"Failed to store in memory: {str(e)}")
        
        return blog_post
    
    async def analyze_blog_post(self, content: str) -> Dict[str, Any]:
        """Analyze a blog post for quality and metrics.
        
        Args:
            content: Blog post content to analyze
            
        Returns:
            Analysis results and metrics
        """
        return await analyze_content(content)
    
    def _is_complex_topic(self, topic: str, outline: List[str], research_data: Dict) -> bool:
        """
        Determine if a topic is complex and requires premium model processing.
        
        Args:
            topic: The main topic
            outline: The content outline
            research_data: Research findings
            
        Returns:
            True if topic is complex, False otherwise
        """
        # Check topic length - longer topics tend to be more complex
        if len(topic.split()) > 4:
            return True
            
        # Check if outline has many sections (indicating complexity)
        if outline and len(outline) > 6:
            return True
            
        # Check if research data contains technical terms
        complex_indicators = [
            "technical", "advanced", "complex", "comprehensive", 
            "detailed", "in-depth", "analysis", "compliance"
        ]
        
        # Check topic for complexity indicators
        if any(indicator in topic.lower() for indicator in complex_indicators):
            return True
            
        # Check research data for complexity
        if research_data and 'findings' in research_data:
            findings = research_data['findings']
            if isinstance(findings, list) and len(findings) > 0:
                # Check first few findings for complexity indicators
                for finding in findings[:3]:
                    if isinstance(finding, dict) and 'content' in finding:
                        content = finding['content']
                        if any(indicator in content.lower() for indicator in complex_indicators):
                            return True
        
        return False
        
    def _generate_minimal_sections(self, outline: List[str], topic: str) -> str:
        """
        Generate minimal content sections as a fallback when generation fails.
        
        Args:
            outline: The content outline
            topic: The main topic
            
        Returns:
            Basic content with outline structure
        """
        if not outline:
            # Create a basic outline if none exists
            outline = [
                f"# Complete Guide to {topic}",
                "## Introduction",
                f"## What is {topic}?",
                f"## Benefits of {topic}",
                f"## How to Implement {topic}",
                "## Conclusion"
            ]
            
        content = []
        for section in outline:
            content.append(section)
            # Add placeholder content for each section
            if section.startswith("#"):
                level = section.count("#")
                if level == 1:  # Title
                    content.append(f"\nThis comprehensive guide covers everything you need to know about {topic}.\n")
                elif "introduction" in section.lower() or "overview" in section.lower():
                    content.append(f"\n{topic} is an important subject that many people want to learn more about. This guide will cover the key aspects and provide valuable insights.\n")
                elif "what is" in section.lower():
                    content.append(f"\n{topic} refers to an important concept in this field. Understanding the basics is essential before diving into more complex aspects.\n")
                elif "benefits" in section.lower() or "advantages" in section.lower():
                    content.append(f"\nImplementing {topic} offers several important benefits:\n- Improved efficiency\n- Better results\n- Enhanced performance\n")
                elif "how to" in section.lower() or "implementation" in section.lower():
                    content.append(f"\nHere are the basic steps to implement {topic}:\n1. Start with research\n2. Create a plan\n3. Execute carefully\n4. Monitor results\n")
                elif "conclusion" in section.lower():
                    content.append(f"\nIn conclusion, {topic} is valuable for many applications. By following the guidelines in this article, you can effectively utilize it in your own work.\n")
                else:
                    content.append(f"\nThis section covers important aspects of {topic} that are relevant to understand the complete picture.\n")
        
        return "\n".join(content)
    
    async def improve_blog_post(self, blog_post: BlogPost) -> BlogPost:
        """Improve an existing blog post.
        
        Args:
            blog_post: Blog post to improve
            
        Returns:
            Improved blog post
        """
        import time
        start_time = time.time()
        log_info(f"Starting improvement for blog post: {blog_post.title}", "IMPROVE")
        
        # Run analysis in parallel with improvement preparation
        analysis_task = asyncio.create_task(self.analyze_blog_post(blog_post.content))
        
        # Wait for analysis to complete
        analysis = await analysis_task
        log_info(f"Analysis completed in {time.time() - start_time:.2f} seconds", "IMPROVE")
        
        # Apply improvements based on analysis
        improved_content = await self.humanizer_agent.apply_improvements(
            blog_post.content,
            analysis
        )
        
        # Update blog post
        blog_post.content = improved_content
        blog_post.metrics = ContentMetrics(
            readability_score=analysis.get("readability", 0),
            seo_score=analysis.get("seo_score", 0),
            engagement_score=analysis.get("engagement", 0)
        )
        
        log_info(f"Blog post improved in {time.time() - start_time:.2f} seconds", "IMPROVE")
        return blog_post
        
    async def get_next_keyword_from_topology(self) -> str:
        """Get the next keyword from the keyword topology for optimal SEO coverage.
        
        Returns:
            A keyword that optimizes for complete coverage of all available keywords
        """
        try:
            if not self.has_keyword_topology or not self.keyword_topology:
                log_warning("Keyword topology not available, using default keyword selection", "KEYWORD")
                return "Web Accessibility"
                
            # First, update the topology to make sure it has all the latest keywords
            await self.keyword_topology.update_topology()
            
            # Get the next keyword that optimizes coverage
            keyword = self.keyword_topology.get_next_keyword()
            log_info(f"Selected next keyword from topology: {keyword}", "KEYWORD")
            return keyword
            
        except Exception as e:
            log_error(f"Error getting next keyword from topology: {str(e)}", "KEYWORD")
            return "Web Accessibility"  # Fallback to default
            
    async def get_topology_report(self) -> Dict[str, Any]:
        """Get a report on the current keyword topology coverage.
        
        Returns:
            Dictionary with coverage statistics
        """
        try:
            if not self.has_keyword_topology or not self.keyword_topology:
                log_warning("Keyword topology not available, cannot generate report", "KEYWORD")
                return {"error": "Keyword topology not available"}
                
            # Get the coverage report from topology
            report = self.keyword_topology.get_coverage_report()
            
            # Add timestamp
            report["timestamp"] = datetime.datetime.now().isoformat()
            report["status"] = "success"
            
            log_info(f"Generated keyword topology report with {report.get('total_keywords', 0)} keywords", "KEYWORD")
            return report
            
        except Exception as e:
            log_error(f"Error generating topology report: {str(e)}", "KEYWORD")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": datetime.datetime.now().isoformat()
            }

# Async wrapper for blog post generation
async def generate_blog_post(**kwargs) -> BlogPost:
    """Generate a blog post using the agent orchestrator.
    
    Args:
        **kwargs: Parameters for blog post generation including:
            - topic: Main topic for the blog post (required)
            - business_type: Type of business (optional)
            - content_goal: Primary goal of the content (optional)
            - research_depth: Depth of research (optional)
            - web_references: Number of web references to use (optional)
            - content_type: Type of content to generate (optional)
            - brand_voice: Description of brand voice (optional)
            - target_audience: Description of target audience (optional)
            
            # Enhanced content generation options
            - industry: Target industry for industry-specific content (optional)
            - add_case_studies: Whether to include case studies (optional, default: True)
            - add_expert_quotes: Whether to include expert quotes (optional, default: True)
            - add_real_data: Whether to include real data and statistics (optional, default: True) 
            - enhanced_formatting: Whether to use enhanced formatting (optional, default: True)
        
    Returns:
        Generated blog post
    """
    orchestrator = AgentOrchestrator()
    # Extract topic from kwargs or use default
    topic = kwargs.pop("topic", None)
    if topic is None:
        # If no topic provided, get one from the keyword topology
        log_info("No topic provided, using keyword topology to select next keyword", "KEYWORD")
        topic = await orchestrator.get_next_keyword_from_topology()
        log_info(f"Auto-selected topic: {topic}", "KEYWORD")
    return await orchestrator.generate_blog_post(topic=topic, **kwargs)
    
# Get the next recommended keyword for blog post generation
async def get_next_recommended_keyword() -> str:
    """Get the next recommended keyword for blog post generation based on the keyword topology.
    
    Returns:
        A keyword that optimizes for complete coverage of all available keywords
    """
    orchestrator = AgentOrchestrator()
    return await orchestrator.get_next_keyword_from_topology()
    
# Get a report on keyword topology coverage
async def get_keyword_topology_report() -> Dict[str, Any]:
    """Get a report on the current keyword topology coverage.
    
    Returns:
        Dictionary with coverage statistics
    """
    orchestrator = AgentOrchestrator()
    return await orchestrator.get_topology_report()
