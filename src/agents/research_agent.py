"""
Advanced research agent that dynamically leverages multiple AI providers
(Perplexity, Anthropic, OpenAI) for comprehensive content research with
SEO optimization capabilities.
"""

import os
import json
import random
from typing import List, Dict, Any, Optional, Union, Literal
import aiohttp
from datetime import datetime
from enum import Enum
from src.utils.cost_tracker import log_api_call
from openai import AsyncOpenAI  # Import AsyncOpenAI instead of OpenAI

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
        """Initialize the research agent with available API keys."""
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
                from src.utils.logging_manager import log_warning
                log_warning("Anthropic package not installed. Run 'pip install anthropic' to use Anthropic.")
                self.anthropic_client = None
        else:
            self.anthropic_client = None
            
        if openai_api_key:
            try:
                self.openai_client = AsyncOpenAI(api_key=openai_api_key)  # Use AsyncOpenAI
            except ImportError:
                from src.utils.logging_manager import log_warning
                log_warning("OpenAI package not installed. Run 'pip install openai' to use OpenAI.")
                self.openai_client = None
        else:
            self.openai_client = None
    
    def _select_provider(self, task_type: str) -> AIProvider:
        """Intelligently select the best provider for a given task."""
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
    
    async def research_topic(self,
                           topic: str,
                           business_context: Optional[Dict] = None,
                           competitor_blogs: Optional[List[Dict]] = None,
                           depth: int = 3,
                           mode: Union[ResearchMode, str] = ResearchMode.DEEP,
                           provider: Optional[Union[AIProvider, str]] = None) -> List[Dict]:
        """Perform comprehensive research on a topic using the best available AI provider."""
        from src.utils.logging_manager import log_info, log_debug
        log_info(f"Starting research on topic: {topic}", "RESEARCH")
        
        # Cache key for this research request
        cache_key = f"{topic}_{mode}_{depth}"
        if hasattr(self, '_research_cache') and cache_key in self._research_cache:
            log_debug("Using cached research results")
            return self._research_cache[cache_key]
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
            return await self._research_with_perplexity(topic, business_context, competitor_blogs, depth, mode)
        elif provider == AIProvider.ANTHROPIC:
            return await self._research_with_anthropic(topic, business_context, competitor_blogs, depth, mode)
        elif provider == AIProvider.OPENAI:
            return await self._research_with_openai(topic, business_context, competitor_blogs, depth, mode)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def _research_with_perplexity(self,
                                topic: str,
                                business_context: Optional[Dict],
                                competitor_blogs: Optional[List[Dict]],
                                depth: int,
                                mode: ResearchMode) -> List[Dict]:
        """Research using Perplexity API."""
        from src.utils.logging_manager import log_info
        log_info("Using Perplexity API for research", "RESEARCH")
        api_key = self.api_keys[AIProvider.PERPLEXITY]
        if not api_key:
            raise ValueError("Perplexity API key not provided")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json",
            "content-type": "application/json"
        }
        
        # Build research query and prompts
        research_query, system_prompt, user_prompt_suffix = self._build_research_prompts(
            topic, business_context, competitor_blogs, mode)
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"{research_query}. {user_prompt_suffix}"
            }
        ]
        
        # Always use the most cost-effective model
        model = "llama-3-sonar-small-online"  # Updated model name for Perplexity
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        try:
            # Debugging payload
            log_debug(f"Perplexity API payload: {json.dumps(payload, indent=2)}", "RESEARCH")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30  # Add timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        log_error(f"Perplexity API error: {response.status}, {error_text}", "RESEARCH")
                    response.raise_for_status()
                    research_data = await response.json()
            
            # Extract content and sources from the response
            findings = []
            if "choices" in research_data and research_data["choices"]:
                content = research_data["choices"][0]["message"]["content"]
                sources = self._extract_sources(content)
                
                findings.append({
                    "content": content,
                    "sources": sources,
                    "confidence": 0.9,  # Default confidence for Perplexity API
                    "provider": "perplexity",
                    "model": model,
                    "tokens": self._count_tokens(content),
                    "timestamp": datetime.now().isoformat()
                })
                
            return findings
            
        except Exception as e:
            from src.utils.logging_manager import log_error
            log_error(f"Error during Perplexity research: {str(e)}")
            return []
    
    async def _research_with_anthropic(self,
                               topic: str,
                               business_context: Optional[Dict],
                               competitor_blogs: Optional[List[Dict]],
                               depth: int,
                               mode: ResearchMode) -> List[Dict]:
        """Research using Anthropic API."""
        from src.utils.logging_manager import log_info
        log_info("Using Anthropic API for research", "RESEARCH")
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
            
        # Build research query and prompts
        research_query, system_prompt, user_prompt_suffix = self._build_research_prompts(
            topic, business_context, competitor_blogs, mode)
        
        try:
            # Use cheaper model (claude-3-haiku) instead of opus
            model = "claude-3-haiku-20240307"
            
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"{research_query}. {user_prompt_suffix}"}
                ]
            )
            
            content = response.content[0].text
            sources = self._extract_sources(content)
            
            return [{
                "content": content,
                "sources": sources,
                "confidence": 0.90,  # Slightly lower confidence for haiku vs opus
                "provider": "anthropic",
                "model": model,
                "tokens": self._count_tokens(content),
                "timestamp": datetime.now().isoformat()
            }]
            
        except Exception as e:
            from src.utils.logging_manager import log_error
            log_error(f"Error during Anthropic research: {str(e)}")
            return []
    
    async def _research_with_openai(self,
                            topic: str,
                            business_context: Optional[Dict],
                            competitor_blogs: Optional[List[Dict]],
                            depth: int,
                            mode: ResearchMode) -> List[Dict]:
        """Research using OpenAI API."""
        from src.utils.logging_manager import log_info
        log_info("Using OpenAI API for research", "RESEARCH")
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
            
        # Build research query and prompts
        research_query, system_prompt, user_prompt_suffix = self._build_research_prompts(
            topic, business_context, competitor_blogs, mode)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{research_query}. {user_prompt_suffix}"}
        ]
        
        try:
            # Use cheaper model (gpt-3.5-turbo) instead of gpt-4
            model = "gpt-3.5-turbo"
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            sources = self._extract_sources(content)
            
            return [{
                "content": content,
                "sources": sources,
                "confidence": 0.92,
                "provider": "openai",
                "model": model,
                "tokens": self._count_tokens(content),
                "timestamp": datetime.now().isoformat()
            }]
            
        except Exception as e:
            from src.utils.logging_manager import log_error
            log_error(f"Error during OpenAI research: {str(e)}")
            return []
    
    def _build_research_prompts(self,
                              topic: str,
                              business_context: Optional[Dict],
                              competitor_blogs: Optional[List[Dict]],
                              mode: ResearchMode) -> tuple[str, str, str]:
        """Build research query and prompts based on inputs."""
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
        
        system_prompt += " Provide comprehensive, factual information with sources that is directly relevant to the user's business context."
        user_prompt_suffix += f"{competitor_insights}\n\nCite your sources."
        
        return research_query, system_prompt, user_prompt_suffix
    
    def _extract_sources(self, content: str) -> List[str]:
        """Extract sources from content."""
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
        
        return sources
    
    def _count_tokens(self, text: str) -> Dict[str, int]:
        """Count tokens in text using word-based approach."""
        # Rough token estimation: 1 token ≈ 4 characters
        char_count = len(text)
        token_estimate = char_count // 4
        
        # Add extra tokens for special characters and spaces
        special_chars = len([c for c in text if not c.isalnum()])
        token_estimate += special_chars // 2
        
        # Ensure minimum token count
        token_estimate = max(token_estimate, 1)
        
        return {
            "input": token_estimate,
            "output": token_estimate
        }

