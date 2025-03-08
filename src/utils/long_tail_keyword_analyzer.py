"""
Long-tail keyword analyzer and generator for blog content.
This module specializes in identifying opportunities for long-tail keywords
and generating niche, specific keyword suggestions based on content analysis.
"""
from typing import List, Dict, Any, Optional, Tuple
import re
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.util import ngrams
import json
from pathlib import Path

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Initialize stopwords
STOP_WORDS = set(stopwords.words('english'))

class LongTailKeywordAnalyzer:
    """Analyzer for identifying and generating long-tail keyword opportunities."""
    
    def __init__(self, industry_specific_terms: Optional[Dict[str, List[str]]] = None):
        """
        Initialize the long-tail keyword analyzer.
        
        Args:
            industry_specific_terms: Optional dictionary mapping industries to relevant terms
        """
        # Default industry-specific terms if none provided
        self.industry_specific_terms = industry_specific_terms or {
            "healthcare": ["patient portal", "medical records", "healthcare providers", "telehealth"],
            "ecommerce": ["online shopping", "product catalog", "checkout process", "shopping cart"],
            "finance": ["banking", "financial services", "investment", "payment processing"],
            "education": ["learning management", "course content", "student portal", "educational resources"],
            "government": ["public services", "citizen access", "government portal", "public records"],
            "technology": ["software", "applications", "user interface", "digital products"]
        }
        
        # Question patterns for generating question-based long-tail keywords
        self.question_patterns = [
            "how to {verb} {noun}",
            "what is {adjective} {noun}",
            "why is {noun} {adjective}",
            "when should {noun} be {verb}",
            "which {noun} is best for {purpose}",
            "where to find {adjective} {noun}",
            "who needs {noun} for {purpose}",
            "can {noun} {verb} {object}"
        ]
        
        # Implementation-specific keyword patterns
        self.implementation_patterns = [
            "implementing {feature} for {platform}",
            "how to test {feature} with {tool}",
            "step-by-step guide to {action} {feature}",
            "best practices for {feature} in {context}",
            "{feature} requirements for {industry}",
            "{feature} compliance checklist for {standard}",
            "automating {feature} testing with {tool}",
            "common {feature} issues and solutions"
        ]
        
        # User-specific keyword patterns
        self.user_specific_patterns = [
            "accessibility for users with {disability}",
            "designing for users who {limitation}",
            "{feature} for users with {need}",
            "how {disability} users navigate {feature}",
            "making {feature} accessible to {user_group}",
            "{feature} requirements for {disability} compliance",
            "testing {feature} with users who {limitation}"
        ]
    
    def extract_potential_keywords(self, content: str) -> List[str]:
        """
        Extract potential keyword phrases from content.
        
        Args:
            content: The blog content to analyze
            
        Returns:
            List of potential keyword phrases
        """
        # Tokenize content
        sentences = sent_tokenize(content.lower())
        
        # Extract n-grams (2-4 word phrases)
        all_ngrams = []
        for sentence in sentences:
            # Clean and tokenize
            clean_sentence = re.sub(r'[^\w\s]', '', sentence)
            tokens = word_tokenize(clean_sentence)
            filtered_tokens = [token for token in tokens if token not in STOP_WORDS and len(token) > 2]
            
            # Generate n-grams
            for n in range(2, 5):  # 2, 3, and 4-grams
                sentence_ngrams = list(ngrams(filtered_tokens, n))
                all_ngrams.extend([' '.join(gram) for gram in sentence_ngrams])
        
        # Count frequency
        ngram_counter = Counter(all_ngrams)
        
        # Return most common n-grams
        return [item[0] for item in ngram_counter.most_common(50)]
    
    def identify_industry_relevance(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        Identify industry relevance of extracted keywords.
        
        Args:
            keywords: List of potential keywords
            
        Returns:
            Dictionary mapping industries to relevant keywords
        """
        industry_keywords = {industry: [] for industry in self.industry_specific_terms}
        
        for keyword in keywords:
            for industry, terms in self.industry_specific_terms.items():
                if any(term in keyword for term in terms):
                    industry_keywords[industry].append(keyword)
        
        # Filter out empty industries
        return {k: v for k, v in industry_keywords.items() if v}
    
    def generate_question_keywords(self, base_keywords: List[str]) -> List[str]:
        """
        Generate question-based long-tail keywords.
        
        Args:
            base_keywords: List of base keywords to transform
            
        Returns:
            List of question-based long-tail keywords
        """
        question_keywords = []
        
        for keyword in base_keywords:
            # Split into parts for substitution
            parts = keyword.split()
            if len(parts) < 2:
                continue
                
            # Identify potential parts of speech (simplified)
            noun = parts[-1]  # Assume last word is a noun
            verb = "implement" if "implement" not in keyword else "optimize"
            adjective = "effective" if "effective" not in keyword else "accessible"
            purpose = "accessibility" if "accessibility" not in keyword else "compliance"
            object = "website" if "website" not in keyword else "application"
            
            # Generate questions using patterns
            for pattern in self.question_patterns:
                question = pattern.format(
                    noun=noun,
                    verb=verb,
                    adjective=adjective,
                    purpose=purpose,
                    object=object
                )
                question_keywords.append(question)
        
        return question_keywords[:20]  # Limit to top 20
    
    def generate_implementation_keywords(self, base_keywords: List[str]) -> List[str]:
        """
        Generate implementation-specific long-tail keywords.
        
        Args:
            base_keywords: List of base keywords to transform
            
        Returns:
            List of implementation-specific long-tail keywords
        """
        implementation_keywords = []
        
        # Common implementation contexts
        platforms = ["WordPress", "Shopify", "React", "Angular", "mobile apps"]
        tools = ["screen readers", "automated testing", "WAVE", "axe", "Lighthouse"]
        actions = ["implementing", "testing", "optimizing", "auditing"]
        contexts = ["e-commerce", "healthcare", "education", "government", "SaaS"]
        standards = ["WCAG 2.1", "ADA", "Section 508", "EAA"]
        
        for keyword in base_keywords:
            # Extract feature from keyword
            feature = keyword
            
            # Generate implementation keywords
            for pattern in self.implementation_patterns:
                # Randomly select context elements
                platform = platforms[hash(keyword) % len(platforms)]
                tool = tools[hash(keyword + "1") % len(tools)]
                action = actions[hash(keyword + "2") % len(actions)]
                context = contexts[hash(keyword + "3") % len(contexts)]
                standard = standards[hash(keyword + "4") % len(standards)]
                
                # Format pattern
                impl_keyword = pattern.format(
                    feature=feature,
                    platform=platform,
                    tool=tool,
                    action=action,
                    context=context,
                    industry=context,
                    standard=standard
                )
                implementation_keywords.append(impl_keyword)
        
        return implementation_keywords[:20]  # Limit to top 20
    
    def generate_user_specific_keywords(self, base_keywords: List[str]) -> List[str]:
        """
        Generate user-specific long-tail keywords.
        
        Args:
            base_keywords: List of base keywords to transform
            
        Returns:
            List of user-specific long-tail keywords
        """
        user_keywords = []
        
        # Common user-specific contexts
        disabilities = [
            "visual impairments", "blindness", "color blindness", 
            "hearing impairments", "motor disabilities", "cognitive disabilities"
        ]
        limitations = [
            "use keyboard only", "use screen readers", "have limited vision",
            "need enlarged text", "require high contrast", "have reading difficulties"
        ]
        needs = [
            "navigation assistance", "content simplification", "audio alternatives",
            "keyboard shortcuts", "touch targets", "error recovery"
        ]
        user_groups = [
            "screen reader users", "keyboard-only users", "low-vision users",
            "elderly users", "users with dyslexia", "users with tremors"
        ]
        
        for keyword in base_keywords:
            # Extract feature from keyword
            feature = keyword
            
            # Generate user-specific keywords
            for pattern in self.user_specific_patterns:
                # Randomly select context elements
                disability = disabilities[hash(keyword) % len(disabilities)]
                limitation = limitations[hash(keyword + "1") % len(limitations)]
                need = needs[hash(keyword + "2") % len(needs)]
                user_group = user_groups[hash(keyword + "3") % len(user_groups)]
                
                # Format pattern
                user_keyword = pattern.format(
                    feature=feature,
                    disability=disability,
                    limitation=limitation,
                    need=need,
                    user_group=user_group
                )
                user_keywords.append(user_keyword)
        
        return user_keywords[:20]  # Limit to top 20
    
    def analyze_content_for_long_tail(self, content: str) -> Dict[str, Any]:
        """
        Analyze content for long-tail keyword opportunities.
        
        Args:
            content: The blog content to analyze
            
        Returns:
            Dictionary with analysis results and keyword suggestions
        """
        # Extract potential base keywords
        base_keywords = self.extract_potential_keywords(content)
        
        # Identify industry relevance
        industry_keywords = self.identify_industry_relevance(base_keywords)
        
        # Generate different types of long-tail keywords
        question_keywords = self.generate_question_keywords(base_keywords[:10])
        implementation_keywords = self.generate_implementation_keywords(base_keywords[:10])
        user_specific_keywords = self.generate_user_specific_keywords(base_keywords[:10])
        
        # Combine all long-tail keywords
        all_long_tail = question_keywords + implementation_keywords + user_specific_keywords
        
        # Analyze current content for long-tail keyword usage
        long_tail_usage = sum(1 for keyword in all_long_tail if keyword in content.lower())
        long_tail_score = min(10, (long_tail_usage / len(all_long_tail)) * 100)
        
        return {
            "base_keywords": base_keywords[:20],
            "industry_relevant_keywords": industry_keywords,
            "long_tail_keywords": {
                "question_based": question_keywords,
                "implementation_specific": implementation_keywords,
                "user_specific": user_specific_keywords
            },
            "long_tail_usage": {
                "count": long_tail_usage,
                "score": long_tail_score,
                "needs_improvement": long_tail_score < 5
            }
        }
    
    def generate_long_tail_suggestions(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate suggestions for improving long-tail keyword usage.
        
        Args:
            analysis: Analysis results from analyze_content_for_long_tail
            
        Returns:
            List of suggestion dictionaries
        """
        suggestions = []
        
        # Check if long-tail keyword usage needs improvement
        if analysis["long_tail_usage"]["needs_improvement"]:
            # Add general suggestion
            suggestions.append({
                "category": "Long-Tail Keywords",
                "issue": "Limited use of specific, long-tail keywords",
                "suggestion": "Incorporate more specific, niche keywords to target qualified traffic"
            })
            
            # Add question-based keyword suggestion
            question_examples = ", ".join(analysis["long_tail_keywords"]["question_based"][:3])
            suggestions.append({
                "category": "Question-Based Keywords",
                "issue": "Few question-based keywords that match user queries",
                "suggestion": f"Add question formats like: {question_examples}"
            })
            
            # Add implementation-specific keyword suggestion
            impl_examples = ", ".join(analysis["long_tail_keywords"]["implementation_specific"][:3])
            suggestions.append({
                "category": "Implementation Keywords",
                "issue": "Limited technical implementation keywords",
                "suggestion": f"Include specific implementation details like: {impl_examples}"
            })
            
            # Add user-specific keyword suggestion
            user_examples = ", ".join(analysis["long_tail_keywords"]["user_specific"][:3])
            suggestions.append({
                "category": "User-Specific Keywords",
                "issue": "Few keywords targeting specific user needs",
                "suggestion": f"Address specific user needs with keywords like: {user_examples}"
            })
            
            # Add industry-specific suggestion if relevant
            if analysis["industry_relevant_keywords"]:
                industry = next(iter(analysis["industry_relevant_keywords"]))
                industry_examples = ", ".join(analysis["industry_relevant_keywords"][industry][:3])
                suggestions.append({
                    "category": "Industry-Specific Keywords",
                    "issue": f"Could better target {industry} industry",
                    "suggestion": f"Expand {industry}-specific keywords like: {industry_examples}"
                })
        
        return suggestions

def analyze_blog_for_long_tail_keywords(content: str) -> Dict[str, Any]:
    """
    Analyze a blog post for long-tail keyword opportunities.
    
    Args:
        content: The blog content to analyze
        
    Returns:
        Dictionary with analysis results and suggestions
    """
    analyzer = LongTailKeywordAnalyzer()
    analysis = analyzer.analyze_content_for_long_tail(content)
    suggestions = analyzer.generate_long_tail_suggestions(analysis)
    
    return {
        "analysis": analysis,
        "suggestions": suggestions
    }

def save_long_tail_analysis(content: str, output_dir: str = "analysis") -> str:
    """
    Analyze blog for long-tail keywords and save results.
    
    Args:
        content: Blog content to analyze
        output_dir: Directory to save analysis results
        
    Returns:
        Path to the saved analysis file
    """
    # Analyze content
    analysis_results = analyze_blog_for_long_tail_keywords(content)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save analysis
    analysis_file = output_path / "long_tail_keyword_analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analysis_results, f, indent=2)
    
    return str(analysis_file)

if __name__ == "__main__":
    # Example usage
    example_content = """
    Digital accessibility is important for websites. WCAG guidelines help make websites accessible.
    Screen readers are used by people with visual impairments to navigate websites.
    """
    
    analysis_path = save_long_tail_analysis(example_content)
    print(f"Long-tail keyword analysis saved to: {analysis_path}")