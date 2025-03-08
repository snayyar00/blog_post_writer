"""
Advanced research agent that dynamically leverages multiple AI providers
(Perplexity, Anthropic, OpenAI) for comprehensive content research with
SEO optimization capabilities.
"""

import os
import json
import random
from typing import List, Dict, Any, Optional, Union, Literal
import requests
from datetime import datetime
from enum import Enum
import tiktoken
from src.utils.cost_tracker import log_api_call

class AIProvider(Enum):
    """Enum for supported AI providers."""
    PERPLEXITY = "perplexity"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AUTO = "auto"  # Automatically select the best provider for the task

class ResearchMode(Enum):
    """Research modes for different content needs."""
    DEEP = "deep"  # In-depth research with extensive sources
    SEO = "seo"    # SEO-focused research with keyword analysis
    TREND = "trend" # Trending topics and current insights
    COMPETITOR = "competitor" # Competitor analysis focus

class ResearchAgent:
    """Advanced research agent that dynamically leverages multiple AI providers."""
    
    def __init__(self,
                 perplexity_api_key: Optional[str] = None,
                 anthropic_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 default_provider: AIProvider = AIProvider.AUTO):
        """
        Initialize the research agent with available API keys.
        
        Args:
            perplexity_api_key: API key for Perplexity
            anthropic_api_key: API key for Anthropic
            openai_api_key: API key for OpenAI
            default_provider: Default AI provider to use
        """
        self.api_keys = {
            AIProvider.PERPLEXITY: perplexity_api_key,
            AIProvider.ANTHROPIC: anthropic_api_key,
            AIProvider.OPENAI: openai_api_key
        }
        
        self.default_provider = default_provider
        self.perplexity_base_url = "https://api.perplexity.ai"
        
        # Track usage for load balancing
        self.usage_stats = {provider: 0 for provider in AIProvider}
        
        # SEO-specific jargon for enhancing content
        self.seo_jargon = [
            "search intent optimization",
            "keyword cannibalization",
            "semantic search relevance",
            "topical authority building",
            "E-E-A-T signals",
            "SERP feature optimization",
            "content gap analysis",
            "zero-click optimization",
            "entity optimization",
            "passage indexing strategy",
            "NLP-optimized content",
            "user experience signals",
            "dwell time optimization",
            "featured snippet targeting",
            "content depth metrics"
        ]
        
        # Initialize provider-specific clients if needed
        if anthropic_api_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            except ImportError:
                print("Anthropic package not installed. Run 'pip install anthropic' to use Anthropic.")
                self.anthropic_client = None
        else:
            self.anthropic_client = None
            
        if openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_api_key)
            except ImportError:
                print("OpenAI package not installed. Run 'pip install openai' to use OpenAI.")
                self.openai_client = None
        else:
            self.openai_client = None
    
    def _select_provider(self, task_type: str) -> AIProvider:
        """
        Intelligently select the best provider for a given task.
        
        Args:
            task_type: Type of task (research, seo, competitor_analysis, etc.)
            
        Returns:
            Selected AI provider
        """
        if self.default_provider != AIProvider.AUTO:
            # Use default provider if specified and available
            if self.api_keys[self.default_provider]:
                return self.default_provider
        
        # Provider specialization mapping
        specializations = {
            "research": [AIProvider.PERPLEXITY, AIProvider.ANTHROPIC, AIProvider.OPENAI],
            "seo": [AIProvider.OPENAI, AIProvider.PERPLEXITY, AIProvider.ANTHROPIC],
            "competitor_analysis": [AIProvider.ANTHROPIC, AIProvider.PERPLEXITY, AIProvider.OPENAI],
            "trend_analysis": [AIProvider.PERPLEXITY, AIProvider.OPENAI, AIProvider.ANTHROPIC]
        }
        
        # Get preferred providers for this task
        preferred_providers = specializations.get(task_type,
            [AIProvider.PERPLEXITY, AIProvider.ANTHROPIC, AIProvider.OPENAI])
        
        # Filter to available providers
        available_providers = [p for p in preferred_providers if self.api_keys[p]]
        
        if not available_providers:
            # No preferred providers available, use any available
            available_providers = [p for p in AIProvider if p != AIProvider.AUTO and self.api_keys[p]]
            
        if not available_providers:
            raise ValueError("No AI providers available. Please provide at least one API key.")
            
        # Select provider with lowest usage (simple load balancing)
        return min(available_providers, key=lambda p: self.usage_stats[p])
    
    def research_topic(self,
                      topic: str,
                      business_context: Optional[Dict] = None,
                      competitor_blogs: Optional[List[Dict]] = None,
                      depth: int = 3,
                      mode: Union[ResearchMode, str] = ResearchMode.DEEP,
                      provider: Optional[Union[AIProvider, str]] = None) -> List[Dict]:
        """
        Perform comprehensive research on a topic using the best available AI provider.
        
        Args:
            topic: The main topic to research
            business_context: Optional business context to tailor research
            competitor_blogs: Optional list of competitor blog content
            depth: How many levels deep to research (1-5)
            mode: Research mode (deep, seo, trend, competitor)
            provider: Specific provider to use (overrides automatic selection)
            
        Returns:
            List of research findings with sources
        """
        # Convert string mode to enum if needed
        if isinstance(mode, str):
            try:
                mode = ResearchMode(mode.lower())
            except ValueError:
                mode = ResearchMode.DEEP
                
        # Convert string provider to enum if needed
        if isinstance(provider, str) and provider:
            try:
                provider = AIProvider(provider.lower())
            except ValueError:
                provider = None
        
        # Select provider if not specified
        if not provider:
            task_type = "research"
            if mode == ResearchMode.SEO:
                task_type = "seo"
            elif mode == ResearchMode.TREND:
                task_type = "trend_analysis"
            elif mode == ResearchMode.COMPETITOR:
                task_type = "competitor_analysis"
                
            provider = self._select_provider(task_type)
        
        # Track usage
        self.usage_stats[provider] = self.usage_stats.get(provider, 0) + 1
        
        # Dispatch to appropriate provider method
        if provider == AIProvider.PERPLEXITY:
            return self._research_with_perplexity(topic, business_context, competitor_blogs, depth, mode)
        elif provider == AIProvider.ANTHROPIC:
            return self._research_with_anthropic(topic, business_context, competitor_blogs, depth, mode)
        elif provider == AIProvider.OPENAI:
            return self._research_with_openai(topic, business_context, competitor_blogs, depth, mode)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _research_with_perplexity(self,
                                topic: str,
                                business_context: Optional[Dict],
                                competitor_blogs: Optional[List[Dict]],
                                depth: int,
                                mode: ResearchMode) -> List[Dict]:
        """Research using Perplexity API."""
        api_key = self.api_keys[AIProvider.PERPLEXITY]
        if not api_key:
            raise ValueError("Perplexity API key not provided")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json",
            "content-type": "application/json"
        }
        
        # Build a more targeted research query based on business context and mode
        research_query = f"Comprehensive research about {topic}"
        
        # Add business context if available
        if business_context:
            business_type = business_context.get('business_type', '')
            industry = business_context.get('industry', '')
            target_audience = business_context.get('target_audience', '')
            
            if business_type or industry:
                research_query += f" specifically for {business_type or industry} businesses"
            
            if target_audience:
                research_query += f" targeting {target_audience}"
        
        # Add competitor insights if available
        competitor_insights = ""
        if competitor_blogs and len(competitor_blogs) > 0:
            competitor_insights = "\n\nCompetitor content analysis:\n"
            for i, blog in enumerate(competitor_blogs[:3]):
                competitor_insights += f"Competitor {i+1}: {blog.get('title', 'Untitled')}\n"
                competitor_insights += f"Key points: {blog.get('summary', 'No summary available')}\n"
        
        # Customize system prompt based on research mode
        system_prompt = "You are a specialized research assistant for content marketing."
        user_prompt_suffix = "Include market data, statistics, expert opinions, and actionable insights. Focus on practical applications and business value."
        
        if mode == ResearchMode.SEO:
            # Add SEO jargon to make content more enticing
            seo_terms = random.sample(self.seo_jargon, min(5, len(self.seo_jargon)))
            seo_jargon_str = ", ".join(seo_terms)
            
            system_prompt = "You are an elite SEO content strategist with expertise in search optimization and content marketing."
            user_prompt_suffix = f"Focus on SEO optimization strategies incorporating concepts like {seo_jargon_str}. Include keyword research, search intent analysis, and content structure recommendations. Provide actionable insights for ranking improvement."
            
        elif mode == ResearchMode.TREND:
            system_prompt = "You are a trend analysis expert specializing in identifying emerging patterns and opportunities."
            user_prompt_suffix = "Focus on current trends, emerging patterns, and future predictions. Include recent statistics, market shifts, and actionable insights for staying ahead of the curve."
            
        elif mode == ResearchMode.COMPETITOR:
            system_prompt = "You are a competitive intelligence specialist with expertise in market positioning and competitor analysis."
            user_prompt_suffix = "Focus on competitive landscape analysis, market positioning strategies, and differentiation opportunities. Provide actionable insights for competitive advantage."
        
        # Prepare messages for chat completions API
        system_content = system_prompt + " Provide comprehensive, factual information with sources that is directly relevant to the user's business context."
        user_content = f"{research_query}. {user_prompt_suffix} {competitor_insights}\n\nCite your sources."
        
        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        # Count tokens for cost tracking (approximate)
        encoding = tiktoken.encoding_for_model("cl100k_base")  # General purpose encoding
        input_tokens = len(encoding.encode(system_content)) + len(encoding.encode(user_content))
        
        # Use a more cost-effective model when appropriate
        model = "sonar-medium-online"  # Less expensive than sonar-deep-research
        if mode == ResearchMode.DEEP or depth > 3:
            model = "sonar-deep-research"  # Use deep research only when necessary
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            research_data = response.json()
            
            # Extract content and sources from the response
            findings = []
            if "choices" in research_data and research_data["choices"]:
                content = research_data["choices"][0]["message"]["content"]
                output_tokens = len(encoding.encode(content))
                
                # Log API call for cost tracking
                log_api_call(
                    provider="perplexity",
                    model=model,
                    operation="research",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                
                # Extract sources from the content (improved implementation)
                sources = []
                in_sources_section = False
                
                for line in content.split("\n"):
                    if line.lower().startswith(("source", "reference", "citation", "[")):
                        in_sources_section = True
                        sources.append(line)
                    elif in_sources_section and line.strip() and not line.startswith("#"):
                        # Continue adding lines that appear to be part of sources
                        sources.append(line)
                    elif in_sources_section and not line.strip():
                        # Empty line might end the sources section
                        in_sources_section = False
                
                findings.append({
                    "content": content,
                    "sources": sources,
                    "confidence": 0.9,  # Default confidence for Perplexity API
                    "provider": "perplexity",
                    "model": model,
                    "tokens": {"input": input_tokens, "output": output_tokens},
                    "timestamp": datetime.now().isoformat()
                })
                
            return findings
            
        except Exception as e:
            print(f"Error during Perplexity research: {str(e)}")
            return []
    
    def _research_with_anthropic(self,
                               topic: str,
                               business_context: Optional[Dict],
                               competitor_blogs: Optional[List[Dict]],
                               depth: int,
                               mode: ResearchMode) -> List[Dict]:
        """Research using Anthropic API."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
            
        # Build research query similar to Perplexity but tailored for Anthropic
        research_query = f"Comprehensive research about {topic}"
        
        # Add business context if available
        if business_context:
            business_type = business_context.get('business_type', '')
            industry = business_context.get('industry', '')
            target_audience = business_context.get('target_audience', '')
            
            if business_type or industry:
                research_query += f" specifically for {business_type or industry} businesses"
            
            if target_audience:
                research_query += f" targeting {target_audience}"
        
        # Add competitor insights if available
        competitor_insights = ""
        if competitor_blogs and len(competitor_blogs) > 0:
            competitor_insights = "\n\nCompetitor content analysis:\n"
            for i, blog in enumerate(competitor_blogs[:3]):
                competitor_insights += f"Competitor {i+1}: {blog.get('title', 'Untitled')}\n"
                competitor_insights += f"Key points: {blog.get('summary', 'No summary available')}\n"
        
        # Customize system prompt based on research mode
        system_prompt = "You are a specialized research assistant for content marketing."
        user_prompt_suffix = "Include market data, statistics, expert opinions, and actionable insights. Focus on practical applications and business value."
        
        if mode == ResearchMode.SEO:
            # Add SEO jargon to make content more enticing
            seo_terms = random.sample(self.seo_jargon, min(5, len(self.seo_jargon)))
            seo_jargon_str = ", ".join(seo_terms)
            
            system_prompt = "You are an elite SEO content strategist with expertise in search optimization and content marketing."
            user_prompt_suffix = f"Focus on SEO optimization strategies incorporating concepts like {seo_jargon_str}. Include keyword research, search intent analysis, and content structure recommendations. Provide actionable insights for ranking improvement."
            
        elif mode == ResearchMode.TREND:
            system_prompt = "You are a trend analysis expert specializing in identifying emerging patterns and opportunities."
            user_prompt_suffix = "Focus on current trends, emerging patterns, and future predictions. Include recent statistics, market shifts, and actionable insights for staying ahead of the curve."
            
        elif mode == ResearchMode.COMPETITOR:
            system_prompt = "You are a competitive intelligence specialist with expertise in market positioning and competitor analysis."
            user_prompt_suffix = "Focus on competitive landscape analysis, market positioning strategies, and differentiation opportunities. Provide actionable insights for competitive advantage."
        
        # Prepare messages and system prompt
        system_content = system_prompt + " Provide comprehensive, factual information with sources that is directly relevant to the user's business context."
        user_content = f"{research_query}. {user_prompt_suffix} {competitor_insights}\n\nCite your sources."
        
        # Count tokens for cost tracking (approximate since Claude uses a different tokenizer)
        # Using tiktoken as an approximation
        encoding = tiktoken.encoding_for_model("cl100k_base")  # Claude-compatible encoding
        input_tokens = len(encoding.encode(system_content)) + len(encoding.encode(user_content))
        
        try:
            # Use cheaper model (claude-3-haiku) instead of opus
            model = "claude-3-haiku-20240307"
            
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_content,
                messages=[
                    {"role": "user", "content": user_content}
                ]
            )
            
            content = response.content[0].text
            output_tokens = len(encoding.encode(content))
            
            # Log API call for cost tracking
            log_api_call(
                provider="anthropic",
                model=model,
                operation="research",
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            # Extract sources from the content
            sources = []
            in_sources_section = False
            
            for line in content.split("\n"):
                if line.lower().startswith(("source", "reference", "citation", "[")):
                    in_sources_section = True
                    sources.append(line)
                elif in_sources_section and line.strip() and not line.startswith("#"):
                    # Continue adding lines that appear to be part of sources
                    sources.append(line)
                elif in_sources_section and not line.strip():
                    # Empty line might end the sources section
                    in_sources_section = False
            
            return [{
                "content": content,
                "sources": sources,
                "confidence": 0.90,  # Slightly lower confidence for haiku vs opus
                "provider": "anthropic",
                "model": model,
                "tokens": {"input": input_tokens, "output": output_tokens},
                "timestamp": datetime.now().isoformat()
            }]
            
        except Exception as e:
            print(f"Error during Anthropic research: {str(e)}")
            return []
    
    def _research_with_openai(self,
                            topic: str,
                            business_context: Optional[Dict],
                            competitor_blogs: Optional[List[Dict]],
                            depth: int,
                            mode: ResearchMode) -> List[Dict]:
        """Research using OpenAI API."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
            
        # Build research query similar to other providers but tailored for OpenAI
        research_query = f"Comprehensive research about {topic}"
        
        # Add business context if available
        if business_context:
            business_type = business_context.get('business_type', '')
            industry = business_context.get('industry', '')
            target_audience = business_context.get('target_audience', '')
            
            if business_type or industry:
                research_query += f" specifically for {business_type or industry} businesses"
            
            if target_audience:
                research_query += f" targeting {target_audience}"
        
        # Add competitor insights if available
        competitor_insights = ""
        if competitor_blogs and len(competitor_blogs) > 0:
            competitor_insights = "\n\nCompetitor content analysis:\n"
            for i, blog in enumerate(competitor_blogs[:3]):
                competitor_insights += f"Competitor {i+1}: {blog.get('title', 'Untitled')}\n"
                competitor_insights += f"Key points: {blog.get('summary', 'No summary available')}\n"
        
        # Customize system prompt based on research mode
        system_prompt = "You are a specialized research assistant for content marketing."
        user_prompt_suffix = "Include market data, statistics, expert opinions, and actionable insights. Focus on practical applications and business value."
        
        if mode == ResearchMode.SEO:
            # Add SEO jargon to make content more enticing
            seo_terms = random.sample(self.seo_jargon, min(5, len(self.seo_jargon)))
            seo_jargon_str = ", ".join(seo_terms)
            
            system_prompt = "You are an elite SEO content strategist with expertise in search optimization and content marketing."
            user_prompt_suffix = f"Focus on SEO optimization strategies incorporating concepts like {seo_jargon_str}. Include keyword research, search intent analysis, and content structure recommendations. Provide actionable insights for ranking improvement."
            
        elif mode == ResearchMode.TREND:
            system_prompt = "You are a trend analysis expert specializing in identifying emerging patterns and opportunities."
            user_prompt_suffix = "Focus on current trends, emerging patterns, and future predictions. Include recent statistics, market shifts, and actionable insights for staying ahead of the curve."
            
        elif mode == ResearchMode.COMPETITOR:
            system_prompt = "You are a competitive intelligence specialist with expertise in market positioning and competitor analysis."
            user_prompt_suffix = "Focus on competitive landscape analysis, market positioning strategies, and differentiation opportunities. Provide actionable insights for competitive advantage."
        
        # Prepare messages
        system_message = {"role": "system", "content": system_prompt + " Provide comprehensive, factual information with sources that is directly relevant to the user's business context."}
        user_message = {"role": "user", "content": f"{research_query}. {user_prompt_suffix} {competitor_insights}\n\nCite your sources."}
        messages = [system_message, user_message]
        
        # Count tokens for cost tracking
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        input_tokens = len(encoding.encode(system_message["content"])) + len(encoding.encode(user_message["content"]))
        
        try:
            # Use cheaper model (gpt-4o-mini) instead of gpt-4-turbo
            model = "gpt-4o-mini"
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            output_tokens = len(encoding.encode(content))
            
            # Log API call for cost tracking
            log_api_call(
                provider="openai",
                model=model,
                operation="research",
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            # Extract sources from the content
            sources = []
            in_sources_section = False
            
            for line in content.split("\n"):
                if line.lower().startswith(("source", "reference", "citation", "[")):
                    in_sources_section = True
                    sources.append(line)
                elif in_sources_section and line.strip() and not line.startswith("#"):
                    # Continue adding lines that appear to be part of sources
                    sources.append(line)
                elif in_sources_section and not line.strip():
                    # Empty line might end the sources section
                    in_sources_section = False
            
            return [{
                "content": content,
                "sources": sources,
                "confidence": 0.92,
                "provider": "openai",
                "model": model,
                "tokens": {"input": input_tokens, "output": output_tokens},
                "timestamp": datetime.now().isoformat()
            }]
            
        except Exception as e:
            print(f"Error during OpenAI research: {str(e)}")
            return []
            
    def _get_company_context_perplexity(self, company_name: str) -> Dict:
        """Get company context using Perplexity API."""
        api_key = self.api_keys[AIProvider.PERPLEXITY]
        if not api_key:
            raise ValueError("Perplexity API key not provided")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        query = {
            "query": f"""Detailed analysis of {company_name} including:
            1. Company history and background
            2. Products and services
            3. Market position and competitors
            4. Recent news and developments
            5. Company culture and values
            6. Financial performance
            7. Future outlook""",
            "max_tokens": 3000
        }
        
        try:
            response = requests.post(
                f"{self.perplexity_base_url}/query",
                headers=headers,
                json=query
            )
            response.raise_for_status()
            
            company_data = response.json()
            return {
                "context": company_data.get("answer", ""),
                "sources": company_data.get("sources", []),
                "last_updated": company_data.get("timestamp", ""),
                "provider": "perplexity"
            }
            
        except Exception as e:
            print(f"Error getting company context from Perplexity: {str(e)}")
            return {}

    def _get_company_context_anthropic(self, company_name: str) -> Dict:
        """Get company context using Anthropic API."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
            
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=3000,
                system="You are a business intelligence analyst specializing in company research.",
                messages=[
                    {"role": "user", "content": f"""Detailed analysis of {company_name} including:
                    1. Company history and background
                    2. Products and services
                    3. Market position and competitors
                    4. Recent news and developments
                    5. Company culture and values
                    6. Financial performance
                    7. Future outlook
                    
                    Provide comprehensive information with sources."""}
                ]
            )
            
            content = response.content[0].text
            
            # Extract sources
            sources = []
            for line in content.split("\n"):
                if line.lower().startswith(("source", "reference", "citation", "[")):
                    sources.append(line)
            
            return {
                "context": content,
                "sources": sources,
                "last_updated": datetime.now().isoformat(),
                "provider": "anthropic"
            }
            
        except Exception as e:
            print(f"Error getting company context from Anthropic: {str(e)}")
            return {}

    def _get_company_context_openai(self, company_name: str) -> Dict:
        """Get company context using OpenAI API."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
            
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a business intelligence analyst specializing in company research."},
                    {"role": "user", "content": f"""Detailed analysis of {company_name} including:
                    1. Company history and background
                    2. Products and services
                    3. Market position and competitors
                    4. Recent news and developments
                    5. Company culture and values
                    6. Financial performance
                    7. Future outlook
                    
                    Provide comprehensive information with sources."""}
                ],
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            
            # Extract sources
            sources = []
            for line in content.split("\n"):
                if line.lower().startswith(("source", "reference", "citation", "[")):
                    sources.append(line)
            
            return {
                "context": content,
                "sources": sources,
                "last_updated": datetime.now().isoformat(),
                "provider": "openai"
            }
            
        except Exception as e:
            print(f"Error getting company context from OpenAI: {str(e)}")
            return {}
    
    def get_company_context(self, company_name: str, provider: Optional[Union[AIProvider, str]] = None) -> Dict:
        """
        Get detailed context about a company using the best available AI provider.
        
        Args:
            company_name: Name of the company to research
            provider: Specific provider to use (overrides automatic selection)
            
        Returns:
            Dictionary containing company information
        """
        # Convert string provider to enum if needed
        if isinstance(provider, str) and provider:
            try:
                provider = AIProvider(provider.lower())
            except ValueError:
                provider = None
        
        # Select provider if not specified
        if not provider:
            provider = self._select_provider("research")
        
        # Track usage
        self.usage_stats[provider] = self.usage_stats.get(provider, 0) + 1
        
        # Dispatch to appropriate provider method
        if provider == AIProvider.PERPLEXITY:
            return self._get_company_context_perplexity(company_name)
        elif provider == AIProvider.ANTHROPIC:
            return self._get_company_context_anthropic(company_name)
        elif provider == AIProvider.OPENAI:
            return self._get_company_context_openai(company_name)
        else:
            raise ValueError(f"Unsupported provider: {provider}")


def research_topic(keywords: List[str], mode: str = "deep", business_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Research content based on a list of keywords using the best available AI provider.
    
    Args:
        keywords: List of keywords to research
        mode: Research mode ('deep', 'seo', 'trend', 'competitor')
        business_context: Optional business context to tailor research
        
    Returns:
        Dictionary containing research results
    """
    # Get API keys from environment variables
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Check if any API keys are available
    if not any([perplexity_api_key, anthropic_api_key, openai_api_key]):
        print("Warning: No API keys found for research. Using mock data.")
        return {
            "findings": [
                {
                    "content": f"Mock research data for keywords: {', '.join(keywords)}",
                    "sources": ["https://example.com/mock-source"],
                    "confidence": 0.8,
                    "provider": "mock",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "keywords_used": keywords,
            "mode": mode
        }
    
    try:
        # Initialize research agent with all available API keys
        agent = ResearchAgent(
            perplexity_api_key=perplexity_api_key,
            anthropic_api_key=anthropic_api_key,
            openai_api_key=openai_api_key,
            default_provider=AIProvider.AUTO
        )
        
        # Combine keywords into a research query
        main_topic = keywords[0] if keywords else "web accessibility"
        
        # Convert mode string to enum if needed
        research_mode = mode
        if isinstance(mode, str):
            try:
                research_mode = ResearchMode(mode.lower())
            except ValueError:
                research_mode = ResearchMode.DEEP
        
        # Perform research with the specified mode
        findings = agent.research_topic(
            topic=main_topic,
            business_context=business_context,
            mode=research_mode
        )
        
        # If no findings were returned, try with a different provider
        if not findings:
            # Try each provider in sequence until one works
            for provider in [AIProvider.PERPLEXITY, AIProvider.ANTHROPIC, AIProvider.OPENAI]:
                if agent.api_keys[provider]:
                    try:
                        findings = agent.research_topic(
                            topic=main_topic,
                            business_context=business_context,
                            mode=research_mode,
                            provider=provider
                        )
                        if findings:
                            break
                    except Exception as provider_error:
                        print(f"Error with {provider.value}: {str(provider_error)}")
        
        # If still no findings, use a simple fallback
        if not findings:
            findings = [{
                "content": f"Research on {main_topic}:\n\nUnable to retrieve detailed information at this time. Please try again later or refine your search terms.",
                "sources": [],
                "confidence": 0.5,
                "provider": "fallback",
                "timestamp": datetime.now().isoformat()
            }]
        
        return {
            "findings": findings,
            "keywords_used": keywords,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error in research_topic: {str(e)}")
        return {
            "findings": [],
            "keywords_used": keywords,
            "error": str(e),
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
