"""Content validator agent that checks quality, accuracy, and SEO metrics."""

from typing import Dict, List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class ContentValidatorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4")
        self.quality_prompt = PromptTemplate.from_template("""
            As a professional content validator, analyze the following blog post for:
            1. Content quality and depth
            2. Factual accuracy
            3. SEO optimization
            4. Readability and engagement
            5. Brand voice consistency
            
            Blog post:
            {content}
            
            Company context:
            {company_context}
            
            Provide a detailed analysis with specific recommendations for improvement.
            Rate each aspect on a scale of 1-10 and explain why.
            Format your response in JSON.
        """)
        
    def validate_content(self, content: str, company_context: str) -> Dict:
        """
        Validate content quality and provide improvement suggestions.
        
        Args:
            content: The blog post content to validate
            company_context: Context about the company for brand voice consistency
            
        Returns:
            Dictionary containing validation results and suggestions
        """
        chain = self.quality_prompt | self.llm | StrOutputParser()
        
        try:
            result = chain.invoke({
                "content": content,
                "company_context": company_context
            })
            
            # Add readability metrics
            readability_scores = self._calculate_readability(content)
            result.update(readability_scores)
            
            return result
            
        except Exception as e:
            print(f"Error during content validation: {str(e)}")
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
