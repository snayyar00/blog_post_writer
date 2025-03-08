"""
Agent orchestrator that coordinates all agents for blog post generation.
Uses functional programming patterns and follows RORO principles.
"""

import os
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import importlib.util

from src.agents.research_agent import research_topic, ResearchAgent
from src.agents.keyword_agent import KeywordTopologyAgent, generate_keywords
from src.agents.context_search_agent import find_related_content
from src.agents.content_quality_agent import ContentQualityChecker
from src.agents.competitor_analysis_agent import analyze_competitor_blogs
from src.agents.humanizer_agent import HumanizerAgent
from src.agents.blog_analyzer import BlogAnalyzer
from src.agents.validator_agent import ContentValidatorAgent
from src.agents.memory_manager import CompanyMemoryManager
from src.agents.content_functions import generate_outline, generate_sections
from src.utils.openai_blog_writer import BlogPost, ContentMetrics

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = {
        "spacy": "pip install spacy && python -m spacy download en_core_web_sm",
        "nltk": "pip install nltk && python -c 'import nltk; nltk.download(\"punkt\"); nltk.download(\"stopwords\"); nltk.download(\"wordnet\")'" ,
        "textblob": "pip install textblob",
        "readability": "pip install readability"
    }
    
    missing_packages = []
    for package, install_cmd in required_packages.items():
        if importlib.util.find_spec(package) is None:
            missing_packages.append(f"- {package}: {install_cmd}")
    
    if missing_packages:
        error_msg = "Missing required dependencies. Please install:\n" + "\n".join(missing_packages)
        raise ImportError(error_msg)


