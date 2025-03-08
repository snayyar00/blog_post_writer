"""
Blog post analysis utilities focused on accessibility and content quality.
"""
from typing import Dict, List, Any, TypedDict, Optional
from pathlib import Path
import re
import json
from dataclasses import dataclass
from pydantic import BaseModel
from .keyword_research_manager import get_keyword_suggestions, create_research_log

class ContentStats(TypedDict):
    count: int
    avg_length: float
    issues: List[int]

class StructureAnalysis(TypedDict):
    paragraphs: ContentStats
    sentences: ContentStats

class AccessibilityTerm(TypedDict):
    description: str
    context: Optional[str]

class AccessibilityAnalysis(TypedDict):
    terms_covered: int
    coverage_score: float
    covered_terms: Dict[str, AccessibilityTerm]
    missing_terms: List[str]

class EmpathyAnalysis(TypedDict):
    empathy_score: float
    empathy_examples: List[str]
    needs_improvement: bool

class TechnicalAnalysis(TypedDict):
    requirements_met: Dict[str, bool]
    score: float

class FlowAnalysis(TypedDict):
    transition_count: int
    flow_score: float
    needs_improvement: bool

class ContentImprovement(BaseModel):
    category: str
    issue: str
    suggestion: str

class BlogAnalysis(BaseModel):
    structure: StructureAnalysis
    accessibility: AccessibilityAnalysis
    empathy: EmpathyAnalysis
    technical: TechnicalAnalysis
    flow: FlowAnalysis
    overall_score: float
    improvements: List[ContentImprovement]

# Constants
ACCESSIBILITY_TERMS = {
    "wcag": "Web Content Accessibility Guidelines - Core standard for web accessibility",
    "ada": "Americans with Disabilities Act - Legal requirement for accessibility",
    "section 508": "Federal accessibility requirements",
    "screen reader": "Essential tool for visually impaired users",
    "keyboard navigation": "Critical for users who can't use a mouse",
    "color contrast": "Important for users with visual impairments",
    "alt text": "Required for image accessibility",
    "aria": "Accessible Rich Internet Applications",
    "semantic html": "Proper markup for accessibility",
    "focus indicators": "Visual cues for keyboard navigation"
}

EMPATHY_PATTERNS = [
    r"\b(?:understand|appreciate|recognize)\b.*\b(?:needs|challenges|difficulties)\b",
    r"\b(?:help|support|assist|enable)\b.*\b(?:you|users|people)\b",
    r"\b(?:everyone|all users|inclusive|accessible)\b",
    r"\b(?:committed|dedicated|ensure)\b.*\b(?:accessibility|inclusion)\b"
]

TECHNICAL_REQUIREMENTS = {
    "wcag_version": r"WCAG\s*2\.[0-9]+",
    "ada_compliance": r"ADA\s+compliance",
    "section_508": r"Section\s+508"
}

TRANSITION_WORDS = [
    "additionally", "furthermore", "moreover",
    "however", "nevertheless", "conversely",
    "therefore", "consequently", "thus",
    "specifically", "for example", "notably"
]

def analyze_structure(content: str) -> StructureAnalysis:
    """Analyze blog post structure."""
    if not content:
        return {
            "paragraphs": {"count": 0, "avg_length": 0, "issues": []},
            "sentences": {"count": 0, "avg_length": 0, "issues": []}
        }
    
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    
    return {
        "paragraphs": {
            "count": len(paragraphs),
            "avg_length": sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "issues": [i for i, p in enumerate(paragraphs) if len(p.split()) > 100 or len(p.split()) < 20]
        },
        "sentences": {
            "count": len(sentences),
            "avg_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0,
            "issues": []
        }
    }

def find_term_context(content: str, term: str, window: int = 100) -> Optional[str]:
    """Find context around a term in content."""
    if not content or not term:
        return None
    
    match = re.search(f".{{0,{window}}}{term}.{{0,{window}}}", content, re.IGNORECASE)
    return match.group(0).strip() if match else None

def analyze_accessibility(content: str) -> AccessibilityAnalysis:
    """Analyze accessibility coverage in content."""
    if not content:
        return {
            "terms_covered": 0,
            "coverage_score": 0,
            "covered_terms": {},
            "missing_terms": list(ACCESSIBILITY_TERMS.keys())
        }
    
    content_lower = content.lower()
    covered_terms = {}
    
    for term, description in ACCESSIBILITY_TERMS.items():
        if term in content_lower:
            covered_terms[term] = {
                "description": description,
                "context": find_term_context(content, term)
            }
    
    return {
        "terms_covered": len(covered_terms),
        "coverage_score": (len(covered_terms) / len(ACCESSIBILITY_TERMS)) * 10,
        "covered_terms": covered_terms,
        "missing_terms": [term for term in ACCESSIBILITY_TERMS if term not in covered_terms]
    }

