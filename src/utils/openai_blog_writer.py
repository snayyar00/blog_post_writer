"""
OpenAI-powered blog writer focused on viral content and business impact.
Uses functional programming patterns and structured outputs.
"""
from typing import Dict, List, Optional, Any
import os
import json
import re
from datetime import datetime
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ContentMetrics(BaseModel):
    """Metrics for content performance and impact."""
    viral_potential: Dict[str, float] = {
        'shareability': 0.0,
        'emotional_impact': 0.0,
        'trending_topic_fit': 0.0,
        'social_media_potential': 0.0
    }
    business_impact: Dict[str, float] = {
        'sales_potential': 0.0,
        'lead_generation': 0.0,
        'brand_authority': 0.0,
        'customer_education': 0.0
    }
    content_type: Dict[str, float] = {
        'educational': 0.0,
        'sales': 0.0,
        'thought_leadership': 0.0
    }
    funnel_stage: str = "middle"
    reader_level: str = "intermediate"
    read_time_minutes: int = 5
    
    # Enhanced content metrics
    readability_score: float = 0.0
    seo_score: float = 0.0
    engagement_score: float = 0.0
    has_real_data: bool = False
    has_case_studies: bool = False
    has_expert_quotes: bool = False
    enhanced_formatting: bool = False

class EnhancementData(BaseModel):
    """Data related to content enhancements."""
    industry: Optional[str] = None
    case_studies: List[Dict[str, str]] = []
    expert_quotes: List[Dict[str, str]] = []
    statistics: List[Dict[str, str]] = []
    has_enhanced_formatting: bool = False

class BlogPost(BaseModel):
    """Generated blog post with metrics."""
    title: str
    content: str
    metrics: ContentMetrics
    keywords: List[str]
    outline: List[str]
    
    # Enhanced content features
    industry: Optional[str] = None
    enhancement_data: Optional[EnhancementData] = None
    generation_time: Optional[float] = None
    
    def model_dump(self) -> Dict[str, Any]:
        """Custom serialization to handle metrics."""
        data = {
            'title': self.title,
            'content': self.content,
            'metrics': self.metrics.model_dump(),
            'keywords': self.keywords,
            'outline': self.outline,
            'generation_time': self.generation_time
        }
        
        if self.industry:
            data['industry'] = self.industry
            
        if self.enhancement_data:
            data['enhancement_data'] = self.enhancement_data.model_dump()
            
        return data

def calculate_content_metrics(
    content: str,
    business_type: str,
    content_goal: str,
    competitor_insights: Optional[Dict[str, Any]] = None
) -> ContentMetrics:
    """Calculate content performance metrics based on analysis."""
    # Initialize metrics
    metrics = ContentMetrics()
    
    # Calculate read time (average 200 words per minute)
    word_count = len(content.split())
    metrics.read_time_minutes = max(1, round(word_count / 200))
    
    # Analyze viral potential based on content characteristics
    has_data = bool(re.search(r'\d+%|\d+\s+percent|statistics show', content.lower()))
    has_examples = bool(re.search(r'for example|such as|like|case study', content.lower()))
    has_actionable = bool(re.search(r'how to|steps|guide|tips|strategies', content.lower()))
    has_emotional = bool(re.search(r'amazing|incredible|surprising|essential|critical', content.lower()))
    
    # Update viral metrics
    metrics.viral_potential.update({
        'shareability': 85.0 if has_actionable and has_examples else 70.0,
        'emotional_impact': 92.0 if has_emotional else 75.0,
        'trending_topic_fit': 78.0 if competitor_insights else 65.0,
        'social_media_potential': 88.0 if has_data and has_examples else 72.0
    })
    
    # Calculate business impact based on goals
    goal_mapping = {
        'Drive Sales': {'sales_potential': 90.0, 'lead_generation': 85.0},
        'Build Authority': {'brand_authority': 95.0, 'customer_education': 88.0},
        'Generate Leads': {'lead_generation': 92.0, 'sales_potential': 85.0},
        'Increase Brand Awareness': {'brand_authority': 90.0, 'social_media_potential': 88.0},
        'Educate Users': {'customer_education': 95.0, 'brand_authority': 85.0}
    }
    
    if content_goal in goal_mapping:
        metrics.business_impact.update(goal_mapping[content_goal])
    
    # Determine content type distribution
    educational_markers = re.findall(r'learn|understand|how|what|why|when|guide|tutorial', content.lower())
    sales_markers = re.findall(r'buy|purchase|offer|deal|limited|exclusive|pricing|cost', content.lower())
    thought_leadership_markers = re.findall(r'industry|trends|future|innovation|strategy|expert|insight', content.lower())
    
    total_markers = len(educational_markers) + len(sales_markers) + len(thought_leadership_markers)
    if total_markers > 0:
        metrics.content_type.update({
            'educational': round(len(educational_markers) / total_markers, 2),
            'sales': round(len(sales_markers) / total_markers, 2),
            'thought_leadership': round(len(thought_leadership_markers) / total_markers, 2)
        })
    
    # Set funnel stage based on content analysis
    if len(sales_markers) > len(educational_markers):
        metrics.funnel_stage = "bottom"
    elif len(thought_leadership_markers) > len(educational_markers):
        metrics.funnel_stage = "top"
    else:
        metrics.funnel_stage = "middle"
    
    # Set reader level based on content complexity
    complex_words = re.findall(r'\b\w{10,}\b', content)
    if len(complex_words) > word_count * 0.05:
        metrics.reader_level = "advanced"
    elif len(complex_words) > word_count * 0.02:
        metrics.reader_level = "intermediate"
    else:
        metrics.reader_level = "beginner"
    
    return metrics

