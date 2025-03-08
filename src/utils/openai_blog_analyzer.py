"""
OpenAI-powered blog post analyzer focused on accessibility and content quality.
Uses functional programming patterns, Pydantic models, and structured outputs.
"""
from typing import List, Any, Optional, Dict, Tuple
import os
from pathlib import Path
import json
from datetime import datetime
from functools import partial
import asyncio
import openai
from dotenv import load_dotenv
from src.models.analysis_models import BlogAnalysis, AnalysisSection, AnalysisRequest

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define structured output schema for OpenAI
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "number",
            "description": "Score from 0-10 based on evaluation criteria",
            "minimum": 0,
            "maximum": 10
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of 2-3 concrete strengths with specific examples"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of 2-3 specific areas needing improvement"
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of 2-3 clear, implementable changes"
        }
    },
    "required": ["score", "strengths", "weaknesses", "suggestions"]
}

async def get_openai_response(prompt: str) -> Optional[Dict[str, Any]]:
    """Get structured response from OpenAI with error handling."""
    try:
        # Early validation
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        
        # Make async API call
        response = await openai.chat.completions.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"},
            functions=[{
                "name": "analyze_section",
                "parameters": ANALYSIS_SCHEMA
            }],
            function_call={"name": "analyze_section"}
        )
        
        # Parse and validate response
        try:
            return json.loads(response.choices[0].message.function_call.arguments)
        except json.JSONDecodeError as e:
            print(f"Error parsing OpenAI response: {e}")
            return None
            
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def create_analysis_prompt(
    request: AnalysisRequest,
    blog_context: str = "",
    competitor_insights: Optional[Dict[str, List[str]]] = None
) -> str:
    """Create focused analysis prompt with clear evaluation criteria."""
    # Base prompt
    prompt_parts = [
        f"Analyze this blog post about web accessibility, focusing on {request.analysis_type}:",
        f"\n{request.content}"
    ]
    
    # Add competitor insights if available
    if competitor_insights:
        prompt_parts.append("\nConsider these competitor insights:")
        if competitor_insights.get('common_headings'):
            prompt_parts.append("Common Headings:")
            prompt_parts.extend(f"- {h}" for h in competitor_insights['common_headings'])
        if competitor_insights.get('popular_keywords'):
            prompt_parts.append("\nPopular Keywords:")
            prompt_parts.extend(f"- {k}" for k in competitor_insights['popular_keywords'])
        if competitor_insights.get('heading_patterns'):
            prompt_parts.append("\nCommon Blog Structures:")
            prompt_parts.extend(f"- {p}" for p in competitor_insights['heading_patterns'])
    
    # Add blog context if available
    if blog_context:
        prompt_parts.append(f"\nReference these insights from our previous blogs:\n{blog_context}")
    
    # Add evaluation criteria
    prompt_parts.extend([
        "\nEvaluate these aspects:",
        *[f"- {point}" for point in request.evaluation_points],
        "\nProvide a structured analysis following the JSON schema. Include:",
        "- score (0-10): A single number based on evaluation criteria",
        "- strengths: 2-3 concrete strengths with specific examples",
        "- weaknesses: 2-3 specific areas needing improvement",
        "- suggestions: 2-3 clear, implementable changes",
        "\nKeep responses brief and actionable. Avoid generic feedback.",
        f"Focus on {request.analysis_type} best practices and provide specific examples.",
        "\nReturn the analysis in valid JSON format matching the schema."
    ])
    
    return "\n".join(prompt_parts)