def analyze_empathy(content: str) -> EmpathyAnalysis:
    """Analyze empathetic language in content."""
    if not content:
        return {
            "empathy_score": 0,
            "empathy_examples": [],
            "needs_improvement": True
        }
    
    empathy_matches = []
    for pattern in EMPATHY_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        empathy_matches.extend([m.group(0) for m in matches])
    
    return {
        "empathy_score": min(10, len(empathy_matches) * 2),
        "empathy_examples": empathy_matches[:3],
        "needs_improvement": len(empathy_matches) < 3
    }

def analyze_technical(content: str) -> TechnicalAnalysis:
    """Analyze technical accuracy of content."""
    if not content:
        return {
            "requirements_met": {name: False for name in TECHNICAL_REQUIREMENTS},
            "score": 0
        }
    
    requirements_met = {
        name: bool(re.search(pattern, content, re.IGNORECASE))
        for name, pattern in TECHNICAL_REQUIREMENTS.items()
    }
    
    return {
        "requirements_met": requirements_met,
        "score": (sum(requirements_met.values()) / len(requirements_met)) * 10
    }

def analyze_flow(content: str) -> FlowAnalysis:
    """Analyze content flow and transitions."""
    if not content:
        return {
            "transition_count": 0,
            "flow_score": 0,
            "needs_improvement": True
        }
    
    transition_count = sum(
        1 for word in TRANSITION_WORDS 
        if re.search(r'\b' + word + r'\b', content, re.IGNORECASE)
    )
    
    return {
        "transition_count": transition_count,
        "flow_score": min(10, transition_count * 2),
        "needs_improvement": transition_count < 5
    }

def generate_improvements(analysis: Dict[str, Any]) -> List[ContentImprovement]:
    """Generate improvement suggestions based on analysis."""
    improvements = []
    
    # Structure improvements
    if analysis["structure"]["paragraphs"]["avg_length"] > 100:
        improvements.append(ContentImprovement(
            category="Structure",
            issue="Some paragraphs are too long",
            suggestion="Break down paragraphs longer than 100 words for better readability"
        ))
    
    # Accessibility improvements
    if analysis["accessibility"]["coverage_score"] < 7:
        missing = ", ".join(analysis["accessibility"]["missing_terms"][:3])
        improvements.append(ContentImprovement(
            category="Accessibility Coverage",
            issue="Missing key accessibility terms",
            suggestion=f"Add coverage of: {missing}"
        ))
    
    # Empathy improvements
    if analysis["empathy"]["needs_improvement"]:
        improvements.append(ContentImprovement(
            category="Empathy",
            issue="Could use more empathetic language",
            suggestion="Add more phrases that acknowledge user challenges and needs"
        ))
    
    # Technical improvements
    if analysis["technical"]["score"] < 7:
        improvements.append(ContentImprovement(
            category="Technical Accuracy",
            issue="Missing some technical requirements",
            suggestion="Ensure all key standards (WCAG, ADA, Section 508) are mentioned with versions"
        ))
    
    # Flow improvements
    if analysis["flow"]["needs_improvement"]:
        improvements.append(ContentImprovement(
            category="Content Flow",
            issue="Limited use of transition words",
            suggestion="Add more transition words between paragraphs for better flow"
        ))
    
    return improvements