async def generate_blog_post(
    business_type: str,
    content_goal: str,
    competitor_insights: Optional[Dict[str, Any]] = None,
    keywords: Optional[List[str]] = None,
    temperature: float = 0.7
) -> Optional[BlogPost]:
    """Generate a viral blog post optimized for business goals."""
    try:
        # Create system prompt
        system_prompt = f"""You are an expert blog writer specializing in {business_type} content.
Your goal is to write viral content that {content_goal.lower()}.
Write in a professional yet approachable tone that connects with readers.
Avoid both corporate jargon and overly casual language (no 'Hey there, friend!').
Maintain a balanced, authoritative voice while being engaging.
Use data points, specific examples, and actionable insights."""
        

        # Create content prompt
        content_prompt = """Generate a comprehensive blog post that follows our established style and quality standards.

Essential elements to include:
1. A concise, benefit-driven headline (5-9 words) that clearly communicates value
2. A brief executive summary (2-3 sentences) at the beginning highlighting key takeaways
3. Industry-specific examples and case studies with real metrics
4. Research-backed data points and statistics that support your claims
5. Clear business impact focus throughout the content

Structure:
- Headline: Clear, specific, and benefit-focused
- Executive Summary: Concise overview for busy professionals
- Introduction: Start with a relevant industry challenge or opportunity
- Body: Well-structured sections with clear subheadings and actionable insights
- Conclusion: Summarize key points and include a strategic call-to-action

Tone and Style:
- Professional yet accessible language
- Authoritative but not condescending
- Strategic focus on business outcomes and ROI
- Balanced perspective with evidence-based recommendations

Avoid:
- Overly casual language or slang
- Generic advice without specific implementation steps
- Unsubstantiated claims without supporting evidence
- Excessive use of first-person narrative"""

        # Add competitor insights
        if competitor_insights:
            content_prompt += "\n\nIncorporate these competitor insights:"
            if competitor_insights.get('common_headings'):
                content_prompt += "\nPopular headings:\n" + "\n".join(f"- {h}" for h in competitor_insights['common_headings'][:5])
            if competitor_insights.get('popular_keywords'):
                content_prompt += "\nTrending keywords:\n" + "\n".join(f"- {k}" for k in competitor_insights['popular_keywords'][:5])

        # Add target keywords
        if keywords:
            content_prompt += f"\n\nTarget keywords:\n" + "\n".join(f"- {k}" for k in keywords)

        # Generate content with OpenAI
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_prompt}
            ],
            temperature=temperature,
            max_tokens=2000
        )

        # Extract content
        content = response.choices[0].message.content

        # Generate metrics based on content and goals
        metrics = calculate_content_metrics(
            content=content,
            business_type=business_type,
            content_goal=content_goal,
            competitor_insights=competitor_insights
        )

        # Extract title and outline
        lines = content.split("\n")
        title = lines[0].strip("#").strip()
        outline = [line.strip("#- ") for line in lines if line.startswith("#") or line.startswith("##")]

        # Create blog post
        return BlogPost(
            title=title,
            content=content,
            metrics=metrics,
            keywords=keywords or [],
            outline=outline
        )

    except Exception as e:
        print(f"Error generating blog post: {e}")
        raise ValueError(f"Failed to generate blog post: {str(e)}")