async def research_topic(keywords: List[str], mode: str = "deep", business_context: Optional[Dict] = None) -> Dict[str, Any]:
    """Research content based on a list of keywords using the best available AI provider."""
    from src.utils.logging_manager import log_info
    log_info(f"Starting research for keywords: {', '.join(keywords)}")
    # Get API keys from environment variables
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Check if any API keys are available
    if not any([perplexity_api_key, anthropic_api_key, openai_api_key]):
        from src.utils.logging_manager import log_warning
        log_warning("No API keys found for research. Using mock data.")
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
        findings = await agent.research_topic(
            topic=main_topic,
            business_context=business_context,
            mode=research_mode
        )
        
        # If no findings were returned, try with a different provider
        if not findings:
            log_warning(f"Research attempt with AUTO provider returned no data, trying specific providers", "RESEARCH")
            # Try each provider in sequence until one works
            for provider in [AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.PERPLEXITY]:
                if agent.api_keys[provider]:
                    try:
                        log_info(f"Research attempt with {provider.value} provider", "RESEARCH")
                        findings = await agent.research_topic(
                            topic=main_topic,
                            business_context=business_context,
                            mode=research_mode,
                            provider=provider
                        )
                        if findings:
                            log_info(f"Successfully retrieved research data with {provider.value}", "RESEARCH")
                            break
                    except Exception as provider_error:
                        from src.utils.logging_manager import log_error
                        log_error(f"Error with {provider.value}: {str(provider_error)}")
                        continue
        
        return {
            "findings": findings if findings else [],
            "keywords_used": keywords,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        from src.utils.logging_manager import log_error
        log_error(f"Error in research_topic: {str(e)}")
        return {
            "findings": [],
            "keywords_used": keywords,
            "error": str(e),
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