def get_openai_response(prompt: str) -> Optional[str]:
    """Get response from OpenAI with error handling."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def extract_score(lines: List[str]) -> float:
    """Extract score from response lines with error handling."""
    try:
        score_lines = [l for l in lines if "Score" in l]
        if not score_lines:
            return 5.0
        score_text = score_lines[0].split(":")[-1].strip()
        return float(score_text)
    except (ValueError, IndexError):
        return 5.0

def extract_section_content(lines: List[str], section_num: int, section_name: str) -> List[str]:
    """Extract content from a numbered section."""
    section_start = f"{section_num}. {section_name}"
    section_lines = []
    in_section = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith(section_start):
            in_section = True
            continue
        elif line[0].isdigit() and line[1] == ".":
            in_section = False
        elif in_section and line.startswith("-"):
            section_lines.append(line.strip("- *"))
    
    return section_lines

def clean_insights(insights: List[str]) -> List[str]:
    """Clean and deduplicate insights."""
    # Remove empty, numbered, or generic lines
    filtered = [
        line.strip() for line in insights 
        if line.strip() 
        and not line[0].isdigit() 
        and not line.lower().startswith(("strengths:", "areas", "suggestions:", "score:"))
    ]
    # Remove duplicates while preserving order
    seen = set()
    return [x for x in filtered if not (x.lower() in seen or seen.add(x.lower()))]

def parse_response(result: Optional[str]) -> Tuple[float, List[str], List[str], List[str]]:
    """Parse OpenAI response with error handling."""
    if not result:
        return 5.0, ["Basic content"], ["Needs improvement"], ["Add more details"]
    
    lines = result.split("\n")
    score = extract_score(lines)
    
    # Extract sections using functional approach
    raw_strengths = extract_section_content(lines, 2, "Strengths")
    raw_improvements = extract_section_content(lines, 3, "Areas to Improve")
    raw_suggestions = extract_section_content(lines, 4, "Actionable Suggestions")
    
    # Clean and deduplicate insights
    strengths = clean_insights(raw_strengths) or ["Content provides basic information"]
    weaknesses = clean_insights(raw_improvements) or ["Could be enhanced with more specific examples"]
    suggestions = clean_insights(raw_suggestions) or ["Consider adding more concrete details"]
    
    return score, strengths, weaknesses, suggestions

async def analyze_with_openai(
    request: AnalysisRequest,
    blog_context: str = "",
    competitor_insights: Optional[Dict[str, List[str]]] = None
) -> AnalysisSection:
    """Analyze content using OpenAI with structured outputs."""
    # Early validation
    if not request.content:
        raise ValueError("Content cannot be empty")
    
    # Default analysis for error cases
    default_analysis = AnalysisSection(
        score=5.0,
        strengths=["Content provides basic information"],
        weaknesses=["Could be enhanced with more specific examples"],
        suggestions=["Consider adding more concrete details"]
    )
    
    try:
        # Create analysis prompt
        prompt = create_analysis_prompt(
            request=request,
            blog_context=blog_context,
            competitor_insights=competitor_insights
        )
        
        # Get OpenAI response
        response = await get_openai_response(prompt)
        if not response:
            return default_analysis
        
        # Parse and validate response
        return AnalysisSection(**response)
        
    except ValueError as e:
        print(f"Validation error: {e}")
        return default_analysis
    except Exception as e:
        print(f"Error in analysis: {e}")
        return AnalysisSection(
            score=5.0,
            strengths=["Content structure unclear"],
            weaknesses=["Analysis failed to parse response"],
            suggestions=["Please try again or contact support"]
        )

# Analysis configurations
ANALYSIS_CONFIGS = {
    "structure": [
        "Paragraph organization and length",
        "Sentence structure and clarity",
        "Headers and subheaders",
        "Logical flow and transitions",
        "Content hierarchy"
    ],
    "accessibility": [
        "Coverage of key accessibility standards (WCAG, ADA, Section 508)",
        "Technical accuracy of accessibility terms",
        "Explanation of accessibility features",
        "Real-world applications and examples",
        "Target audience understanding"
    ],
    "empathy": [
        "Understanding of user challenges",
        "Inclusive language",
        "Emotional connection",
        "User-centric perspective",
        "Supportive tone"
    ]
}

async def analyze_content(
    content: str,
    keyword: Optional[str] = None,
    competitor_insights: Optional[Dict[str, List[str]]] = None
) -> BlogAnalysis:
    """Perform comprehensive content analysis using structured outputs."""
    # Early validation
    if not content:
        raise ValueError("Content cannot be empty")
    
    try:
        # Get relevant blog context for each analysis type
        from .initialize_blog_context import get_blog_context
        contexts = {
            analysis_type: get_blog_context(
                f"{analysis_type} {keyword if keyword else ' '.join(points)}"
            )
            for analysis_type, points in ANALYSIS_CONFIGS.items()
        }
        
        # Prepare analysis requests
        analysis_requests = []
        for analysis_type, evaluation_points in ANALYSIS_CONFIGS.items():
            # Add keyword to evaluation points if provided
            points = list(evaluation_points)
            if keyword:
                points.append(f"Relevance and usage of keyword: {keyword}")
            
            # Create analysis request
            request = AnalysisRequest(
                content=content,
                analysis_type=analysis_type,
                evaluation_points=points
            )
            analysis_requests.append((analysis_type, request))
        
        # Run all analyses concurrently
        analysis_tasks = [
            analyze_with_openai(
                request=request,
                blog_context=contexts[analysis_type],
                competitor_insights=competitor_insights
            )
            for analysis_type, request in analysis_requests
        ]
        analysis_results = await asyncio.gather(*analysis_tasks)
        
        # Map results to analysis types
        analyses = {
            request[0]: result 
            for request, result in zip(analysis_requests, analysis_results)
        }
        
        # Calculate overall score
        scores = [section.score for section in analyses.values()]
        overall_score = sum(scores) / len(scores)
        
        # Return validated analysis
        return BlogAnalysis(
            overall_score=overall_score,
            structure=analyses["structure"],
            accessibility=analyses["accessibility"],
            empathy=analyses["empathy"]
        )
        
    except ValueError as e:
        raise ValueError(f"Analysis validation error: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error in analysis: {e}")

def format_section_report(section: AnalysisSection, title: str) -> List[str]:
    """Format a section of the analysis report."""
    return [
        f"## {title} Analysis",
        f"Score: {section.score:.1f}/10\n",
        "### Strengths",
        *[f"- {strength}" for strength in section.strengths],
        "\n### Areas for Improvement",
        *[f"- {weakness}" for weakness in section.weaknesses],
        "\n### Suggestions",
        *[f"- {suggestion}" for suggestion in section.suggestions],
        "\n"
    ]

def generate_report(analysis: BlogAnalysis) -> str:
    """Generate a markdown report from analysis results using Pydantic models."""
    # Start with header and overall score
    report_sections = [
        "# Blog Post Analysis Report\n",
        f"## Overall Score: {analysis.overall_score:.1f}/10\n"
    ]
    
    # Define sections to analyze
    sections = [
        ("Structure", analysis.structure),
        ("Accessibility", analysis.accessibility),
        ("Empathy", analysis.empathy)
    ]
    
    # Use list comprehension to flatten the sections
    section_lines = [
        line 
        for title, section in sections
        for line in format_section_report(section, title)
    ]
    
    report_sections.extend(section_lines)
    return "\n".join(report_sections)

def generate_report(analysis: BlogAnalysis) -> str:
    """Generate a markdown report from analysis results using Pydantic models."""
    report_sections = [
        "# Blog Post Analysis Report\n",
        f"## Overall Score: {analysis.overall_score:.1f}/10\n"
    ]
    
    sections = [
        ("Structure", analysis.structure),
        ("Accessibility", analysis.accessibility),
        ("Empathy", analysis.empathy)
    ]
    
    for title, section in sections:
        report_sections.extend(format_section_report(section, title))
    
    return "\n".join(report_sections)

async def analyze_and_save(
    content: str,
    output_dir: str = "analysis",
    keyword: Optional[str] = None,
    competitor_insights: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Path]:
    """Analyze content and save results with optional keyword and competitor insights."""
    try:
        # Early validation
        if not content:
            raise ValueError("Content cannot be empty")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate timestamp once for consistent filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Analyze content
        analysis = await analyze_content(
            content=content,
            keyword=keyword,
            competitor_insights=competitor_insights
        )
        
        # Generate report
        report = generate_report(analysis)
        
        # Save analysis as JSON
        analysis_file = output_path / f"analysis_{timestamp}.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis.model_dump(), f, indent=2)
        
        # Save report as markdown
        report_file = output_path / f"report_{timestamp}.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        return {
            "analysis_file": analysis_file,
            "report_file": report_file
        }
        
    except ValueError as e:
        raise ValueError(f"Invalid input: {str(e)}")
    except Exception as e:
        raise Exception(f"Analysis error: {str(e)}")

if __name__ == "__main__":
    example = "This is an example blog post about web accessibility..."
    try:
        report_path = analyze_and_save(example)
        print(f"Analysis saved to: {report_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