def analyze_blog_post(
    content: str,
    output_dir: str = "analysis",
    seed_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive blog post analysis with keyword research.
    
    Args:
        content: Blog post content
        output_dir: Directory to save analysis results
        seed_keywords: Optional list of seed keywords for research
        
    Returns:
        Dict containing analysis results, paths, and keyword research
    """
    try:
        if not content:
            raise ValueError("Content cannot be empty")
        
        # Create output directories
        output_path = Path(output_dir)
        research_dir = output_path / "keyword_research"
        for path in [output_path, research_dir]:
            path.mkdir(exist_ok=True)
        
        # Get keyword suggestions if seed keywords provided
        keyword_data = {}
        if seed_keywords:
            keyword_data = get_keyword_suggestions(
                seed_keywords=seed_keywords,
                research_dir=research_dir
            )
            # Log keyword research
            create_research_log(
                primary_keyword=keyword_data["suggested_keywords"][0],
                related_keywords=keyword_data["suggested_keywords"][1:],
                research_dir=research_dir,
                notes=f"Generated from seeds: {', '.join(seed_keywords)}"
            )
        
        # Perform all analyses
        structure = analyze_structure(content)
        accessibility = analyze_accessibility(content)
        empathy = analyze_empathy(content)
        technical = analyze_technical(content)
        flow = analyze_flow(content)
        
        # Calculate overall score
        scores = [
            accessibility["coverage_score"],
            empathy["empathy_score"],
            technical["score"],
            flow["flow_score"]
        ]
        overall_score = sum(scores) / len(scores)
        
        # Generate improvements
        improvements = generate_improvements({
            "structure": structure,
            "accessibility": accessibility,
            "empathy": empathy,
            "technical": technical,
            "flow": flow
        })
        
        # Create analysis object
        analysis = BlogAnalysis(
            structure=structure,
            accessibility=accessibility,
            empathy=empathy,
            technical=technical,
            flow=flow,
            overall_score=overall_score,
            improvements=improvements
        )
        
        # Save analysis results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_file = output_path / f"analysis_{timestamp}.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis.model_dump(), f, indent=2)
        
        # Generate and save report
        report = generate_markdown_report(analysis)
        report_file = output_path / f"report_{timestamp}.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        return {
            "analysis": analysis,
            "analysis_path": str(analysis_file),
            "report_path": str(report_file),
            "keyword_research": keyword_data
        }
        
    except Exception as e:
        raise Exception(f"Error analyzing blog post: {str(e)}")

def generate_markdown_report(analysis: BlogAnalysis) -> str:
    """Generate a markdown report from analysis results."""
    report = []
    
    # Overall score
    report.append("# Blog Post Analysis Report\n")
    report.append(f"## Overall Score: {analysis.overall_score:.1f}/10\n")
    
    # Structure
    report.append("## Structure Analysis")
    struct = analysis.structure
    report.append(f"- Paragraphs: {struct['paragraphs']['count']}")
    report.append(f"- Average paragraph length: {struct['paragraphs']['avg_length']:.1f} words")
    report.append(f"- Sentences: {struct['sentences']['count']}\n")
    
    # Accessibility
    report.append("## Accessibility Coverage")
    access = analysis.accessibility
    report.append(f"- Coverage Score: {access['coverage_score']:.1f}/10")
    report.append("- Missing Terms:")
    for term in access["missing_terms"][:3]:
        report.append(f"  * {term}")
    report.append("")
    
    # Empathy
    report.append("## Empathy Analysis")
    empathy = analysis.empathy
    report.append(f"- Empathy Score: {empathy['empathy_score']}/10")
    if empathy["empathy_examples"]:
        report.append("- Examples of empathetic language:")
        for example in empathy["empathy_examples"]:
            report.append(f"  * {example}")
    report.append("")
    
    # Technical
    report.append("## Technical Analysis")
    tech = analysis.technical
    report.append(f"- Technical Score: {tech['score']:.1f}/10")
    report.append("- Requirements Met:")
    for req, met in tech["requirements_met"].items():
        report.append(f"  * {req}: {'✓' if met else '✗'}")
    report.append("")
    
    # Flow
    report.append("## Content Flow")
    flow = analysis.flow
    report.append(f"- Flow Score: {flow['flow_score']}/10")
    report.append(f"- Transition words used: {flow['transition_count']}\n")
    
    # Improvements
    report.append("## Suggested Improvements")
    for imp in analysis.improvements:
        report.append(f"### {imp.category}")
        report.append(f"**Issue**: {imp.issue}")
        report.append(f"**Suggestion**: {imp.suggestion}\n")
    
    return "\n".join(report)

def analyze_and_save(content: str, output_dir: str = "analysis") -> str:
    """
    Analyze blog post and save results.
    
    Args:
        content: Blog post content
        output_dir: Directory to save analysis results
        
    Returns:
        Path to the analysis report file
    
    Raises:
        ValueError: If content is empty
        OSError: If there are file system errors
    """
    try:
        # Analyze content
        analysis = analyze_blog_post(content)
        
        # Generate report
        report = generate_markdown_report(analysis)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save analysis as JSON
        analysis_file = output_path / "blog_analysis.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis.dict(), f, indent=2)
        
        # Save report as markdown
        report_file = output_path / "blog_analysis_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        return str(report_file)
        
    except ValueError as e:
        raise ValueError(f"Invalid content: {str(e)}")
    except OSError as e:
        raise OSError(f"Error saving analysis: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error during analysis: {str(e)}")

if __name__ == "__main__":
    example_content = """
    # Example Blog Post
    This is an example blog post about web accessibility...
    """
    
    try:
        report_path = analyze_and_save(example_content)
        print(f"Analysis report saved to: {report_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
