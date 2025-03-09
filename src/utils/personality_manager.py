"""
Dynamic personality manager for content generation that adapts tone and style
based on topic characteristics while maintaining consistent core identity.
"""

from typing import Dict, List, Any, Tuple
import re
from dataclasses import dataclass
from src.utils.logging_manager import log_info, log_debug, log_warning, log_error

@dataclass
class TopicCharacteristics:
    """Characteristics that influence content personality."""
    technical_depth: float  # 0-10 scale
    business_impact: float  # 0-10 scale
    user_impact: float  # 0-10 scale
    compliance_level: float  # 0-10 scale
    implementation_complexity: float  # 0-10 scale

class PersonalityManager:
    """Manages dynamic content personality based on topic analysis."""
    
    def __init__(self):
        # Technical keywords that indicate depth
        self.technical_indicators = {
            'code', 'implementation', 'development', 'api', 'testing',
            'framework', 'integration', 'script', 'programming', 'backend',
            'frontend', 'database', 'architecture', 'infrastructure'
        }
        
        # Business-related keywords
        self.business_indicators = {
            'roi', 'cost', 'revenue', 'business', 'enterprise', 'strategy',
            'market', 'investment', 'budget', 'stakeholder', 'conversion',
            'analytics', 'metrics', 'performance'
        }
        
        # User-focused keywords
        self.user_indicators = {
            'user', 'experience', 'usability', 'interface', 'accessibility',
            'design', 'interaction', 'feedback', 'behavior', 'journey',
            'persona', 'navigation', 'engagement'
        }
        
        # Compliance-related keywords
        self.compliance_indicators = {
            'compliance', 'wcag', 'ada', 'section508', 'regulation',
            'requirement', 'standard', 'guideline', 'policy', 'legal',
            'audit', 'certification', 'conformance'
        }
        
        # Implementation complexity indicators
        self.complexity_indicators = {
            'complex', 'advanced', 'enterprise', 'integration', 'migration',
            'optimization', 'scalability', 'security', 'performance',
            'architecture', 'infrastructure'
        }
    
    def analyze_topic(self, keyword: str, context: Dict[str, Any] = None) -> TopicCharacteristics:
        """
        Analyze a topic to determine its characteristics.
        
        Args:
            keyword: The main topic keyword
            context: Additional context about the topic
            
        Returns:
            TopicCharacteristics with scores for each dimension
        """
        # Normalize keyword for analysis
        keyword_lower = keyword.lower()
        words = set(re.findall(r'\w+', keyword_lower))
        
        # Calculate base scores from keyword
        technical_score = self._calculate_indicator_score(words, self.technical_indicators)
        business_score = self._calculate_indicator_score(words, self.business_indicators)
        user_score = self._calculate_indicator_score(words, self.user_indicators)
        compliance_score = self._calculate_indicator_score(words, self.compliance_indicators)
        complexity_score = self._calculate_indicator_score(words, self.complexity_indicators)
        
        # Adjust scores based on context if provided
        if context:
            if 'research_findings' in context:
                # Analyze research findings for additional context
                findings = str(context['research_findings']).lower()
                words = set(re.findall(r'\w+', findings))
                
                # Update scores with context
                technical_score = max(technical_score, self._calculate_indicator_score(words, self.technical_indicators))
                business_score = max(business_score, self._calculate_indicator_score(words, self.business_indicators))
                user_score = max(user_score, self._calculate_indicator_score(words, self.user_indicators))
                compliance_score = max(compliance_score, self._calculate_indicator_score(words, self.compliance_indicators))
                complexity_score = max(complexity_score, self._calculate_indicator_score(words, self.complexity_indicators))
        
        return TopicCharacteristics(
            technical_depth=technical_score,
            business_impact=business_score,
            user_impact=user_score,
            compliance_level=compliance_score,
            implementation_complexity=complexity_score
        )
    
    def _calculate_indicator_score(self, words: set, indicators: set) -> float:
        """Calculate score based on presence of indicator words."""
        matches = words.intersection(indicators)
        return min(len(matches) * 2.5, 10.0)  # Scale to 0-10
    
    def get_personality_prompt(self, characteristics: TopicCharacteristics) -> str:
        """
        Generate a personality-driven prompt based on topic characteristics.
        
        Args:
            characteristics: TopicCharacteristics object with dimension scores
            
        Returns:
            Prompt string that guides content personality
        """
        # Core personality elements (always present)
        prompt = """
        CORE PERSONALITY:
        You are a passionate accessibility advocate and experienced technologist who deeply cares about digital inclusion.
        Your background includes:
        - 15+ years of hands-on development and accessibility experience
        - Personal connection to accessibility through family members with disabilities
        - Extensive work with major companies on accessibility implementations
        - Active involvement in open-source accessibility projects
        - Deep understanding of both technical and human aspects of digital inclusion
        
        YOUR CORE TRAITS:
        - Empathetic but practical
        - Passionate but data-driven
        - Technical expert who excels at making complex topics simple
        - Problem-solver who sees challenges as opportunities
        - Slightly witty, using relevant metaphors and examples
        """
        
        # Add technical depth personality elements
        if characteristics.technical_depth > 7:
            prompt += """
            TECHNICAL VOICE:
            - Write like a patient mentor teaching a junior developer
            - Use clear code examples and technical best practices
            - Break down complex concepts into digestible steps
            - Share insider tips from real-world implementations
            - Include troubleshooting advice for common issues
            """
        elif characteristics.technical_depth > 4:
            prompt += """
            TECHNICAL VOICE:
            - Balance technical detail with practical application
            - Include high-level code concepts without deep diving
            - Focus on implementation patterns and approaches
            - Provide technical context for business decisions
            """
        
        # Add business impact personality elements
        if characteristics.business_impact > 7:
            prompt += """
            BUSINESS VOICE:
            - Write like a strategic consultant with accessibility expertise
            - Focus on ROI and business value while maintaining empathy
            - Use real case studies and success metrics
            - Connect technical decisions to business outcomes
            - Provide clear action items for stakeholders
            """
        elif characteristics.business_impact > 4:
            prompt += """
            BUSINESS VOICE:
            - Balance business needs with accessibility requirements
            - Include basic cost-benefit analysis
            - Highlight business advantages of accessibility
            - Provide implementation timelines and resource needs
            """
        
        # Add user impact personality elements
        if characteristics.user_impact > 7:
            prompt += """
            USER-FOCUSED VOICE:
            - Write from the perspective of users with disabilities
            - Share real user stories and feedback
            - Focus on the human impact of accessibility
            - Include user testing insights and recommendations
            - Emphasize inclusive design principles
            """
        elif characteristics.user_impact > 4:
            prompt += """
            USER-FOCUSED VOICE:
            - Keep user needs at the forefront
            - Include basic user experience considerations
            - Highlight the importance of user testing
            - Provide user-centric implementation tips
            """
        
        # Add compliance personality elements
        if characteristics.compliance_level > 7:
            prompt += """
            COMPLIANCE VOICE:
            - Write like a knowledgeable guide through regulations
            - Break down complex requirements into clear steps
            - Provide practical compliance checklists
            - Include relevant legal context and implications
            - Share compliance testing and validation approaches
            """
        elif characteristics.compliance_level > 4:
            prompt += """
            COMPLIANCE VOICE:
            - Cover key compliance requirements
            - Explain basic legal implications
            - Provide general compliance guidance
            - Include basic testing recommendations
            """
        
        # Add implementation complexity elements
        if characteristics.implementation_complexity > 7:
            prompt += """
            IMPLEMENTATION VOICE:
            - Write like a senior architect sharing best practices
            - Break down complex implementations into phases
            - Provide detailed architecture considerations
            - Include scaling and performance guidance
            - Share risk mitigation strategies
            """
        elif characteristics.implementation_complexity > 4:
            prompt += """
            IMPLEMENTATION VOICE:
            - Provide clear implementation steps
            - Include basic architectural guidance
            - Focus on common implementation challenges
            - Share general best practices
            """
        
        # Add writing style guidelines based on characteristics mix
        prompt += """
        WRITING STYLE GUIDELINES:
        1. Start with a real-world scenario or problem that readers can relate to
        2. Use "we" and "you" to create connection while maintaining expertise
        3. Share relevant personal experiences or observations
        4. Include practical tips from actual projects
        5. Use metaphors and analogies to explain complex concepts
        6. End with an empowering call to action
        
        TONE ADJUSTMENTS:
        - Technical depth: {technical_depth}/10 (Higher = more technical detail)
        - Business impact: {business_impact}/10 (Higher = more ROI focus)
        - User impact: {user_impact}/10 (Higher = more empathy and user stories)
        - Compliance level: {compliance_level}/10 (Higher = more regulatory detail)
        - Implementation complexity: {implementation_complexity}/10 (Higher = more architectural guidance)
        """.format(
            technical_depth=characteristics.technical_depth,
            business_impact=characteristics.business_impact,
            user_impact=characteristics.user_impact,
            compliance_level=characteristics.compliance_level,
            implementation_complexity=characteristics.implementation_complexity
        )
        
        return prompt