def ensure_api_keys():
    """Ensure that necessary API keys are available."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")


class AgentOrchestrator:
    """Orchestrates all agents for blog post generation."""
    
    def __init__(self):
        """Initialize the orchestrator with all required agents."""
        # Check dependencies and API keys
        check_dependencies()
        ensure_api_keys()
        
        self.keyword_agent = KeywordTopologyAgent()
        self.quality_checker = ContentQualityChecker()
        
        # Initialize memory manager with error handling
        try:
            self.memory_manager = CompanyMemoryManager()
            self.has_memory_manager = True
        except Exception as e:
            print(f"Warning: Failed to initialize memory manager: {str(e)}")
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
                print("Research agent initialized successfully with available API providers")
            else:
                self.research_agent = None
                print("No API keys available for research agent")
        except Exception as e:
            print(f"Warning: Failed to initialize research agent: {str(e)}")
            self.research_agent = None
            
        self.humanizer_agent = HumanizerAgent()
        self.validator_agent = ContentValidatorAgent()
        self.blog_analyzer = BlogAnalyzer()
        
    async def generate_blog_post(self, params: Dict[str, Any]) -> Optional[BlogPost]:
        """
        Generate a complete blog post using all agents.
        
        Args:
            params: Dictionary containing:
                - keyword: Main keyword for the blog post
                - business_type: Type of business (e.g., "Technology", "E-commerce")
                - content_goal: Primary goal of the content (e.g., "educate", "convert")
                - web_references: Number of web references to use
                
        Returns:
            BlogPost object containing the generated content and metrics
        """
        try:
            # Extract parameters
            keyword = params.get("keyword", "")
            business_type = params.get("business_type", "Technology")
            content_goal = params.get("content_goal", "educate and inform readers")
            web_references = params.get("web_references", 3)
            
            # Validate and potentially enhance the input keyword using context files
            from src.utils.context_keyword_manager import get_initial_keyword, load_keyword_directory, get_top_keywords
            from pathlib import Path
            import os
            
            # If keyword is too generic or empty, try to get a better one from context
            generic_keywords = ["content marketing", "marketing", "content", "blog", "article", ""]
            directory_path = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "keyword_directory.json"))
            
            if keyword.lower() in generic_keywords or len(keyword) < 5:
                print(f"⚠️ Generic keyword detected: {keyword}. Finding a better keyword from context...")
                # Try to get a better keyword from context
                if directory_path.exists():
                    directory = load_keyword_directory(directory_path)
                    top_keywords = get_top_keywords(directory, count=5)
                    if top_keywords:
                        keyword = top_keywords[0]
                        print(f"🔄 Using better keyword from context: {keyword}")
                else:
                    # Fallback to get_initial_keyword if directory doesn't exist
                    keyword = get_initial_keyword()
                    print(f"🔄 Using initial keyword from context: {keyword}")
            
            # Step 1: Research phase - gather information
            print(f"🔍 Researching topic: {keyword}")
            research_results = await self._conduct_research(keyword, web_references)
            
            # Step 2: Keyword analysis
            print(f"🔑 Analyzing keywords for: {keyword}")
            keyword_results = await self._analyze_keywords(keyword, research_results)
            
            # Step 3: Competitor analysis
            print(f"👀 Analyzing competitors for: {keyword}")
            competitor_insights = await self._analyze_competitors(keyword, web_references)
            
            # Step 4: Content generation
            print(f"✍️ Generating content for: {keyword}")
            blog_content = await self._generate_content(
                keyword=keyword,
                business_type=business_type,
                content_goal=content_goal,
                research_results=research_results,
                keyword_results=keyword_results,
                competitor_insights=competitor_insights
            )
            
            # Step 5: Content quality check and improvement
            print(f"🔍 Checking content quality")
            improved_content = await self._improve_content_quality(blog_content, keyword)
            
            # Step 6: Humanize content
            print(f"🧠 Humanizing content")
            final_content = await self._humanize_content(improved_content, business_type)
            
            # Step 7: Final validation
            print(f"✅ Validating final content")
            validation_results = await self._validate_content(final_content, keyword)
            
            # Extract title and create metrics
            title = self._extract_title(final_content)
            metrics = self._generate_metrics(validation_results, business_type, content_goal)
            
            # Create and return the blog post
            return BlogPost(
                title=title,
                content=final_content,
                metrics=metrics,
                keywords=keyword_results.get("primary_keywords", [keyword]),
                outline=self._extract_outline(final_content)
            )
            
        except Exception as e:
            print(f"Error in blog post generation: {str(e)}")
            return None
    
    async def _conduct_research(self, keyword: str, web_references: int) -> Dict[str, Any]:
        """Conduct research on the topic using research agent with business context."""
        try:
            # Load context data if available
            context_data = self._load_context_data()
            print(f"Loaded {len(context_data)} context files for research")
            
            # Extract business context from context files
            business_context = self._extract_business_context(context_data)
            
            # Get competitor blogs
            competitor_blogs = await self._get_competitor_blogs(keyword, business_context)
            print(f"Retrieved {len(competitor_blogs)} competitor blogs for analysis")
            
            # Find related content from context files
            related_content = find_related_content(keyword, context_data)
            
            # Check if we have a research agent configured
            if hasattr(self, 'research_agent') and self.research_agent:
                print(f"Using Perplexity research agent for deep research on: {keyword}")
                # Use our enhanced research agent with business context and competitor blogs
                findings = self.research_agent.research_topic(
                    topic=keyword,
                    business_context=business_context,
                    competitor_blogs=competitor_blogs,
                    depth=3
                )
                
                research_findings = {"findings": findings}
            else:
                # Fallback to basic research function
                print(f"Research agent not available, using basic research for: {keyword}")
                research_findings = research_topic([keyword])  # Pass as positional argument
            
            # If research findings are empty, try a fallback approach with OpenAI
            if not research_findings.get("findings"):
                print("Using fallback research approach with OpenAI...")
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser
                import json
                
                # Create a more detailed prompt that includes business context
                business_context_str = ""
                if business_context:
                    business_context_str = f"\nBusiness Type: {business_context.get('business_type', 'Not specified')}\n"
                    business_context_str += f"Industry: {business_context.get('industry', 'Not specified')}\n"
                    business_context_str += f"Target Audience: {business_context.get('target_audience', 'Not specified')}\n"
                
                # Add competitor insights
                competitor_insights = ""
                if competitor_blogs:
                    competitor_insights = "\nCompetitor Content Analysis:\n"
                    for i, blog in enumerate(competitor_blogs[:3]):
                        competitor_insights += f"Competitor {i+1}: {blog.get('title', 'Untitled')}\n"
                        competitor_insights += f"Key points: {blog.get('summary', 'No summary available')}\n"
                
                llm = ChatOpenAI(model="gpt-4")
                research_prompt = PromptTemplate.from_template("""
                    Research the following topic and provide comprehensive information that is relevant to the business context:
                    
                    Topic: {keyword}
                    
                    {business_context}
                    
                    {competitor_insights}
                    
                    Include:
                    1. Key facts and statistics relevant to the business
                    2. Best practices for this business type and industry
                    3. Expert opinions and case studies
                    4. Recent developments and trends
                    5. Practical applications and business value
                    
                    Format your response as JSON with the following structure:
                    {{
                        "findings": [
                            {{
                                "content": "Detailed research finding",
                                "sources": ["Source URL or reference"],
                                "confidence": 0.9
                            }}
                        ]
                    }}
                """)
                
                chain = research_prompt | llm | StrOutputParser()
                
                try:
                    result = chain.invoke({
                        "keyword": keyword, 
                        "business_context": business_context_str,
                        "competitor_insights": competitor_insights
                    })
                    research_findings = json.loads(result)
                except Exception as e:
                    print(f"Error in fallback research: {str(e)}")
                    research_findings = {
                        "findings": [{
                            "content": f"Research on {keyword} shows it's an important topic in {web_references} different contexts.",
                            "sources": ["Generated as fallback"],
                            "confidence": 0.5
                        }]
                    }
            
            # Combine results
            return {
                "findings": research_findings.get("findings", []),
                "related_content": related_content,
                "web_references": web_references
            }
        except Exception as e:
            print(f"Error in _conduct_research: {str(e)}")
            # Return minimal research data as fallback
            return {
                "findings": [{
                    "content": f"Research on {keyword} shows it's an important topic with various applications.",
                    "sources": ["Generated as fallback"],
                    "confidence": 0.5
                }],
                "related_content": {},
                "web_references": web_references
            }
    
    async def _analyze_keywords(self, keyword: str, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze keywords using keyword agent and context data for more targeted selection."""
        # Load context data
        context_data = self._load_context_data()
        
        # Extract business context for more targeted keyword selection
        business_context = self._extract_business_context(context_data)
        
        # Extract keywords from context files
        context_keywords = self._extract_keywords_from_context(context_data)
        
        # Get competitor insights for keyword analysis
        competitor_blogs = await self._get_competitor_blogs(keyword, business_context)
        competitor_keywords = self._extract_competitor_keywords(competitor_blogs)
        
        # Use perplexity for keyword research if available
        if hasattr(self, 'research_agent') and self.research_agent:
            print(f"Using Perplexity for deep keyword research on: {keyword}")
            perplexity_keywords = self._extract_keywords_from_research(research_results)
        else:
            perplexity_keywords = []
        
        # Combine all keywords for analysis
        combined_keywords = set([keyword])
        combined_keywords.update(context_keywords[:10])  # Top 10 keywords from context
        combined_keywords.update(competitor_keywords[:10])  # Top 10 keywords from competitors
        combined_keywords.update(perplexity_keywords[:10])  # Top 10 keywords from perplexity
        
        # Generate keyword topology for the most relevant combined keywords
        topology = await self.keyword_agent.generate_keyword_topology(list(combined_keywords)[:5])
        
        # Extract primary keywords with preference for context and competitor keywords
        primary_keywords = [cluster.main_keyword for cluster in topology.get("primary", [])]
        primary_keywords.extend([kw for cluster in topology.get("primary", []) 
                               for kw in cluster.related_keywords[:3]])
        
        # Add high-value keywords from context files
        for kw in context_keywords[:5]:
            if kw not in primary_keywords:
                primary_keywords.append(kw)
        
        # Add high-value keywords from competitor analysis
        for kw in competitor_keywords[:5]:
            if kw not in primary_keywords:
                primary_keywords.append(kw)
        
        # Extract secondary keywords
        secondary_keywords = [cluster.main_keyword for cluster in topology.get("secondary", [])]
        secondary_keywords.extend([kw for cluster in topology.get("secondary", []) 
                                 for kw in cluster.related_keywords[:2]])
        
        # Add remaining context and competitor keywords
        for kw in context_keywords[5:10] + competitor_keywords[5:10]:
            if kw not in primary_keywords and kw not in secondary_keywords:
                secondary_keywords.append(kw)
        
        print(f"Selected {len(primary_keywords)} primary keywords and {len(secondary_keywords)} secondary keywords")
        print(f"Primary keywords: {', '.join(primary_keywords[:5])}...")
        
        return {
            "primary_keywords": list(set(primary_keywords)),
            "secondary_keywords": list(set(secondary_keywords)),
            "keyword_topology": topology,
            "content_structure": self.keyword_agent.suggest_content_structure(topology)
        }
    
    async def _analyze_competitors(self, keyword: str, web_references: int) -> Dict[str, Any]:
        """Analyze competitors using competitor analysis agent."""
        try:
            # Use the competitor analysis agent
            competitor_results = analyze_competitor_blogs(topic=keyword, max_competitors=web_references, max_posts_per_competitor=2)
            
            # Extract common patterns
            common_headings = competitor_results.get("common_headings", [])
            popular_keywords = competitor_results.get("popular_keywords", [])
            content_structure = competitor_results.get("content_structure", {})
            
            return {
                "common_headings": common_headings,
                "popular_keywords": popular_keywords,
                "content_structure": content_structure,
                "competitor_blogs": competitor_results.get("competitor_blogs", [])
            }
            
        except Exception as e:
            print(f"Error analyzing competitors: {str(e)}")
            return {
                "common_headings": [],
                "popular_keywords": [],
                "content_structure": {},
                "competitor_blogs": []
            }
    
    async def _generate_content(self, keyword: str, business_type: str, content_goal: str,
                              research_results: Dict[str, Any], keyword_results: Dict[str, Any],
                              competitor_insights: Dict[str, Any]) -> str:
        """Generate content using research and keyword insights."""
        try:
            # Determine content type based on business_type and content_goal
            content_type = self._determine_content_type(business_type, content_goal)
            print(f"Generating {content_type} outline for keyword: {keyword}")
            
            # Create content outline - match the signature in content_functions.py
            outline = generate_outline(
                keyword=keyword,
                research_results=research_results,
                competitor_insights=competitor_insights,
                content_type=content_type
            )
            
            if not outline or not isinstance(outline, list):
                print("Warning: Failed to generate outline, using fallback")
                outline = [
                    f"# {keyword.title()}: A Comprehensive Guide",
                    "## Introduction",
                    "## What is " + keyword.title(),
                    "## Benefits of " + keyword.title(),
                    "## Best Practices",
                    "## Conclusion"
                ]
            
            print(f"Generated outline with {len(outline)} sections")
            
            # Generate sections based on outline - match the signature in content_functions.py
            sections = generate_sections(
                outline=outline,
                research_results=research_results,
                keyword=keyword,
                content_type=content_type
            )
            
            if not sections or not isinstance(sections, str) or len(sections) < 100:
                print("Warning: Generated content too short, using fallback")
                # Fallback content generation
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import PromptTemplate
                
                llm = ChatOpenAI(model="gpt-4")
                content_prompt = PromptTemplate.from_template("""
                    Write a comprehensive blog post about {keyword} following this outline:
                    {outline}
                    
                    Target audience: {business_type} professionals
                    Content goal: {content_goal}
                    
                    Make the content engaging, informative, and well-structured.
                    Include proper headings, subheadings, and formatting.
                    Minimum length: 1000 words.
                """)
                
                chain = content_prompt | llm
                response = chain.invoke({
                    "keyword": keyword,
                    "outline": "\n".join(outline),
                    "business_type": business_type,
                    "content_goal": content_goal
                })
                
                sections = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            # Fallback with minimal content
            outline = [
                f"# {keyword.title()}: A Comprehensive Guide",
                "## Introduction",
                "## Key Points",
                "## Conclusion"
            ]
            sections = f"# {keyword.title()}: A Comprehensive Guide\n\n## Introduction\n\nThis is a comprehensive guide about {keyword}.\n\n## Key Points\n\nHere are some key points about {keyword}.\n\n## Conclusion\n\nIn conclusion, {keyword} is an important topic for {business_type} businesses looking to {content_goal}."
        
        # Combine sections into full content
        if isinstance(sections, list):
            content = "\n\n".join(sections)
        else:
            content = sections  # sections is already a string
        
        # Store in memory for future reference if memory manager is available
        if hasattr(self, 'has_memory_manager') and self.has_memory_manager:
            try:
                self.memory_manager.store_memory(
                    content=content,
                    metadata={
                        "type": "generated_content",
                        "keyword": keyword,
                        "outline": str(outline)
                    },
                    memory_type="generated_content"
                )
            except Exception as e:
                print(f"Warning: Failed to store memory: {str(e)}")
        
        return content
    
    async def _improve_content_quality(self, content: str, keyword: str) -> str:
        """Check and improve content quality."""
        try:
            # Analyze content quality
            quality_analysis = self.quality_checker.analyze_content(content)
            
            # Apply improvements based on analysis
            improvements = quality_analysis.get("improvements", [])
            
            if not improvements:
                return content
                
            # Use the blog analyzer to improve content
            analysis = self.blog_analyzer.analyze_blog(content)
            
            # Apply improvements based on analysis
            if analysis.get("improvements"):
                # Create a prompt to improve the content based on suggestions
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser
                
                llm = ChatOpenAI(model="gpt-4")
                improve_prompt = PromptTemplate.from_template("""
                    Improve this blog post based on the following suggestions:
                    
                    Blog post:
                    {content}
                    
                    Improvement suggestions:
                    {suggestions}
                    
                    Keywords to emphasize:
                    {keyword}
                    
                    Return the improved content only.
                """)
                
                chain = improve_prompt | llm | StrOutputParser()
                
                # Convert suggestions to text format
                suggestions_text = "\n".join([f"- {s['category']}: {s['suggestion']}" for s in analysis["improvements"]])
                
                improved_content = chain.invoke({
                    "content": content,
                    "suggestions": suggestions_text,
                    "keyword": keyword
                })
                
                return improved_content
            
            return content
        except Exception as e:
            print(f"Error improving content quality: {str(e)}")
            return content
    
    async def _humanize_content(self, content: str, business_type: str) -> str:
        """Humanize content to make it more engaging."""
        try:
            # Determine brand voice based on business type
            brand_voice = f"Professional and authoritative voice for a {business_type} business"
            target_audience = "Business professionals and decision makers interested in web accessibility"
            
            # Check content length and chunk if necessary to avoid token limits
            if len(content) > 6000:  # Approximate token limit threshold
                print("Content too long for humanization, processing in chunks")
                
                # Split content into sections (preserving headings)
                import re
                sections = re.split(r'(#+\s.*?\n)', content)
                
                # Recombine into manageable chunks
                chunks = []
                current_chunk = ""
                
                for i in range(0, len(sections)):
                    # If adding this section would make the chunk too large, start a new chunk
                    if len(current_chunk) + len(sections[i]) > 5000:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sections[i]
                    else:
                        current_chunk += sections[i]
                
                # Add the last chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Process each chunk
                humanized_chunks = []
                for chunk in chunks:
                    try:
                        humanized_chunk = self.humanizer_agent.humanize_content(
                            content=chunk,
                            brand_voice=brand_voice,
                            target_audience=target_audience
                        )
                        humanized_chunks.append(humanized_chunk)
                    except Exception as chunk_error:
                        print(f"Error humanizing chunk: {str(chunk_error)}")
                        humanized_chunks.append(chunk)  # Use original chunk if humanization fails
                
                # Combine humanized chunks
                return "".join(humanized_chunks)
            else:
                # Humanize content using the humanizer agent
                humanized_content = self.humanizer_agent.humanize_content(
                    content=content,
                    brand_voice=brand_voice,
                    target_audience=target_audience
                )
                
                return humanized_content
        except Exception as e:
            print(f"Error during content humanization: {str(e)}")
            return content
    
    async def _validate_content(self, content: str, keyword: str) -> Dict[str, Any]:
        """Validate the final content."""
        try:
            # Create company context based on keyword
            company_context = f"Company focused on web accessibility with expertise in {keyword}"
            
            # Check content length to avoid token limits
            if len(content) > 6000:  # Approximate token limit threshold
                print("Content too long for validation, performing simplified validation")
                
                # Perform simplified validation on key sections
                import re
                
                # Extract introduction and conclusion
                intro_match = re.search(r'^(.*?)(?=\n##)', content, re.DOTALL)
                conclusion_match = re.search(r'##\s*Conclusion.*?$', content, re.DOTALL)
                
                intro = intro_match.group(0) if intro_match else ""
                conclusion = conclusion_match.group(0) if conclusion_match else ""
                
                # Extract headings to check structure
                headings = re.findall(r'##\s*(.*?)\n', content)
                
                # Create a simplified validation based on these elements
                has_intro = len(intro) > 100
                has_conclusion = len(conclusion) > 100
                has_structure = len(headings) >= 3
                
                # Check keyword presence
                keyword_count = content.lower().count(keyword.lower())
                keyword_density = keyword_count / (len(content.split()) / 1000)  # per 1000 words
                
                # Create validation results
                validation_results = {
                    "is_valid": has_intro and has_conclusion and has_structure and 0.5 <= keyword_density <= 5,
                    "quality_score": 7.0,
                    "issues": [],
                    "suggestions": []
                }
                
                # Add issues and suggestions based on checks
                if not has_intro:
                    validation_results["issues"].append("Missing or short introduction")
                    validation_results["suggestions"].append("Add a comprehensive introduction")
                
                if not has_conclusion:
                    validation_results["issues"].append("Missing or short conclusion")
                    validation_results["suggestions"].append("Add a strong conclusion with call to action")
                
                if not has_structure:
                    validation_results["issues"].append("Insufficient structure")
                    validation_results["suggestions"].append("Add more headings to improve content structure")
                
                if keyword_density < 0.5:
                    validation_results["issues"].append("Low keyword density")
                    validation_results["suggestions"].append(f"Increase mentions of '{keyword}' throughout the content")
                elif keyword_density > 5:
                    validation_results["issues"].append("Excessive keyword density")
                    validation_results["suggestions"].append(f"Reduce mentions of '{keyword}' to avoid keyword stuffing")
                
                return validation_results
            
            # Validate content using the validator agent
            validation_results = self.validator_agent.validate_content(
                content=content,
                company_context=company_context
            )
            
            # If validation fails, use a fallback approach
            if not validation_results:
                # Analyze using blog analyzer as fallback
                analysis = await self.blog_analyzer.analyze_blog(content)
                validation_results = {
                    "quality_score": analysis.get("overall_score", 7.0),
                    "seo_score": 7.0,
                    "readability": {
                        "score": 7.0,
                        "level": "intermediate"
                    },
                    "content": content
                }
            
            return validation_results
        except Exception as e:
            print(f"Error validating content: {str(e)}")
            return {
                "quality_score": 7.0,
                "seo_score": 7.0,
                "readability": {
                    "score": 7.0,
                    "level": "intermediate"
                },
                "content": content
            }
    
    def _extract_title(self, content: str) -> str:
        """Extract title from content."""
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line.replace("# ", "")
            if line.startswith("#"):
                return line.replace("#", "").strip()
        return "Blog Post about " + content.split()[0:5]
    
    def _extract_outline(self, content: str) -> List[str]:
        """Extract outline from content."""
        lines = content.split("\n")
        outline = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("## "):
                outline.append(line.replace("## ", ""))
            elif line.startswith("### "):
                outline.append(line.replace("### ", ""))
                
        return outline
    
    def _extract_keywords_from_context(self, context_data: Dict[str, Any]) -> List[str]:
        """Extract relevant keywords from context files."""
        keywords = []
        
        # Look for keyword files specifically
        keyword_files = ["Webability_Updated Keyword Research.xlsx - webability.csv", "SEO Content.md"]
        
        for filename, content in context_data.items():
            # Check if this is a keyword research file
            if filename in keyword_files:
                if filename.endswith(".csv") and isinstance(content, str):
                    # Parse CSV content
                    lines = content.strip().split("\n")
                    for line in lines[3:]:  # Skip header rows
                        parts = line.split(",")
                        if len(parts) >= 3 and parts[2].strip():
                            keywords.append(parts[2].strip().lower())
                elif filename.endswith(".md") and isinstance(content, str):
                    # Extract keywords from markdown content
                    # Look for sections with keywords
                    if "High-Value Keywords" in content:
                        section = content.split("High-Value Keywords")[1].split("##")[0]
                        # Extract keywords from bullet points
                        import re
                        bullet_points = re.findall(r'\*\s*\*\*([^:]+):\*\*', section)
                        keywords.extend([kw.strip().lower() for kw in bullet_points])
                    
                    # Look for other keyword mentions
                    keyword_matches = re.findall(r'\*\*([^\*]+)\*\*', content)
                    potential_keywords = [match.strip().lower() for match in keyword_matches 
                                        if 3 <= len(match.strip()) <= 50 and not match.strip().startswith("http")]
                    keywords.extend(potential_keywords)
            
            # Extract keywords from business context files
            if filename == "business_competitors.md" and isinstance(content, str):
                # Extract competitor names and features
                import re
                competitor_names = re.findall(r'###\s+([^\n]+)', content)
                keywords.extend([name.strip().lower() for name in competitor_names])
                
                # Extract features
                features = re.findall(r'\*\*Unique Features\*\*:\s+([^\n]+)', content)
                for feature_list in features:
                    feature_keywords = feature_list.split(",")
                    keywords.extend([kw.strip().lower() for kw in feature_keywords])
            
            # Extract keywords from WebAbility.io info
            if "WebAbility.io" in filename and isinstance(content, str):
                # Extract key phrases related to web accessibility
                phrases = ["web accessibility", "ADA compliance", "WCAG", "accessibility standards",
                          "digital accessibility", "inclusive design", "screen readers", "assistive technology"]
                
                # Add specific keywords from the content
                import re
                # Find phrases in bullet points
                bullet_points = re.findall(r'\*\s+([^\n]+)', content)
                for point in bullet_points:
                    # Extract potential keywords (2-3 word phrases)
                    words = point.split()
                    for i in range(len(words)-1):
                        if i+2 <= len(words):
                            phrase = " ".join(words[i:i+2]).lower()
                            if 5 <= len(phrase) <= 50 and not any(c.isdigit() for c in phrase):
                                keywords.append(phrase)
                    
                    for i in range(len(words)-2):
                        if i+3 <= len(words):
                            phrase = " ".join(words[i:i+3]).lower()
                            if 5 <= len(phrase) <= 50 and not any(c.isdigit() for c in phrase):
                                keywords.append(phrase)
        
        # Remove duplicates and sort by frequency
        from collections import Counter
        keyword_counter = Counter(keywords)
        
        # Return sorted list of unique keywords
        return [kw for kw, _ in keyword_counter.most_common(30)]
    
    def _extract_competitor_keywords(self, competitor_blogs: List[Dict[str, Any]]) -> List[str]:
        """Extract keywords from competitor blogs."""
        keywords = []
        
        for blog in competitor_blogs:
            # Extract keywords from title
            title = blog.get("title", "")
            if title:
                # Split title into words and create 1-3 word phrases
                words = title.split()
                
                # Add single words (excluding stop words)
                stop_words = {"the", "and", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by"}
                for word in words:
                    if word.lower() not in stop_words and len(word) > 3:
                        keywords.append(word.lower())
                
                # Add 2-word phrases
                for i in range(len(words)-1):
                    phrase = f"{words[i]} {words[i+1]}".lower()
                    if not any(word.lower() in stop_words for word in phrase.split()):
                        keywords.append(phrase)
                
                # Add 3-word phrases
                for i in range(len(words)-2):
                    phrase = f"{words[i]} {words[i+1]} {words[i+2]}".lower()
                    if sum(1 for word in phrase.split() if word.lower() in stop_words) <= 1:
                        keywords.append(phrase)
            
            # Extract keywords from content
            content = blog.get("content", "")
            if content:
                # Look for header tags in HTML content
                import re
                headers = re.findall(r'<h[1-3][^>]*>([^<]+)</h[1-3]>', content)
                for header in headers:
                    words = header.split()
                    for i in range(len(words)-1):
                        phrase = f"{words[i]} {words[i+1]}".lower()
                        if not any(word.lower() in stop_words for word in phrase.split()):
                            keywords.append(phrase)
            
            # Extract keywords from summary
            summary = blog.get("summary", "")
            if summary:
                # Split summary into sentences
                sentences = summary.split(". ")
                for sentence in sentences:
                    words = sentence.split()
                    for i in range(len(words)-1):
                        if i+2 <= len(words):
                            phrase = " ".join(words[i:i+2]).lower()
                            if not any(word.lower() in stop_words for word in phrase.split()):
                                keywords.append(phrase)
        
        # Remove duplicates and sort by frequency
        from collections import Counter
        keyword_counter = Counter(keywords)
        
        # Return sorted list of unique keywords
        return [kw for kw, _ in keyword_counter.most_common(20)]
    
    def _determine_content_type(self, business_type: str, content_goal: str) -> str:
        """Determine the content type based on business type and content goal."""
        # Map business types to content types
        business_type_mapping = {
            "Technology": "technical",
            "Finance": "journalistic",
            "Healthcare": "journalistic",
            "Education": "standard",
            "Retail": "standard",
            "Manufacturing": "technical",
            "Legal": "journalistic",
            "Consulting": "standard"
        }
        
        # Map content goals to content types
        content_goal_mapping = {
            "educate": "journalistic",
            "inform": "journalistic",
            "convert": "standard",
            "engage": "standard",
            "technical": "technical",
            "guide": "technical"
        }
        
        # Default to standard content type
        content_type = "standard"
        
        # Check business type
        for bt, ct in business_type_mapping.items():
            if bt.lower() in business_type.lower():
                content_type = ct
                break
        
        # Check content goal (overrides business type if found)
        for cg, ct in content_goal_mapping.items():
            if cg.lower() in content_goal.lower():
                content_type = ct
                break
        
        return content_type
        
    def _extract_keywords_from_research(self, research_results: Dict[str, Any]) -> List[str]:
        """Extract keywords from research results."""
        keywords = []
        
        # Extract keywords from research findings
        findings = research_results.get("findings", [])
        
        for finding in findings:
            content = finding.get("content", "")
            if content:
                # Split content into sentences
                sentences = content.split(". ")
                
                # Process each sentence to extract potential keywords
                for sentence in sentences:
                    # Split into words
                    words = sentence.split()
                    
                    # Skip short sentences
                    if len(words) < 5:
                        continue
                    
                    # Extract 2-3 word phrases that might be keywords
                    stop_words = {"the", "and", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by"}
                    
                    for i in range(len(words)-1):
                        if i+2 <= len(words):
                            phrase = " ".join(words[i:i+2]).lower()
                            if not any(word.lower() in stop_words for word in phrase.split()) and len(phrase) > 5:
                                keywords.append(phrase)
                    
                    for i in range(len(words)-2):
                        if i+3 <= len(words):
                            phrase = " ".join(words[i:i+3]).lower()
                            if sum(1 for word in phrase.split() if word.lower() in stop_words) <= 1 and len(phrase) > 5:
                                keywords.append(phrase)
        
        # Remove duplicates and sort by frequency
        from collections import Counter
        keyword_counter = Counter(keywords)
        
        # Return sorted list of unique keywords
        return [kw for kw, _ in keyword_counter.most_common(20)]
        return outline
    
    def _generate_metrics(self, validation_results: Dict[str, Any], 
                        business_type: str, content_goal: str) -> ContentMetrics:
        """Generate metrics for the blog post."""
        metrics = ContentMetrics()
        
        # Set viral potential
        metrics.viral_potential = {
            "shareability": validation_results.get("shareability", 0.7) * 100,
            "emotional_impact": validation_results.get("emotional_impact", 0.6) * 100,
            "trending_topic_fit": validation_results.get("trending_topic_fit", 0.8) * 100,
            "social_media_potential": validation_results.get("social_media_potential", 0.7) * 100
        }
        
        # Set business impact
        metrics.business_impact = {
            "sales_potential": validation_results.get("sales_potential", 0.6) * 100,
            "lead_generation": validation_results.get("lead_generation", 0.7) * 100,
            "brand_authority": validation_results.get("brand_authority", 0.8) * 100,
            "customer_education": validation_results.get("customer_education", 0.75) * 100
        }
        
        # Set content type
        metrics.content_type = {
            "educational": 0.8 if "educate" in content_goal.lower() else 0.5,
            "sales": 0.8 if "convert" in content_goal.lower() else 0.4,
            "thought_leadership": 0.8 if "authority" in content_goal.lower() else 0.6
        }
        
        # Set other metrics
        metrics.funnel_stage = validation_results.get("funnel_stage", "middle")
        metrics.reader_level = validation_results.get("reader_level", "intermediate")
        metrics.read_time_minutes = len(validation_results.get("content", "").split()) // 200
        
        return metrics
    
    def _load_context_data(self) -> Dict[str, Any]:
        """Load context data from files with proper handling of different file types."""
        context_data = {}
        context_dir = Path("./context")
        
        # Early return if context directory doesn't exist
        if not context_dir.exists():
            print("Context directory not found. Creating one...")
            context_dir.mkdir(exist_ok=True)
            return {}
        
        # Process each file based on its type
        for file_path in context_dir.glob("*"):
            if not file_path.is_file():
                continue
                
            file_ext = file_path.suffix.lower()
            try:
                # Handle different file types
                if file_ext in [".xlsx", ".xls"]:
                    # For Excel files, use pandas to extract data
                    try:
                        import pandas as pd
                        df = pd.read_excel(file_path, engine="openpyxl")
                        context_data[file_path.name] = df.to_json(orient="records")
                    except ImportError:
                        print("Pandas not installed. Cannot read Excel files.")
                        print("Install with: pip install pandas openpyxl")
                elif file_ext in [".json"]:
                    # For JSON files
                    import json
                    with open(file_path, 'r') as f:
                        context_data[file_path.name] = json.load(f)
                elif file_ext in [".csv"]:
                    # For CSV files
                    try:
                        import pandas as pd
                        df = pd.read_csv(file_path)
                        context_data[file_path.name] = df.to_json(orient="records")
                    except ImportError:
                        print("Pandas not installed. Cannot read CSV files.")
                else:
                    # For text files (txt, md, etc.)
                    try:
                        context_data[file_path.name] = file_path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        # Try with different encoding if utf-8 fails
                        context_data[file_path.name] = file_path.read_text(encoding='latin-1')
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                # Don't let one file failure stop the entire process
                continue
        
        print(f"Loaded {len(context_data)} context files successfully")
        return context_data
        
    def _extract_business_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract business context from context files."""
        business_context = {
            "business_type": "",
            "industry": "",
            "target_audience": "",
            "company_name": "",
            "products_services": [],
            "key_differentiators": [],
            "brand_voice": ""
        }
        
        # Look for business context in files with specific names
        business_files = ["business_info.json", "company_info.json", "business_profile.json", "brand_info.json"]
        
        for filename, content in context_data.items():
            # Check if this is a business info file
            if filename in business_files and isinstance(content, dict):
                # Direct mapping from JSON file
                for key in business_context.keys():
                    if key in content:
                        business_context[key] = content[key]
            
            # Look for business context in text files
            elif filename.endswith(".txt") or filename.endswith(".md"):
                if isinstance(content, str):
                    # Look for business context in text content
                    text_content = content.lower()
                    
                    # Extract business type
                    if "business type:" in text_content and not business_context["business_type"]:
                        line = [l for l in content.split("\n") if "business type:" in l.lower()]
                        if line:
                            business_context["business_type"] = line[0].split(":", 1)[1].strip()
                    
                    # Extract industry
                    if "industry:" in text_content and not business_context["industry"]:
                        line = [l for l in content.split("\n") if "industry:" in l.lower()]
                        if line:
                            business_context["industry"] = line[0].split(":", 1)[1].strip()
                    
                    # Extract target audience
                    if "target audience:" in text_content and not business_context["target_audience"]:
                        line = [l for l in content.split("\n") if "target audience:" in l.lower()]
                        if line:
                            business_context["target_audience"] = line[0].split(":", 1)[1].strip()
                    
                    # Extract company name
                    if "company name:" in text_content and not business_context["company_name"]:
                        line = [l for l in content.split("\n") if "company name:" in l.lower()]
                        if line:
                            business_context["company_name"] = line[0].split(":", 1)[1].strip()
        
        # If we couldn't find any business context, use default values for accessibility industry
        if not any(business_context.values()):
            print("No business context found in context files. Using default accessibility industry values.")
            business_context = {
                "business_type": "SaaS",
                "industry": "Web Accessibility",
                "target_audience": "Business owners, web developers, and accessibility professionals",
                "company_name": "WebAbility",
                "products_services": ["Accessibility compliance tools", "Accessibility audits", "Remediation services"],
                "key_differentiators": ["AI-powered scanning", "Real-time monitoring", "Compliance reporting"],
                "brand_voice": "Professional, helpful, and educational"
            }
        
        return business_context
    
    async def _get_competitor_blogs(self, keyword: str, business_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get competitor blogs related to the keyword."""
        competitor_blogs = []
        
        # First, get WebAbility's own blogs from their sitemap
        webability_blogs = await self._get_webability_blogs(keyword)
        if webability_blogs:
            print(f"Found {len(webability_blogs)} relevant WebAbility blogs")
            competitor_blogs.extend(webability_blogs)
        
        # Define default competitors based on business context
        default_competitors = []
        
        # Set industry-specific competitors
        if business_context.get("industry", "").lower() == "web accessibility":
            default_competitors = [
                "accessibe.com",
                "userway.org",
                "www.levelaccess.com",
                "www.deque.com",
                "www.accessibilityassociation.org"
            ]
        elif business_context.get("industry", "").lower() == "seo" or "marketing" in business_context.get("industry", "").lower():
            default_competitors = [
                "moz.com",
                "ahrefs.com",
                "semrush.com",
                "searchenginejournal.com",
                "contentmarketinginstitute.com"
            ]
        
        # Look for competitor URLs in context files
        competitor_file_names = ["competitors.json", "competitor_urls.txt", "competitor_analysis.json"]
        context_dir = Path("./context")
        
        for file_name in competitor_file_names:
            file_path = context_dir / file_name
            if file_path.exists() and file_path.is_file():
                try:
                    if file_name.endswith(".json"):
                        import json
                        with open(file_path, 'r') as f:
                            competitor_data = json.load(f)
                            if isinstance(competitor_data, list):
                                default_competitors = competitor_data
                            elif isinstance(competitor_data, dict) and "urls" in competitor_data:
                                default_competitors = competitor_data["urls"]
                    elif file_name.endswith(".txt"):
                        with open(file_path, 'r') as f:
                            lines = f.readlines()
                            default_competitors = [line.strip() for line in lines if line.strip()]
                except Exception as e:
                    print(f"Error reading competitor file {file_path}: {e}")
        
        print(f"Analyzing competitors: {', '.join(default_competitors)}")
        
        # Dynamically detect competitor blog URLs based on industry
        print(f"Dynamically detecting competitor blogs for {keyword}...")
        
        # Import web scraper
        from src.utils.web_scraper import scrape_blog_posts, detect_blog_url
        
        # Try different blog URL patterns for each competitor
        for competitor_url in default_competitors:
            print(f"Analyzing competitor: {competitor_url}")
            try:
                # Ensure URL has proper format
                if not competitor_url.startswith("http"):
                    competitor_url = f"https://{competitor_url}"
                
                # Detect the correct blog URL pattern
                blog_url = await detect_blog_url(competitor_url)
                
                if not blog_url:
                    print(f"Could not detect blog URL for {competitor_url}, trying common patterns")
                    # Try common blog URL patterns
                    blog_patterns = ["/blog", "/articles", "/resources", "/insights", "/news"]
                    
                    for pattern in blog_patterns:
                        try:
                            test_url = f"{competitor_url}{pattern}"
                            # Test if URL is accessible
                            import requests
                            response = requests.head(test_url, timeout=5, allow_redirects=True)
                            if response.status_code < 400:  # Valid URL if status code is 2xx or 3xx
                                blog_url = test_url
                                print(f"Found valid blog URL: {blog_url}")
                                break
                        except Exception:
                            continue
                
                if not blog_url:
                    print(f"Could not find valid blog URL for {competitor_url}")
                    continue
                
                # Scrape blog posts with timeout and error handling
                posts = await scrape_blog_posts(blog_url, keyword, max_posts=2)
                
                # Add to competitor blogs if we found posts
                if posts:
                    competitor_blogs.extend(posts)
                    print(f"Found {len(posts)} relevant posts from {blog_url}")
            except Exception as e:
                print(f"Error analyzing competitor {competitor_url}: {str(e)}")
        
        # If we couldn't get any competitor blogs, create some dummy data
        if not competitor_blogs:
            print("No competitor blogs found. Creating placeholder data.")
            competitor_blogs = [
                {
                    "title": f"The Ultimate Guide to {keyword.title()}",
                    "url": "https://example.com/blog/ultimate-guide",
                    "summary": f"A comprehensive guide covering all aspects of {keyword}.",
                    "date": "2023-01-15"
                },
                {
                    "title": f"10 Best Practices for {keyword.title()}",
                    "url": "https://example.com/blog/best-practices",
                    "summary": f"Industry experts share their top tips for {keyword}.",
                    "date": "2023-02-20"
                }
            ]
        
        return competitor_blogs
        
    async def _get_webability_blogs(self, keyword: str) -> List[Dict[str, Any]]:
        """Fetch and analyze WebAbility's own blogs from their sitemap."""
        try:
            print("Fetching WebAbility's sitemap from https://www.webability.io/sitemap.xml")
            
            # Import necessary functions
            from src.utils.web_scraper import fetch_sitemap, scrape_blog_posts
            
            # Fetch URLs from sitemap
            sitemap_url = "https://www.webability.io/sitemap.xml"
            urls = fetch_sitemap(sitemap_url)
            
            if not urls:
                print("No URLs found in WebAbility's sitemap")
                return []
                
            print(f"Found {len(urls)} URLs in WebAbility's sitemap")
            
            # Filter for blog URLs
            blog_patterns = ['/blog/', '/article/', '/post/', '/news/']
            blog_urls = [url for url in urls if any(pattern in url for pattern in blog_patterns)]
            
            if not blog_urls:
                # If no blog URLs found with patterns, use all URLs that aren't obvious non-blog URLs
                non_blog_patterns = ['/contact', '/about', '/pricing', '/terms', '/privacy', '/login', '/signup']
                blog_urls = [url for url in urls if not any(pattern in url for pattern in non_blog_patterns)]
            
            print(f"Filtered to {len(blog_urls)} potential blog URLs")
            
            # Store WebAbility's blogs
            webability_blogs = []
            
            # Process each blog URL to extract content
            for url in blog_urls[:10]:  # Limit to 10 URLs to avoid excessive processing
                try:
                    # Fetch page content
                    import requests
                    from bs4 import BeautifulSoup
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract title
                    title_elem = soup.find(['h1', 'h2', '.post-title', '.entry-title'])
                    title = title_elem.get_text().strip() if title_elem else url.split('/')[-1]
                    
                    # Extract content
                    content_elem = soup.find(['article', '.post-content', '.entry-content', '.content', 'main'])
                    content = content_elem.get_text() if content_elem else soup.get_text()
                    
                    # Check if keyword is in content
                    if keyword.lower() in content.lower() or keyword.lower() in title.lower():
                        # Extract summary
                        summary = ""
                        paragraphs = soup.find_all('p')
                        for p in paragraphs:
                            p_text = p.get_text().strip()
                            if len(p_text) > 50:
                                summary = p_text
                                break
                        
                        # Extract date
                        date_elem = soup.find(['time', '.date', '.post-date', '.published'])
                        date = date_elem.get_text().strip() if date_elem else ""
                        
                        webability_blogs.append({
                            'title': title,
                            'url': url,
                            'summary': summary,
                            'date': date,
                            'source': 'WebAbility'
                        })
                except Exception as e:
                    print(f"Error processing WebAbility blog {url}: {e}")
            
            print(f"Found {len(webability_blogs)} relevant WebAbility blogs")
            return webability_blogs
            
        except Exception as e:
            print(f"Error fetching WebAbility blogs: {e}")
            return []


async def generate_blog_post(
    keyword: str,
    business_type: str = "Technology",
    content_goal: str = "educate and inform readers",
    web_references: int = 3
) -> Optional[BlogPost]:
    """
    Generate a complete blog post using all agents.
    
    Args:
        keyword: Main keyword for the blog post
        business_type: Type of business (e.g., "Technology", "E-commerce")
        content_goal: Primary goal of the content (e.g., "educate", "convert")
        web_references: Number of web references to use
        
    Returns:
        BlogPost object containing the generated content and metrics
    """
    # Check dependencies and API keys before proceeding
    try:
        check_dependencies()
        ensure_api_keys()
    except (ImportError, ValueError) as e:
        print(f"Error: {str(e)}")
        raise
    orchestrator = AgentOrchestrator()
    
    params = {
        "keyword": keyword,
        "business_type": business_type,
        "content_goal": content_goal,
        "web_references": web_references
    }
    
    return await orchestrator.generate_blog_post(params)
