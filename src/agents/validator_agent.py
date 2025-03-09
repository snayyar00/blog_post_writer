"""Content validator agent that checks quality, accuracy, and SEO metrics."""

import json
from typing import Dict, List, Tuple
from langchain_openai import ChatOpenAI
from src.utils.logging_manager import log_info, log_warning, log_error, log_debug
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class ContentValidatorAgent:
    def __init__(self):
        # Use gpt-3.5-turbo for validation since it's sufficient for this task
        self.llm = ChatOpenAI(model="gpt-3.5-turbo")
        self.quality_prompt = PromptTemplate.from_template("""
            As a professional web accessibility content validator, analyze the following blog post for:
            1. Content quality and depth
            2. Factual accuracy, especially regarding accessibility standards and best practices
            3. SEO optimization for accessibility-related keywords
            4. Readability and engagement
            5. Brand voice consistency with WebAbility.io's focus on accessibility
            6. Relevance to web accessibility, digital inclusion, or closely related topics
            
            IMPORTANT: WebAbility.io is a company focused EXCLUSIVELY on web accessibility solutions.
            All content must be directly related to web accessibility, ADA compliance, WCAG standards,
            assistive technologies, or digital inclusion. Content about general tech topics without 
            a clear accessibility focus should be rejected.
            
            Blog post:
            {content}
            
            Company context:
            {company_context}
            
            Provide a detailed analysis with specific recommendations for improvement.
            Rate each aspect on a scale of 1-10 and explain why.
            Format your response in JSON with the following structure:
            {{
                "is_valid": true/false,
                "readability": 0-10,
                "seo_score": 0-10,
                "engagement_score": 0-10,
                "quality_analysis": {{
                    "content_depth": 0-10,
                    "factual_accuracy": 0-10,
                    "brand_consistency": 0-10,
                    "accessibility_relevance": 0-10
                }},
                "suggestions": [
                    "suggestion 1",
                    "suggestion 2"
                ],
                "issues": "Any critical issues that make the content unsuitable (if applicable)"
            }}
            
            Set "is_valid" to false if the content is not directly related to web accessibility or
            if it contains major factual errors about accessibility standards.
        """)
        
    async def validate_content(self, content: str, company_context: str) -> Dict:
        """
        Validate content quality and provide improvement suggestions.
        Also ensures the content is relevant to web accessibility.
        
        Args:
            content: The blog post content to validate
            company_context: Context about the company for brand voice consistency
            
        Returns:
            Dictionary containing validation results and suggestions
        """
        # First, check if content is relevant to web accessibility
        is_relevant = await self._check_accessibility_relevance(content)
        if not is_relevant:
            log_warning("Content fails accessibility relevance check", "QUALITY")
            return {
                "is_valid": False,
                "readability": 0,
                "seo_score": 0,
                "engagement_score": 0,
                "quality_analysis": {
                    "content_depth": 0,
                    "factual_accuracy": 0,
                    "brand_consistency": 0
                },
                "suggestions": [
                    "The content isn't relevant to web accessibility or related topics",
                    "Revise to focus on web accessibility, ADA compliance, WCAG standards, or digital inclusion",
                    "Ensure the content aligns with WebAbility.io's core business focus"
                ],
                "issues": "Content is off-topic for web accessibility. Our brand focuses on accessibility topics only."
            }
            
        # Continue with regular validation if content is relevant
        chain = self.quality_prompt | self.llm | StrOutputParser()
        
        try:
            log_debug("Starting content validation", "QUALITY")
            log_debug("Using gpt-3.5-turbo for content validation", "QUALITY")
            result_str = await chain.ainvoke({
                "content": content,
                "company_context": company_context
            })
            log_debug("Received validation response from LLM", "QUALITY")
            
            # Parse JSON result
            try:
                result = json.loads(result_str)
                log_debug("Successfully parsed validation JSON", "QUALITY")
            except json.JSONDecodeError:
                log_error("Error parsing validation result JSON", "QUALITY")
                result = {}
            
            # Add readability metrics
            log_debug("Calculating readability metrics", "QUALITY")
            readability_scores = self._calculate_readability(content)
            result.update(readability_scores)
            log_debug("Updated result with readability scores", "QUALITY")
            
            # Ensure required fields exist
            result.setdefault("is_valid", True)
            result.setdefault("readability", 0)
            result.setdefault("seo_score", 0)
            result.setdefault("engagement_score", 0)
            result.setdefault("quality_analysis", {
                "content_depth": 0,
                "factual_accuracy": 0,
                "brand_consistency": 0
            })
            result.setdefault("suggestions", [])
            
            return result
            
        except Exception as e:
            log_error(f"Error during content validation: {str(e)}", "QUALITY")
            return {}
            
    def _calculate_readability(self, content: str) -> Dict:
        """Calculate various readability metrics."""
        import textstat
        
        return {
            "readability": {
                "flesch_reading_ease": textstat.flesch_reading_ease(content),
                "flesch_kincaid_grade": textstat.flesch_kincaid_grade(content),
                "gunning_fog": textstat.gunning_fog(content),
                "smog_index": textstat.smog_index(content)
            }
        }
        
    def check_plagiarism(self, content: str) -> Tuple[float, List[Dict]]:
        """
        Check content for potential plagiarism.
        
        Args:
            content: The content to check
            
        Returns:
            Tuple of (similarity_score, list of similar sources)
        """
        from difflib import SequenceMatcher
        import requests
        
        # This is a simplified version. In production, you'd want to use
        # a proper plagiarism detection service API
        
        def similar(a: str, b: str) -> float:
            return SequenceMatcher(None, a, b).ratio()
            
        # Search for similar content online
        # This is just a placeholder - you'd want to use a proper search API
        similar_sources = []
        similarity_score = 0.0
        
        return similarity_score, similar_sources
        
    async def _check_accessibility_relevance(self, content: str) -> bool:
        """
        Check if content is relevant to web accessibility or related topics.
        
        Args:
            content: The blog post content to validate
            
        Returns:
            Boolean indicating if content is relevant to accessibility
        """
        # Define a prompt to check relevance
        relevance_prompt = PromptTemplate.from_template("""
            As a web accessibility expert, evaluate whether the following content is relevant 
            to web accessibility or related topics such as:
            - ADA compliance and accessibility laws
            - WCAG standards and implementation
            - Digital inclusion and assistive technology
            - Screen readers and accessibility tools
            - SEO as it relates to accessibility
            - UX design for accessibility
            - Accessibility in ecommerce
            - Technical accessibility implementation
            - Mobile accessibility
            - Content accessibility best practices
            - Emerging technologies and accessibility
            - Accessibility auditing and testing
            
            Our company, WebAbility.io, primarily focuses on web accessibility solutions and content,
            but we also cover trending topics in digital inclusion, SEO, and user experience that relate to accessibility.
            
            Content:
            {content}
            
            Is this content relevant to web accessibility or related topics that would be valuable to our audience?
            Respond with just "YES" or "NO", followed by a single sentence explanation.
        """)
        
        # Use a simpler model for this quick check
        check_llm = ChatOpenAI(model="gpt-3.5-turbo")
        check_chain = relevance_prompt | check_llm | StrOutputParser()
        
        try:
            log_debug("Checking content relevance to web accessibility", "QUALITY")
            result = await check_chain.ainvoke({"content": content[:4000]})  # Limit content length
            
            # Parse result - look for YES/NO at the beginning
            is_relevant = result.strip().upper().startswith("YES")
            
            if is_relevant:
                log_debug("Content passed accessibility relevance check", "QUALITY")
            else:
                log_warning(f"Content failed accessibility relevance check: {result}", "QUALITY")
                
            return is_relevant
            
        except Exception as e:
            log_error(f"Error during accessibility relevance check: {str(e)}", "QUALITY")
            # Default to True in case of error to avoid false rejections
            return True
    
    def suggest_improvements(self, validation_results: Dict) -> List[str]:
        """Generate specific improvement suggestions based on validation results."""
        suggestions = []
        
        if validation_results.get("readability", {}).get("flesch_reading_ease", 0) < 60:
            suggestions.append("Consider simplifying language for better readability")
            
        if validation_results.get("seo_score", 0) < 7:
            suggestions.append("Optimize keyword placement and density")
            
        if validation_results.get("engagement_score", 0) < 7:
            suggestions.append("Add more real-world examples and case studies")
            
        return suggestions
